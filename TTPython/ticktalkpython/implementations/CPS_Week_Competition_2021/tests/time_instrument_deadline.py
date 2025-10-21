import sys, os, time, math

sys.path.insert(0, os.path.abspath('..'))

import pickle
import socket
import multiprocessing, queue
from intervaltree import Interval

import Tag, Token, WaitingMatching
import Network
import ProcessManager
from Instrumentation import TimeInstrument, TimeLogItem


class PythagFunctionProcess():
    #minimal wrapper; if you need state, then the function needs to be a method of this function-process class such that self is available when the function runs. 
    def __init__(self, network_send_queue, instrument_queue=None):
        self.input_queue = multiprocessing.Queue()

        self.network_send_queue = network_send_queue
        self.instrument_queue = instrument_queue

        self.proc = multiprocessing.Process(target=self.listener)
        self.proc.start()

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
            # c = None
            c=-1
            print('deadline triggered!')
        else:
            c = math.sqrt(a**2 + b**2)

        print('Pythagorean function running!')
        # print(a)
        # print(b)
        # print(c)
        # print(time_overlap)

        # Prep value to be sent to the part of the program
        time_interval =  str(time_overlap.begin) + ':' + str(time_overlap.end)
        self.instrument_queue.put(TimeLogItem(time.time(), 'pythagorean', time_interval))
        output_tag = Tag.Tag('pythagorean', 'a', time_overlap.begin+25, time_overlap.end+25)
        output_token = Token.Token(output_tag, c)
        recipient_name = 'CAV1'
        self.network_send_queue.put((output_token, recipient_name)) #send to named device, e.g. CAV1, RSU


def main():
    #receive to this IP + port
    tx_port = 7167 #TX on this port, RX on 7178 (port+1)
    rx_port = tx_port+1
    self_ip = '192.168.0.152' #This needs to be THIS device's IP on the 192.168 subnet
    
    # find self IP
    # self_ip = [l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1], [[(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) if l][0][0]

    instrument = TimeInstrument('CAV')

    interface_manager = ProcessManager.TokenInterfaceManager(instrument_queue=instrument.queue, rx_ip=self_ip, rx_port=tx_port)
    interface_manager.add_route('CAV1', '192.168.0.152:'+str(rx_port)) # use the RX port

    #receive network interface
    rx_network = Network.TTNetwork(ip=self_ip, port=rx_port, msg_receiver=interface_manager.receiver_function)

    #wrapped function that needs to be synchronized
    pythag_fp = PythagFunctionProcess(interface_manager.send_token_queue, instrument.queue)
    pythag_sync = WaitingMatching.InputSynchronizedFunction(pythag_fp.pythagorean, pythag_fp.input_queue, instrument.queue, use_deadline=True)

    #register synchronization section with process/interface manager
    interface_manager.add_sync_process(pythag_sync.function_name, pythag_sync)

    interface_manager.start_send_process(self_ip, tx_port)
    time.sleep(1)
    #create tokens
    now = time.time()
    input_a_tag = Tag.Tag(pythag_sync.function_name, 'a', now, now+5)
    input_a_token = Token.Token(input_a_tag, 3)
    input_b_tag = Tag.Tag(pythag_sync.function_name, 'b', now, now+5)
    input_b_token = Token.Token(input_b_tag, 4)

    #send tokens through network interface
    interface_manager.send_token_to_device(input_a_token, 'CAV1')
    interface_manager.send_token_to_device(input_b_token, 'CAV1')
    time.sleep(10)
    
    input_a_tag = Tag.Tag(pythag_sync.function_name, 'DEADLINE', now+25+2.5, now+30)
    input_a_token = Token.Token(input_a_tag, 3)
    interface_manager.send_token_to_device(input_a_token, 'CAV1')
    # interface_manager.send_token_queue.put((input_a_token, 'self')) #TODO: clean up; no need to be a 'put'
    # interface_manager.send_token_queue.put((input_b_token, 'self'))

    #need this to make sure the main process doesn't finish and carry everything into the abyss
    time.sleep(60)
    print("All Done!")
    pythag_sync.proc.join() 

if __name__ == "__main__":
    main()
