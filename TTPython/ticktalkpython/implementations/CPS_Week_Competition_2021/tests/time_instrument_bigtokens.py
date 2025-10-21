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
        # a=a[0]
        # b=b[0]
        if a == None or b == None:
            c = None
        else:
            c = math.sqrt(a[0]**2 + b[0]**2)
            if c > 1e10: return
        print('Pythagorean function running on %f and %f to produce %f!' % (a[0],b[0],c))
        # print(a)
        # print(b)
        # print(c)
        # print(time_overlap)
        time_interval =  str(time_overlap.begin) + ':' + str(time_overlap.end)
        self.instrument_queue.put(TimeLogItem(time.time(), 'pythagorean', time_interval))

        # Loopback some tokens to the same function for further testing; for testing purposes only. Comment out lines below to run as single iteration. 
        output_tag = Tag.Tag('pythagorean', 'a', time_overlap.begin, time_overlap.end)
        output_token = Token.Token(output_tag, (c, a[1]))
        recipient_name = 'self'
        self.network_send_queue.put((output_token, recipient_name)) #send to named device, e.g. CAV1, RSU
        output_tag = Tag.Tag('pythagorean', 'b', time_overlap.begin, time_overlap.end)
        output_token = Token.Token(output_tag, (c/2, b[1]))
        recipient_name = 'self'
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
    pythag_sync = WaitingMatching.InputSynchronizedFunction(pythag_fp.pythagorean, pythag_fp.input_queue, instrument.queue)

    #register synchronization section with process/interface manager
    interface_manager.add_sync_process(pythag_sync.function_name, pythag_sync)

    interface_manager.start_send_process(self_ip, tx_port)
    time.sleep(1)


    a_value = (3, 'asdf'*256*1) #1kB message, but can easily be increased with last parameter
    b_value = (4, 'asdf'*256*1)

    #create tokens
    now = time.time()
    for i in range(5):
        input_a_tag = Tag.Tag(pythag_sync.function_name, 'a', now+i*100, now+(i+1)*100)
        input_a_token = Token.Token(input_a_tag, a_value)
        input_b_tag = Tag.Tag(pythag_sync.function_name, 'b', now+i*100, now+(i+1)*100)
        input_b_token = Token.Token(input_b_tag, b_value)

        #send tokens through network interface
        interface_manager.send_token_to_device(input_a_token, 'CAV1')
        interface_manager.send_token_to_device(input_b_token, 'CAV1')
    
    time.sleep(15)

    input_a_tag = Tag.Tag('bluh', 'a', now+1000, now+2000)
    input_a_token = Token.Token(input_a_tag, a_value)
    input_b_tag = Tag.Tag(pythag_sync.function_name, 'b', now+1000, now+2000)
    input_b_token = Token.Token(input_b_tag, b_value)
    interface_manager.send_token_to_device(input_a_token, 'CAV1')
    interface_manager.send_token_to_device(input_b_token, 'CAV1')
    # interface_manager.send_token_queue.put((input_a_token, 'self')) #TODO: clean up; no need to be a 'put'
    # interface_manager.send_token_queue.put((input_b_token, 'self'))

    time.sleep(5)
    print("All Done!")
    
    #need this to make sure the main process doesn't finish and carry everything into the abyss
    pythag_sync.proc.join() 

if __name__ == "__main__":
    main()
