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

@STREAMify #streamify is meant for generating sampled data streams
def sinusoid_sampler(c_time, c_file):
    import linecache

    if c_file == 0:
        filename = "data_0.txt"
    else:
        filename = "data_1.txt"
    particular_line = linecache.getline(c_file, c_time)
    split = particular_line.split(',')
    detections = []
    for idx in range(len(split)):
        if idx == 0:
            x = float(split[idx])
        elif idx == 1:
            y = float(split[idx])
        elif idx == 2:
            yaw = float(split[idx])
        else:
            if idx % 2 == 0:
                detections.append((float(split[idx-1]), float(split[idx])))

    return detections

@SQify 
def combineDetections(input1, input2):
    current_list = []
    for each in input1:
        current_list.append(each) 

    for each in input2:
        current_list.append(each)

    return current_list
    

@GRAPHify
def streamify_test(trigger):
  A_1 = 1
  A_2 = 2

  with TTClock.root() as root_clock:
    # collect a timestamp from a clock; needs a trigger whose arrival will make the timestamp be taken. This is for setting the start-tick of the STREAMify's periodic firing rule
    start_time = READ_TTCLOCK(trigger, TTClock=root_clock)
    N = 30
    # Setup the stop-tick of the STREAMify's firing rule
    stop_time = start_time + (1000000 * N) # sample for N seconds

    # create a sampling interval by copying the start and stop tick from token values to the token time interval
    sampling_time = VALUES_TO_TTTIME(start_time, stop_time)
    
    # copy the sampling interval to the input values to the STREAMify node; these input values will be treated as sticky tokens, and define the duration over which STREAMify'd nodes must run
    A1_sample = COPY_TTTIME(A_1, sampling_time)
    A2_sample = COPY_TTTIME(A_2, sampling_time) 

    # do the sampling with streamify'd SQs. Only one of the inputs needs the special sampling time interval (but it wouldn't hurt if all did) because the other const values have infinite timestamps
    sensor_1 = sinusoid_sampler(A1_sample, A_1, TTClock=root_clock, TTPeriod=125000, TTPhase=0, TTDataIntervalWidth=10000) 
    sensor_2 = sinusoid_sampler(A2_sample, A_2, TTClock=root_clock, TTPeriod=125000, TTPhase=0, TTDataIntervalWidth=10000) 

    # do some operations on the streams at runtime. Multiple streams will have their values synchronized by searching for intersections/overlaps in their time-intervals
    output = combineDetections(sensor_1, sensor_2)
    return output
    