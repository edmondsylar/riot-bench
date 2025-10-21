# Copyright 2021 Carnegie Mellon University
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import time, sys

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

    return frame_read, camera_timestamp

def process_camera(camera_frame, camera_timestamp):
    sys.path.insert(0, '/content/ticktalkpython/libraries')
    import camera_recognition
    global sq_state
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

    return coordinates, processed_timestamp

def write_to_file(output, camera_timestamp):
    # Output filename
    outfile = "/content/ticktalkpython/output/out_test.txt"
    with open(outfile, 'a') as file:
        file.write(str(camera_timestamp) + ', ' + str(output) + "\n")
        print("Processed timestamp: " + str(camera_timestamp))

def streamify_test(trigger):
  # Adjust timing interval
  interval = 1.0
  # Start on an even number
  nextTime = (time.time() % 1.0) + 1
  while(True):
      if time.time() > nextTime:
        start_time = time.time()

        camera_frame, camera_timestamp = camera_sampler(trigger) 

        output, proccessed_timestamp = process_camera(camera_frame, camera_timestamp)
    
        write_to_file(output, camera_timestamp)

        print( "  system processing time: ", time.time()-start_time )
        
        nextTime = nextTime + interval

trigger = 1
streamify_test(1)