# Copyright 2021 Carnegie Mellon University
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import time, json, sys
# I don't understand why but shapely must be imported in this file
# or the import will fail in the included files!
from shapely.geometry import box
from shapely.affinity import rotate, translate

sq_state = {}

def camera_sampler(trigger):
    sys.path.insert(0, '/content/ticktalkpython/libraries')
    import camera_recognition
    global sq_state
    if sq_state.get('camera', None) == None:
        # Setup our various camera settings
        camera_specifications = camera_recognition.Settings()
        camera_specifications.darknetPath = '/content/darknet/'
        camera_specifications.useCamera = False
        camera_specifications.inputFilename = '/content/yolofiles/cav1/live_test_output.avi'
        camera_specifications.camTimeFile = '/content/yolofiles/cav1/cam_output.txt'
        camera_specifications.cameraHeight = .2
        camera_specifications.cameraAdjustmentAngle = 0.0
        camera_specifications.fps = 60
        camera_specifications.width = 1280
        camera_specifications.height = 720 
        camera_specifications.flip = 2
        sq_state['camera'] = camera_recognition.Camera(camera_specifications)
    frame_read, camera_timestamp = sq_state['camera'].takeCameraFrame()

    return [frame_read, camera_timestamp]

def process_camera(camera_data):
    sys.path.insert(0, '/content/ticktalkpython/libraries')
    import camera_recognition
    global sq_state
    camera_frame = camera_data[0]
    camera_timestamp = camera_data[1]
    if sq_state.get('camera_recognition', None) == None:
        # Setup our various camera settings
        camera_specifications = camera_recognition.Settings()
        camera_specifications.darknetPath = '/content/darknet/'
        camera_specifications.useCamera = False
        camera_specifications.inputFilename = '/content/yolofiles/cav1/live_test_output.avi'
        camera_specifications.camTimeFile = '/content/yolofiles/cav1/cam_output.txt'
        camera_specifications.cameraHeight = .2
        camera_specifications.cameraAdjustmentAngle = 0.0
        camera_specifications.fps = 60
        camera_specifications.width = 1280
        camera_specifications.height = 720 
        camera_specifications.flip = 2
        sq_state['camera_recognition'] = camera_recognition.ProcessCamera(camera_specifications)

    coordinates, processed_timestamp = sq_state['camera_recognition'].processCameraFrame(camera_frame, camera_timestamp)

    return [coordinates, processed_timestamp]

def lidar_sampler(trigger):
    global sq_state
    if sq_state.get('lidar', None) == None:
        # LIDAR filename
        lidar_file = '/content/yolofiles/cav0/lidar_output.txt'
        f = open(lidar_file, 'r+')
        sq_state['lidar'] = f.readlines()
        sq_state['lidar_time_idx'] = 0
        f.close()
    lidar_timestamp = float(sq_state['lidar'][sq_state['lidar_time_idx']])
    localization = json.loads(sq_state['lidar'][sq_state['lidar_time_idx'] + 1])
    lidar_frame = json.loads(sq_state['lidar'][sq_state['lidar_time_idx'] + 2])
    sq_state['lidar_time_idx'] += 3

    return [localization, lidar_frame, lidar_timestamp]

def process_lidar(lidar_package):
    sys.path.insert(0, '/content/ticktalkpython/libraries')
    import lidar_recognition, sensor
    global sq_state
    localization = lidar_package[0]
    lidar_frame = lidar_package[1]
    lidar_timestamp = lidar_package[2]
    if sq_state.get('lidar_recognition', None) == None:
        sq_state['lidar_recognition'] = lidar_recognition.LIDAR(lidar_timestamp)
        sq_state['lidarsensor'] = sensor.Sensor("M1M1", 0.0, 360, 15.0,
                                               0, .05, .05, .083)
        lidarcoordinates, lidartimestamp = sq_state['lidar_recognition'].processLidarFrame(lidar_frame,
                                                                                lidar_timestamp,
                                                                                localization[0],
                                                                                localization[1], 
                                                                                localization[2],
                                                                                sq_state['lidarsensor'])
    else: 
        lidarcoordinates, lidartimestamp = sq_state['lidar_recognition'].processLidarFrame(lidar_frame,
                                                                                lidar_timestamp,
                                                                                localization[0],
                                                                                localization[1], 
                                                                                localization[2],
                                                                                sq_state['lidarsensor'])
    return [localization, lidarcoordinates, lidartimestamp]

def process_fusion(processed_camera, processed_lidar):
    sys.path.insert(0, '/content/ticktalkpython/libraries')
    import local_fusion, planning_control, shared_math
    global sq_state
    localization = processed_lidar[0]
    lidar_output = processed_lidar[1]
    lidar_timestamp = processed_lidar[2]
    cam_output = processed_camera[0]
    camera_timestamp = processed_camera[1]
    if sq_state.get('fusion', None) == None:
        # Fusion node
        sq_state['fusion'] = local_fusion.FUSION(0, 0)
        # Planner node
        sq_state['planner'] = planning_control.Planner()
    
    # Call the fusion algorithm
    fusion_result = []
    sq_state['fusion'].processDetectionFrame(local_fusion.CAMERA, camera_timestamp, cam_output, .25, 1)
    sq_state['fusion'].processDetectionFrame(local_fusion.LIDAR, lidar_timestamp, lidar_output, .25, 1)
    fusion_result = sq_state['fusion'].fuseDetectionFrame(1, sq_state['planner'])

    # Convert to world coordinate system
    results = []
    for idx, each in enumerate(fusion_result):
        new = shared_math.rotate((0, 0), (float(each[1]), float(each[2])), float(localization[2]))
        sensed_x = new[0] + localization[0]
        sensed_y = new[1] + localization[1]
        results.append([sensed_x, sensed_y])

    return results

def write_to_file(fusion_result):
    # Output filename
    import time
    outfile = "/content/ticktalkpython/output/out_lidar_camera_fusion_test.txt"
    with open(outfile, 'a') as file:
        file.write(str(fusion_result) + "\n")
        print("Processed fusion @ ", time.time())

def streamify_test(trigger):
    # Adjust timing interval
    interval = 1.0
    # Start on an even number
    nextTime = (time.time() % 1.0) + 1
    while(True):
        if time.time() > nextTime:
            camera_sample = camera_sampler(trigger) 

            lidar_sample = lidar_sampler(trigger) 

            cam_output = process_camera(camera_sample)

            lidar_output = process_lidar(lidar_sample)

            fusion_result = process_fusion(cam_output, lidar_output)

            write_to_file(fusion_result)
            
            nextTime = nextTime + interval

trigger = 1
streamify_test(1)