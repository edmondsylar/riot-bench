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


@STREAMify  # streamify is meant for generating sampled data streams
def sample_magnetometer(A, f, phi):
    from math import cos, pi

    global sq_state
    if sq_state.get('count', None) == None:
        sq_state['count'] = 1
    # alternatively, imagine we read a sensor (like a syscall/ioctl)

    sample = A - (A * cos(sq_state['count'] * 2 * f / pi + phi))
    sq_state['count'] += 1

    return sample


@SQify
def calculate_car_speed(sense1_token, sense2_token):
    cutoff = 1.71
    distance = 5 # meters

    sense1 = sense1_token.value
    sense2 = sense2_token.value

    global sq_state
    if sq_state.get('saw_car', None) == None:
        sq_state['saw_car'] = False
        sq_state['last_time'] = 0

    if sense1 < cutoff and sq_state.get['saw_car'] == False:
        return None
    else:
        if sq_state.get['saw_car'] == False:
            sq_state['prev_time'] = sense1_token.time
            sq_state['saw_car'] = True
        if sense2 < cutoff:
            return "2nd sensor hasn't seen car yet!"
        sq_state['saw_car'] = False
        return distance / (
            (sense2_token.time.stop_tick - sense2_token.time.start_tick) -
            (sq_state['prev_time'].stop_tick -
             sq_state['prev_time'].start_tick) / 1e6) # for m/s


@SQify
def movingAverage(new_input):
    global sq_state

    if not isinstance(new_input, float):
        return

    count = sq_state.get('count', 0)
    average = (sq_state.get('average', 0) * count + new_input) / (count + 1)

    sq_state['count'] = count + 1
    sq_state['average'] = average

    return average


@GRAPHify
def streamify_test(trigger):
    A_1 = 1
    A_2 = 1
    f = 0.25
    phi_1 = 0
    phi_2 = -0.5

    with TTClock.root() as root_clock:
        # collect a timestamp from a clock; needs a trigger whose arrival
        # will make the timestamp be taken. This is for setting the start-tick
        # of the STREAMify's periodic firing rule
        start_time = READ_TTCLOCK(trigger, TTClock=root_clock)
        N = 5
        # Setup the stop-tick of the STREAMify's firing rule
        stop_time = start_time + (1000000 * N)  # sample for N seconds

        # create a sampling interval by copying the start and stop tick from
        # token values to the token time interval
        sampling_time = VALUES_TO_TTTIME(start_time, stop_time)

        # copy the sampling interval to the input values to the STREAMify node;
        # these input values will be treated as sticky tokens, and define the
        # duration over which STREAMify'd nodes must run
        A1_sample = COPY_TTTIME(A_1, sampling_time)
        A2_sample = COPY_TTTIME(A_2, sampling_time)

        # do the sampling with streamify'd SQs. Only one of the inputs needs the
        # special sampling time interval (but it wouldn't hurt if all did)
        # because the other const values have infinite timestamps
        inductance1 = sample_magnetometer(A1_sample,
                                     f,
                                     phi_1,
                                     TTClock=root_clock,
                                     TTPeriod=500000,
                                     TTPhase=0,
                                     TTDataIntervalWidth=100000)
        inductance2 = sample_magnetometer(A2_sample,
                                     f,
                                     phi_2,
                                     TTClock=root_clock,
                                     TTPeriod=500000,
                                     TTPhase=0,
                                     TTDataIntervalWidth=100000)

        speed = calculate_car_speed(inductance1,
                                    inductance2,
                                    TTExecuteOnFullToken=True)

        # do some operations on the streams at runtime. Multiple streams will
        # have their values synchronized by searching for intersections/overlaps
        # in their time-intervals
        y = movingAverage(speed)
        return speed
