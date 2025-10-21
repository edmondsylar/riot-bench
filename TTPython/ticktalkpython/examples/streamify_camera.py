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

import sys, os
sys.path.insert(0,os.path.abspath("./examples"))
import camera_recognition

@STREAMify #streamify is meant for generating sampled data streams
def camera_sampler(camera_specifications):
    global sq_state
    if sq_state.get('camera', None) == None:
        sq_state['camera'] = nano.Camera(camera_specifications.flip, camera_specifications.width, camera_specifications.height, camera_specifications.fps)
        frame_read = sq_state['camera'].camera.read()
    else: 
        frame_read = sq_state['camera'].camera.read()

    return frame_read

@SQify
def process_camera(camera_specifications, yolo_settings, camera_frame):
    global sq_state
    if sq_state.get('camera_recognition', None) == None:
        sq_state['camera_recognition'] = YOLO()
        sq_state['camera_recognition'].init(time.time(), yolo_settings, camera_specifications)
        coordinates, timestamp  = sq_state['camera_recognition'].readFrame(camera_frame)
    else: 
        coordinates, timestamp  = sq_state['camera_recognition'].readFrame(camera_frame)

    return coordinates

@GRAPHify
def streamify_test(trigger):
  # Setup our various camera settings
  yolo_settings = camera_recognition.Settings()
  yolo_settings.darknetPath = '../darknet/'
  camera_specifications = camera_recognition.CameraSpecifications()
  camera_specifications.cameraHeight = .2
  camera_specifications.cameraAdjustmentAngle = 0.0
  camera_specifications.fps = 60
  camera_specifications.width = 1280
  camera_specifications.height = 720 
  camera_specifications.flip = 2

  with TTClock.root() as root_clock:
    # collect a timestamp from a clock; needs a trigger whose arrival will make the timestamp be taken. This is for setting the start-tick of the STREAMify's periodic firing rule
    start_time = READ_TTCLOCK(trigger, TTClock=root_clock)
    N = 30
    # Setup the stop-tick of the STREAMify's firing rule
    stop_time = start_time + (1000000 * N) # sample for N seconds

    # create a sampling interval by copying the start and stop tick from token values to the token time interval
    sampling_time = VALUES_TO_TTTIME(start_time, stop_time)

    # do the sampling with streamify'd SQs. Only one of the inputs needs the special sampling time interval (but it wouldn't hurt if all did) because the other const values have infinite timestamps
    camera_frame = camera_sampler(camera_specifications, TTClock=root_clock, TTPeriod=125000, TTPhase=0, TTDataIntervalWidth=100000) 
    
   # do some operations on the streams at runtime. Multiple streams will have their values synchronized by searching for intersections/overlaps in their time-intervals
    output = process_camera(camera_specifications, yolo_settings, camera_frame)
    return output
