# Copyright 2021 Carnegie Mellon University
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import matplotlib.pyplot as plt
import linecache

def sinusoid_sampler(c_time, c_file):
    # global sq_state
    # if sq_state.get('count', None) == None:
    #     sq_state['count'] = 0
    
    # extracting the nth line
    if c_file == 0:
        filename = "data_0.txt"
    else:
        filename = "data_1.txt"
    particular_line = linecache.getline(c_file, c_time)
    split = particular_line.split(',')
    detections = []
    x = 0.0
    y = 0.0
    if particular_line != '':
        for idx in range(len(split)):
            if idx == 0:
                continue
            elif idx == 1:
                continue
            elif idx == 2:
                x = float(split[idx])
            elif idx == 3:
                y = float(split[idx])
            else:
                if idx % 2 == 1:
                    detections.append([float(split[idx-1]), float(split[idx])])

    return detections, [x, y]

def movingAverage(input1, input2, self1, self2):
    # global sq_state
    # if sq_state.get('match_and_kalman', None) == None:
    #     sq_state['count'] = 0

    #sq_state['count'] = count + 1
    ourself_list = []
    ourself_list.append(self1)
    ourself_list.append(self2)

    observation_list = []
    for each in input1:
        observation_list.append(each) 

    for each in input2:
        observation_list.append(each)

    return observation_list, ourself_list
    

def streamify_test(trigger):
    file_1 = "data_0.txt"
    file_2 = "data_1.txt"

    current_time = 0
    output_observations = []
    output_self = []
    for count in range(900):
        # collect a timestamp from a clock; needs a trigger whose arrival will make the timestamp be taken. This is for setting the start-tick of the STREAMify's periodic firing rule
        start_time = current_time

        # do the sampling with streamify'd SQs. Only one of the inputs needs the special sampling time interval (but it wouldn't hurt if all did) because the other const values have infinite timestamps
        sensor_1, self_1 = sinusoid_sampler(count+1, file_1) 
        sensor_2, self_2 = sinusoid_sampler(count+1, file_2) 

        # do some operations on the streams at runtime. Multiple streams will have their values synchronized by searching for intersections/overlaps in their time-intervals
        observations, self_pos = movingAverage(sensor_1, sensor_2, self_1, self_2)
        output_observations.append(observations)
        output_self.append(self_pos)

        current_time += 0.125

    x_val = []
    y_val = []
    for timestep in output_observations:
        for observation in timestep:
            x_val.append(observation[0])
            y_val.append(observation[1])

    self_x_val = []
    self_y_val = []
    for timestep in output_self:
        for observation in timestep:
            self_x_val.append(observation[0])
            self_y_val.append(observation[1])

    plt.plot(self_x_val,self_y_val,'ob')
    plt.plot(x_val,y_val,'xr')
    plt.show()

streamify_test(0)