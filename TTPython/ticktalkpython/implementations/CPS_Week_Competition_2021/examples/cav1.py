import sys, os, time, math

import pickle
import multiprocessing, queue
from intervaltree import Interval

from competition import Token, WaitingMatching, Tag
from competition import Network
from competition import ProcessManager

import camera_recognition
import lidar_recognition
import planning_control
import communication
import motors

import json
import socket


def whoAmI():
    # Finds our own IP address automagically, doesn't work on mac!
    return [l for l in (
    [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1], [
        [(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in
            [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) if l][0][0]

def sourceImagesThread(settings, camSpecs, network_send_queue, start_time, interval):
    # Init the camera class
    cameraRecognition = camera_recognition.Camera(settings, camSpecs)
    target = interval

    # Now wait for input
    while 1:
        if (round(time.time(),3) % target) == 0.000:
            # Send a message to start the deadline
            now = time.time()
            tag_deadline = Tag.Tag('example_function_max', 'DEADLINE', now, now + 0.125)
            token_deadline = Token.Token(tag_deadline, None)
            wm_proc.receiveToken(token_deadline)

            # Take the camera frame and process
            camcoordinates, camtimestamp_start, camtimestamp_end  = cameraRecognition.takeCameraFrame()

            # Prep value to be sent to the part of the program
            output_tag = Tag.Tag('local_fusion', 'camera', camtimestamp_start, camtimestamp_end)
            output_token = Token.Token(output_tag, camcoordinates)
            recipient_name = 'CAV1'
            network_send_queue.put((output_token, recipient_name)) #send to named device, e.g. CAV1, RSU

            # Only the first iteration targets the start time
            target = interval

def sourceLIDARThread(pipeFromC, pipeToC, network_send_queue, start_time, interval):
    # Start the connection with the LIDAR through pipes
    lidarDevice = communication.connectLIDAR(pipeFromC, pipeToC)
    target = interval

    # Init the LIDAR processing class
    lidarRecognition = lidar_recognition.LIDAR(time.time())

    # Wait for 1 second before we start everything
    time.sleep(2)

    start, end = lidarDevice.getFromC()
    lidarcoordinates, lidartimestamp = lidarRecognition.processLidarFrame(lidarDevice.parseFromC(), start)

    # Now wait for input
    while 1:
        if (round(time.time(),3) % target) == 0.000:
            # Take the LIDAR frame and process
            start, end = lidarDevice.getFromC()
            lidarcoordinates, lidartimestamp = lidarRecognition.processLidarFrame(lidarDevice.parseFromC(), start)

            # Prep value to be sent to the part of the program
            output_tag = Tag.Tag('local_fusion', 'lidar', start, end)
            output_token = Token.Token(output_tag, lidarcoordinates)
            recipient_name = 'CAV1'
            network_send_queue.put((output_token, recipient_name)) #send to named device, e.g. CAV1, RSU

            # Only the first iteration targets the start time
            target = interval

class Fusion():
    #minimal wrapper; if you need state, then the function needs to be a method of this function-process class such that self is available when the function runs. 
    def __init__(self, network_send_queue):
        self.input_queue = multiprocessing.Queue()
        self.function = self.local_fusion

        self.network_send_queue = network_send_queue

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

    def local_fusion(self, camera, lidar, time_overlap=Interval(0,.125)):

        '''
        args supplied by the synchronized WM function
        '''
        if camera == None and lidar == None:
            print(" Missed both! ")
            fused = []
        elif camera == None:
            print(" Missed Camera! ")
            fused = lidar
        elif lidar == None:
            print(" Missed LIDAR! ")
            fused = camera
        else:
            print(" Got them both! ")
            fused = camera + lidar

        print('Local fusion function running!')
        print(time_overlap)

        # Prep value to be sent to the part of the program
        output_tag = Tag.Tag('global_fusion', 'cav1_obs', time_overlap.begin, time_overlap.end)
        output_token = Token.Token(output_tag, fused)
        recipient_name = 'RSU'
        self.network_send_queue.put((output_token, recipient_name)) #send to named device, e.g. CAV1, RSU

        # Prep value to be sent to the part of the program
        output_tag = Tag.Tag('global_fusion', 'cav1_pos', time_overlap.begin, time_overlap.end)
        output_token = Token.Token(output_tag, [0.0,0.0,0.0])
        recipient_name = 'RSU'
        self.network_send_queue.put((output_token, recipient_name)) #send to named device, e.g. CAV1, RSU

class Actuation():
    #minimal wrapper; if you need state, then the function needs to be a method of this function-process class such that self is available when the function runs. 
    def __init__(self, network_send_queue):
        self.input_queue = multiprocessing.Queue()
        self.function = self.local_fusion

        self.network_send_queue = network_send_queue

        # Init everything
        self.planner = None

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

    def actuate(self, tfl_state, sticky_init, time_overlap=Interval(0,.125)):

        '''
        args supplied by the synchronized WM function
        '''

        # # Check if we have been initialized
        # if self.planner == None or sticky_route != None:
        #     self.planner = planning_control.Planner()
        #     self.planner.initialVehicleAtPosition(sticky_init["l_x"], sticky_init["l_y"], sticky_init["l_yaw"], sticky_route["route_x"], sticky_route["route_y"], sticky_route["route_TFL"], 1, False)

        if tfl_state == None:
            print ( "Emergency stop!" )
        else:
            print('Actuation achieved!')
        print(time_overlap)
            
        # else:
        #     # Update our various pieces
        #     self.planner.targetVelocityGeneral = float(RSU_response["v_t"])
        #     self.planner.update_localization([localization[0], localization[1], lidarDevice[2]])
        #     self.planner.recieve_coordinate_group_commands(RSU_response["tfl_state"])
        #     self.planner.pure_pursuit_control()

        #     # Now update our current PID with respect to other vehicles
        #     self.planner.check_positions_of_other_vehicles_adjust_velocity(RSU_response["veh_locations"], sticky_vehicle_id)

        #     # We can't update the PID controls until after all positions are known
        #     self.planner.update_pid()

        #     # Finally, issue the commands to the motors
        #     steering_ppm, motor_pid = self.planner.return_command_package()

def main():
    #receive to this IP + port
    tx_port = 7167 #TX on this port, RX on 7178 (port+1)
    rx_port = tx_port+1
    self_ip = whoAmI() #This needs to be THIS device's IP on the 192.168 subnet

    #turn network messages into tokens that get sent to the right function
    interface_manager = ProcessManager.TokenInterfaceManager(rx_ip=self_ip, rx_port=tx_port)

    with open('routing.json') as json_file:
        data = json.load(json_file)

        print ( data['routing']['CAV1'] )

        interface_manager.add_route('CAV1', data['routing']['CAV1']+':'+str(rx_port)) # use the RX port
        interface_manager.add_route('CAV2', data['routing']['CAV2']+':'+str(rx_port)) # use the RX port
        interface_manager.add_route('CAM', data['routing']['CAM']+':'+str(rx_port)) # use the RX port
        interface_manager.add_route('RSU', data['routing']['RSU']+':'+str(rx_port)) # use the RX port

    #receive network interface
    rx_network = Network.TTNetwork(ip=self_ip, port=rx_port, msg_receiver=interface_manager.receiver_function)

    #wrapped function that needs to be synchronized
    local_fusion_fp = Fusion(interface_manager.send_token_queue)
    fusion_sync = WaitingMatching.InputSynchronizedFunction(Fusion.local_fusion, local_fusion_fp.input_queue)

    #wrapped function that needs to be synchronized
    actuation_fp = Actuation(interface_manager.send_token_queue)
    actuation_sync = WaitingMatching.InputSynchronizedFunction(Actuation.actuate, actuation_fp.input_queue, use_deadline=True)

    #register synchronization section with process/interface manager
    interface_manager.add_sync_process(pythag_sync.function_name, pythag_sync)

    # Init the camera
    # Setup our various settings
    settings = camera_recognition.Settings()
    settings.darknetPath = '../darknet/'
    camSpecs = camera_recognition.CameraSpecifications()
    camSpecs.cameraHeight = .2
    camSpecs.cameraAdjustmentAngle = 0.0

    # Lidar settings
    pipeFromC= "/home/jetson/Projects/slamware/fifo_queues/fifopipefromc"
    pipeToC= "/home/jetson/Projects/slamware/fifo_queues/fifopipetoc"

    # Set the time to start 10 seconds from now and let it rip!
    start_time = time.time() + 10
    interval = .125
    
    cameraThread = multiprocessing.Process(target=sourceImagesThread, args=(settings, camSpecs, interface_manager.send_token_queue, start_time, interval))
    cameraThread.start()
    lidarThread = multiprocessing.Process(target=sourceLIDARThread, args=(pipeFromC, pipeToC, interface_manager.send_token_queue, start_time, interval))
    lidarThread.start()

    #need this to make sure the main process doesn't finish and carry everything into the abyss
    pythag_sync.proc.join() 

if __name__ == "__main__":
    main()
