# Copyright 2021 Carnegie Mellon University
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from logging import root
from SQ import STREAMify, GRAPHify
from Clock import TTClock
from Instructions import *

@STREAMify
def camera_sampler(trigger):
    import sys, time
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

    return [frame_read, camera_timestamp, time.time()]

@SQify 
def process_camera(cam_sample):
    import sys, time
    sys.path.insert(0, '/content/ticktalkpython/libraries')
    import camera_recognition
    global sq_state
    camera_frame = cam_sample[0]
    camera_timestamp = cam_sample[1]
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

    return [coordinates, processed_timestamp, cam_sample[2], time.time()]

@SQify 
def write_to_file(processed_camera):
    # Output filename
    output = processed_camera[0]
    camera_timestamp = processed_camera[1]
    outfile = "/content/ticktalkpython/output/example_1_output.txt"
    with open(outfile, 'a') as file:
        file.write('cam_time:' + str(camera_timestamp) + ', sys_proc_time:' + str(processed_camera[3]-processed_camera[2]) + ', output' + str(output) + "\n")
        print("Processed timestamp: " + str(camera_timestamp))
    return 1

@GRAPHify
def example_1_test(trigger):
    A_1 = 1
    with TTClock.root() as root_clock:
        # Workaround 
        # collect a timestamp from a clock; needs a trigger whose arrival will make the timestamp be taken. This is for setting the start-tick of the STREAMify's periodic firing rule
        start_time = READ_TTCLOCK(trigger, TTClock=root_clock)
        N = 50
        # Setup the stop-tick of the STREAMify's firing rule
        stop_time = start_time + (1000000 * N) # sample for N seconds

        # create a sampling interval by copying the start and stop tick from token values to the token time interval
        sampling_time = VALUES_TO_TTTIME(start_time, stop_time)
        
        # copy the sampling interval to the input values to the STREAMify node; these input values will be treated as sticky tokens, and define the duration over which STREAMify'd nodes must run
        sample_window = COPY_TTTIME(A_1, sampling_time)

        cam_sample = camera_sampler(sample_window, TTClock=root_clock, TTPeriod=750000, TTPhase=0, TTDataIntervalWidth=250000) 
    
        processed_camera = process_camera(cam_sample)
        
        write = write_to_file(processed_camera)