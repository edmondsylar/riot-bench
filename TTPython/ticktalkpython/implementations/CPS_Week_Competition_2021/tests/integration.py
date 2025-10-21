import sys, os, time, math

sys.path.insert(0, os.path.abspath('..'))

import pickle, logging
import multiprocessing, queue
from intervaltree import Interval

import DebugLogger

DebugLogger.set_base_logger_level(0)
logging.basicConfig(level=0)

import Tag, Token, WaitingMatching
import Network
import ProcessManager



class PythagFunctionProcess():
    #minimal wrapper; if you need state, then the function needs to be a method of this function-process class such that self is available when the function runs. 
    def __init__(self, network_send_queue):
        self.input_queue = multiprocessing.Queue()

        self.network_send_queue = network_send_queue

        self.proc = multiprocessing.Process(target=self.listener)
        self.proc.start()

        tag = Tag(t_start, t_stop, 'global_fusion', 'cav'+self.CAV_ID)
        token = Token(locations, tag)
        recipient_device = 'RSU'
        self.send_token_queue.put((token, recipient_device))

    def listener(self):
        while True:
            try:
                input_args = self.input_queue.get(block=True, timeout=1)
                args = input_args[0]
                kwargs = input_args[1]
                self.pythagorean(*args, **kwargs)
            except queue.Empty:
                continue
            except: 
                raise

    def pythagorean(self, a, b, time_overlap=Interval(0,1)):
        '''
        args supplied by the synchronized WM function
        '''
        if a == None or b == None:
            c = None
        else:
            c = math.sqrt(a**2 + b**2)

        # print('Pythagorean function running!')
        # print(a)
        # print(b)
        # print(c)
        # print(time_overlap)

        # Prep value to be sent to the part of the program
        print(time_overlap)
        output_tag = Tag.Tag('pythagorean', 'a', time_overlap.begin, time_overlap.end)
        output_token = Token.Token(output_tag, c)
        print(output_token )
        print(output_token.value)
        recipient_name = 'self'
        self.network_send_queue.put((output_token, recipient_name)) #send to named device, e.g. CAV1, RSU


def main():
    #receive to this IP + port
    tx_port = 7167 #TX on this port, RX on 7178 (port+1)
    rx_port = tx_port+1
    self_ip = '192.168.0.152' #This needs to be THIS device's IP on the 192.168 subnet

    #turn network messages into tokens that get sent to the right function
    interface_manager = ProcessManager.TokenInterfaceManager(rx_ip=self_ip, rx_port=tx_port)
    interface_manager.add_route('CAV1', '192.168.0.152:'+str(rx_port)) # use the RX port

    #receive network interface
    rx_network = Network.TTNetwork(ip=self_ip, port=rx_port, msg_receiver=interface_manager.receiver_function)

    #wrapped function that needs to be synchronized
    pythag_fp = PythagFunctionProcess(interface_manager.send_token_queue)
    pythag_sync = WaitingMatching.InputSynchronizedFunction(pythag_fp.pythagorean, pythag_fp.input_queue)

    #register synchronization section with process/interface manager
    interface_manager.add_sync_process(pythag_sync.function_name, pythag_sync)

    interface_manager.start_send_process(self_ip, tx_port)


    #create tokens
    now = time.time()
    input_a_tag = Tag.Tag(pythag_sync.function_name, 'a', now+0, now+100)
    input_a_token = Token.Token(input_a_tag, 3)
    input_b_tag = Tag.Tag(pythag_sync.function_name, 'b', now+0, now+100)
    input_b_token = Token.Token(input_b_tag, 4)

    #send tokens through network interface
    interface_manager.send_token_to_device(input_a_token, 'CAV1')
    interface_manager.send_token_to_device(input_b_token, 'CAV1')
    # interface_manager.send_token_queue.put((input_a_token, 'self')) #TODO: clean up; no need to be a 'put'
    # interface_manager.send_token_queue.put((input_b_token, 'self'))

    #need this to make sure the main process doesn't finish and carry everything into the abyss
    pythag_sync.proc.join() 

if __name__ == "__main__":
    main()
