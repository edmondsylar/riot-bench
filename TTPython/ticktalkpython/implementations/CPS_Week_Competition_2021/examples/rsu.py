import sys, os, time, math

import pickle
import multiprocessing, queue
from intervaltree import Interval

sys.path.insert(0, os.path.abspath('../'))

import Token, WaitingMatching, Tag
import Network
import ProcessManager

import json
import socket
import math
from threading import Lock, Thread
from queue import Queue

from rsu_folder import gui
from rsu_folder import mapGenerator
from rsu_folder import rsu
from rsu_folder import vehicle

def whoAmI():
    # Finds our own IP address automagically, doesn't work on mac!
    return [l for l in (
    [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1], [
        [(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in
            [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) if l][0][0]

class GlobalFusion():
    #minimal wrapper; if you need state, then the function needs to be a method of this function-process class such that self is available when the function runs. 
    def __init__(self, network_send_queue, RSU, first_deadline, g_back_queue):
        self.input_queue = multiprocessing.Queue()
        self.function = self.global_fusion

        self.network_send_queue = network_send_queue

        self.RSU = RSU
        self.interval = .125
        self.deadline = first_deadline

        self.g_back_queue = g_back_queue

        self.proc = multiprocessing.Process(target=self.listener)
        self.proc.start()

    def listener(self):
        while True:
            try:
                input_args = self.input_queue.get(block=True, timeout=1)
                args = input_args[0]
                kwargs = input_args[1]
                self.global_fusion(*args, **kwargs)
            except queue.Empty:
                continue
            except: 
                raise

    def global_fusion(self, cam, cav1, time_overlap=Interval(0,.125)):
    #def global_fusion(self, cav1_obs, cav1_pos, time_overlap=Interval(0,.125)):
        cav2 = None
        #cam = None
        #cav1 = None
        '''
        args supplied by the synchronized WM function
        '''

        try:
            rec = self.g_back_queue.get(block=False, timeout=.001)
            start = time.time()
            while rec != None and ((time.time() - start) <= .01):
                #print ( " rec ", str(rec))
                for veh in rec:
                    self.RSU.vehicles[veh[0]].targetVelocityGeneral = veh[1]
                #print ( " speed changed to ", str(rec))
                rec = self.g_back_queue.get(block=False, timeout=.001)
        except:
            pass

        self.RSU.checkLightState()

        #print('Global fusion function running!')
        #print(time_overlap)

        if cav1 != None:
            response = self.RSU.recieveMessage(cav1)

            #print ( '   responding ' + str(response) )

            # Prep value to be sent to the part of the program
            output_tag = Tag.Tag('actuate', 'response', time_overlap.begin, time_overlap.end)
            output_token = Token.Token(output_tag, [[float(cav1['x']), float(cav1['y']), float(cav1['yaw']), None, time.time()],response])
            recipient_name = 'CAV1'
            self.network_send_queue.put((output_token, recipient_name)) #send to named device, e.g. CAV1, RSU

            # Send our data to ourself in the gui thread, inefficient but effective
            output_tag = Tag.Tag('update_vehicles', 'cav1', time_overlap.begin, time_overlap.end + .001)
            output_token = Token.Token(output_tag, cav1)
            recipient_name = 'RSU'
            self.network_send_queue.put((output_token, recipient_name)) #send to named device, e.g. CAV1, RSU
        else:
            # Send our data to ourself in the gui thread, inefficient but effective
            output_tag = Tag.Tag('update_vehicles', 'cav1', time_overlap.begin, time_overlap.end + .001)
            output_token = Token.Token(output_tag, None)
            recipient_name = 'RSU'
            self.network_send_queue.put((output_token, recipient_name)) #send to named device, e.g. CAV1, RSU

        if cav2 != None:
            response = self.RSU.recieveMessage(cav2)

            #print ( '   responding ' + str(response) )

            # Prep value to be sent to the part of the program
            output_tag = Tag.Tag('actuate', 'response', time_overlap.begin, time_overlap.end)
            output_token = Token.Token(output_tag, [[float(cav2['x']), float(cav2['y']), float(cav2['yaw']), None, time.time()],response])
            recipient_name = 'CAV2'
            self.network_send_queue.put((output_token, recipient_name)) #send to named device, e.g. CAV2, RSU

            # Send our data to ourself in the gui thread, inefficient but effective
            output_tag = Tag.Tag('update_vehicles', 'cav2', time_overlap.begin, time_overlap.end + .001)
            output_token = Token.Token(output_tag, cav2)
            recipient_name = 'RSU'
            self.network_send_queue.put((output_token, recipient_name)) #send to named device, e.g. CAV2, RSU
        else:
            # Send our data to ourself in the gui thread, inefficient but effective
            output_tag = Tag.Tag('update_vehicles', 'cav2', time_overlap.begin, time_overlap.end + .001)
            output_token = Token.Token(output_tag, None)
            recipient_name = 'RSU'
            self.network_send_queue.put((output_token, recipient_name)) #send to named device, e.g. CAV2, RSU

        if cam != None:
            response = self.RSU.recieveMessage(cam)

            # Prep value to be sent to the part of the program
            output_tag = Tag.Tag('actuate', 'response', time_overlap.begin, time_overlap.end)
            output_token = Token.Token(output_tag, response)
            recipient_name = 'CAM'
            self.network_send_queue.put((output_token, recipient_name)) #send to named device, e.g. CAV1, RSU

            # Send our data to ourself in the gui thread, inefficient but effective
            output_tag = Tag.Tag('update_vehicles', 'cam', time_overlap.begin, time_overlap.end + .001)
            output_token = Token.Token(output_tag, cam)
            recipient_name = 'RSU'
            self.network_send_queue.put((output_token, recipient_name)) #send to named device, e.g. CAV1, RSU
        else:
            # Send our data to ourself in the gui thread, inefficient but effective
            output_tag = Tag.Tag('update_vehicles', 'cam', time_overlap.begin, time_overlap.end + .001)
            output_token = Token.Token(output_tag, None)
            recipient_name = 'RSU'
            self.network_send_queue.put((output_token, recipient_name)) #send to named device, e.g. CAV1, RSU

        # Send our data to ourself in the gui thread, inefficient but effective
        output_tag = Tag.Tag('update_vehicles', 'tfl_state', time_overlap.begin, time_overlap.end + .001)
        output_token = Token.Token(output_tag, self.RSU.trafficLightArray)
        recipient_name = 'RSU'
        self.network_send_queue.put((output_token, recipient_name)) #send to named device, e.g. CAV1, RSU

        # # Send our own deadline to ourself1
        # tag_deadline = Tag.Tag('global_fusion', 'DEADLINE', self.deadline, self.deadline + .100)
        # token_deadline = Token.Token(tag_deadline, None)
        # recipient_name = 'RSU'
        # self.network_send_queue.put((token_deadline, recipient_name)) #send to named device, e.g. CAV1, RSU
        # self.deadline = self.deadline + self.interval

class QTContainter():
    #minimal wrapper; if you need state, then the function needs to be a method of this function-process class such that self is available when the function runs. 
    def __init__(self, network_send_queue, mapSpecs, vehicles, sensors, trafficLightArray, g_queue, g_back_queue):
        self.input_queue = multiprocessing.Queue()
        self.function = self.update_vehicles

        self.network_send_queue = network_send_queue

        # self.vehicles = vehicles
        # self.sensors = sensors
        # self.trafficLightArray = trafficLightArray
        self.g_queue = g_queue

        self.proc = multiprocessing.Process(target=self.listener)
        self.proc.start()

        # Start up the GUI as it's own thread
        t = Thread(target=self.QT_main, args=(mapSpecs, vehicles, sensors, trafficLightArray, self.g_queue, g_back_queue))
        t.daemon = True
        t.start()

    def listener(self):
        while True:
            try:
                input_args = self.input_queue.get(block=True, timeout=1)
                args = input_args[0]
                kwargs = input_args[1]
                self.update_vehicles(*args, **kwargs)
            except queue.Empty:
                continue
            except: 
                raise

    def QT_main(self, mapSpecs, vehicles, sensors, trafficLightArray, g_queue, g_back_queue):
        # Initialize a simulator with the GUI set to on, cm map, .1s timestep, and vehicle spawn scale of 1 (default)
        QTapp = gui.QtWidgets.QApplication(sys.argv)
        self.mainWin = gui.MainWindow(mapSpecs, vehicles, sensors, trafficLightArray, g_queue, g_back_queue)
        self.mainWin.show()

        sys.exit(QTapp.exec_())

    def update_vehicles(self, cav1, cav2, cam, tfl_state, time_overlap=Interval(0,.125)):
        self.g_queue.put([cav1, cav2, cam, tfl_state])

def main():
    #receive to this IP + port
    tx_port = 7167 #TX on this port, RX on 7178 (port+1)
    rx_port = tx_port+1
    self_ip = "192.168.1.162" #This needs to be THIS device's IP on the 192.168 subnet

    #turn network messages into tokens that get sent to the right function
    interface_manager = ProcessManager.TokenInterfaceManager(rx_ip=self_ip, rx_port=tx_port)

    with open('routing.json') as json_file:
        data = json.load(json_file)

        #print ( data['routing']['CAV1'] )

        interface_manager.add_route('CAV1', data['routing']['CAV1']+':'+str(rx_port)) # use the RX port
        interface_manager.add_route('CAV2', data['routing']['CAV2']+':'+str(rx_port)) # use the RX port
        interface_manager.add_route('CAM', data['routing']['CAM']+':'+str(rx_port)) # use the RX port
        interface_manager.add_route('RSU', data['routing']['RSU']+':'+str(rx_port)) # use the RX port

    # Setup the shared variables
    vehicles = {}
    sensors = {}
    pose = {}
    trafficLightArray = [0, 2, 0]

    # Setup the mapspecs
    mapSpecs = mapGenerator.MapSpecs()
    sim = rsu.RSU(mapSpecs, vehicles, sensors, trafficLightArray, True)

    #receive network interface
    rx_network = Network.TTNetwork(ip=self_ip, port=rx_port, msg_receiver=interface_manager.receiver_function)

    # Set up the first deadline
    first_deadline = (time.time() / 1.0) + 5

    # Make some queues to talk with the gui
    g_queue = multiprocessing.Queue()
    g_back_queue = multiprocessing.Queue()

    #wrapped function that needs to be synchronized
    global_fusion_fp = GlobalFusion(interface_manager.send_token_queue, sim, first_deadline, g_back_queue)
    global_fusion_sync = WaitingMatching.InputSynchronizedFunction(GlobalFusion.global_fusion, global_fusion_fp.input_queue, use_deadline=True)

    #wrapped function that needs to be synchronized
    qt_container_fp = QTContainter(interface_manager.send_token_queue, mapSpecs, vehicles, sensors, trafficLightArray, g_queue, g_back_queue)
    qt_container_sync = WaitingMatching.InputSynchronizedFunction(QTContainter.update_vehicles, qt_container_fp.input_queue)

    #register synchronization section with process/interface manager
    interface_manager.add_sync_process(global_fusion_sync.function_name, global_fusion_sync)

    #register synchronization section with process/interface manager
    interface_manager.add_sync_process(qt_container_sync.function_name, qt_container_sync)

    # Send the first deadline
    tag_deadline = Tag.Tag('global_fusion', "DEADLINE", first_deadline, first_deadline+.100)
    token_deadline = Token.Token(tag_deadline, None)
    recipient_name = 'RSU'

    interface_manager.send_token_to_device(token_deadline, recipient_name)

    #need this to make sure the main process doesn't finish and carry everything into the abyss
    global_fusion_sync.proc.join()

if __name__ == "__main__":
    main()