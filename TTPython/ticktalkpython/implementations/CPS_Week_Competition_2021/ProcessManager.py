# Copyright 2021 Carnegie Mellon University
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import sys, os, time, socket
import pickle
import multiprocessing, queue, threading
import Network
import WaitingMatching, Token
from Instrumentation import TimeLogItem
import DebugLogger

logger = DebugLogger.get_logger(__name__)


def delay_function(arg, func, delay=3, repeat_count=0):
    # logger.debug('delay process to sleep for %f seconds before releasing token %s' % (duration, token))
    if delay > 0:
        time.sleep(delay) 
    func(arg, repeat_count=repeat_count+1)


class TokenInterfaceManager():

    def __init__(self, self_name='self', rx_ip='127.0.0.1', rx_port=8080, instrument_queue=None, debug_logging=False, too_old_threshold=.200):
        ##Note that rx_ip and rx_port are actuall the TX port and IP. Assume the actual RX IP is the same, but the RX port is one (1) greater.
        self.name = self_name
        self.debug_logging = debug_logging
        self.wm_input_queues = {}
        self.too_old_threshold = too_old_threshold
        
        if rx_ip == '127.0.0.1':
            #127.0.0.1 doesn't work well.. find the self IP another way. May not work perfectly..
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            rx_ip = (s.getsockname()[0])
            s.close()
            
        self.routing_table = {self_name:rx_ip+":"+str(rx_port+1)}
        self.routing_table['self'] = rx_ip+":"+str(rx_port+1)

        # self.network = Network.TTNetwork(msg_receiver=self.token_reciever, ip=self_network_ip, port=self_network_port)

        self.send_token_queue = multiprocessing.Queue(maxsize=25)
        self.instrument_queue = instrument_queue

        #this is actually the tx_port
        # self.start_send_process(rx_ip, rx_port)
        self.receiver_function = self.token_reciever


    def start_send_process(self, tx_ip, tx_port):
        self.send_proc = multiprocessing.Process(target=self.token_send_listener, args=[tx_ip, tx_port])
        self.send_proc.start()

    def add_sync_process(self, function_name, synchronization_process:WaitingMatching.InputSynchronizedFunction):

        receiveTokenFunc = getattr(synchronization_process, 'receiveToken',  None)
        assert callable(receiveTokenFunc), 'Invalid function/object provided'

        self.wm_input_queues[function_name] = synchronization_process.input_queue
        # self.send_token_queue.put(('new process', function_name, synchronization_process.input_queue))

    def add_route(self, device_name, dest_addr):
        '''
        dest address is assumed to be IP:port, e.g. 192.168.0.1:1024. We may only add to this; if it must be removed, overwrite it with some bogus address
        '''
        self.routing_table[device_name] = dest_addr #also sufficient for updating a route
        self.send_token_queue.put(('new route', device_name, dest_addr))


    def token_reciever(self, message, repeat_count=0):

        #check message type; should be InputToken
        if message.message_type != Network.TTMessageType.InputToken:
            if self.debug_logging:
                logger.error('Error! Unrecognized message type %s' % str(message.type))

        try:
            token = pickle.loads(message.payload)
        except:
            return

        self.give_token_to_process(token)

    def token_send_listener(self, tx_ip, tx_port):
        tx_network = Network.TTNetwork(ip=tx_ip, port=tx_port) 

        while True:
            try:
                try:
                    qsize = self.send_token_queue.qsize()
                    if qsize > 10: logger.log(50, "Too many items in send queue: %d" % qsize)
                except: pass
                input_args = self.send_token_queue.get(block=True, timeout=5)
                if isinstance(input_args[0], Token.Token) :
                    #TODO: if token is too old (need parameter), then we may need to drop it entirely)
                    token = input_args[0]
                    if self.instrument_queue:
                        self.instrument_queue.put(TimeLogItem(time.time(), 'PM.send_token', 'token_id:'+str(token.id)))
                    # remove tokens that are 'too old'. 
                    if token.tag.stop + self.too_old_threshold < time.time():
                        logger.log(50,'token too old. Skipping')
                        continue

                    recipient_device_address = input_args[1]
                    if len(input_args)>2:
                        ensure_delivery=input_args[2]
                    else: 
                        ensure_delivery=False
                    # If we're sending the token to ourselves, then don't bother sending through network. Shortcut
                    if recipient_device_address == self.routing_table['self'] or self.routing_table[recipient_device_address] == self.routing_table['self']:
                        # logger.log(41, "Routing table resolved outgoing token to be to itself; shortcut network and send to process %s" % token.tag.func_name)
                        self.give_token_to_process(token)
                        continue

                    try:
                        ip = recipient_device_address.split(':')[0]
                        port = int(recipient_device_address.split(':')[1])
                    except IndexError as e:
                        recipient_device_address = self.routing_table[recipient_device_address]
                        ip = recipient_device_address.split(':')[0]
                        port = int(recipient_device_address.split(':')[1])
                    except:
                        raise
                    t1 = time.time()
                    self._send_token(token, ip, port, tx_network, ensure_delivery=ensure_delivery)
                    t2 = time.time()
                    t_diff = t2-t1
                    # logger.log(42, "Initiating token-send took %f seconds to return" % (t_diff))
                else:
                    if input_args[0] == 'new route':
                        #if it's not a token, it's an entry for the routing table
                        self.routing_table[input_args[1]] = input_args[2]
                        if self.debug_logging:
                            logger.debug('add routing table entries')
                            logger.debug(self.routing_table)
                    elif input_args[0] == 'new process':
                        self.wm_input_queues[input_args(1)] = input_args[2]
            except queue.Empty:
                continue
            except KeyError as e:
                logger.error('Device Name could not be found in the routing table! Token will not be sent!')
                logger.error(e)
                logger.error(self.routing_table)
            except: 
                raise

    def _send_token(self, token, ip, port, network, ensure_delivery=False):

        # token_bytes = pickle.dumps(token)
        #look up who we are sending to
        if self.instrument_queue:
            self.instrument_queue.put(TimeLogItem(time.time(), 'PM.send_token', str(token.tag)))
        message = Network.message(token, Network.TTMessageType.InputToken, recipient_ip=ip, recipient_port=port)
        network.send(message, ensure=ensure_delivery)

    def send_token_to_device(self, token, recipient_device_name):

        if self.routing_table[recipient_device_name] == self.routing_table['self']:
            # logger.log(41, "Routing table resolved outgoing token to be to itself; shortcut network and send to process %s" % token.tag.func_name)
            self.give_token_to_process(token)
        
        else:
            self.send_token_queue.put((token, recipient_device_name))

    def give_token_to_process(self, token, repeat_count=0):
        function_to_call = token.tag.func_name
        try:
            # sync_proc = self.synchronization_processes[function_to_call]
            sync_input_queue = self.wm_input_queues[function_to_call]
            sync_input_queue.put(token)

            if self.instrument_queue:
                self.instrument_queue.put(TimeLogItem(time.time(), 'PM.give_token_to_process', 'token_id:'+str(token.id)))

            # sync_proc.receiveToken(token)
        except KeyError:
            
            logger.warning("Token intended for function that is not known: %s" % token.tag.func_name)
            if repeat_count < 10:
                delay_thread = threading.Thread(target=delay_function, args=[token, self.give_token_to_process], kwargs={'repeat_count':repeat_count})
                delay_thread.start()
            else: raise
        except: raise
