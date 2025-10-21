# Copyright 2021 Carnegie Mellon University
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from logging import root
from Deadline import TTDeadline
from SQ import STREAMify, GRAPHify
from Clock import TTClock
from Instructions import *

@STREAMify #streamify is meant for generating sampled data streams
def foo(a, b):
    global sq_state
    if sq_state.get('last_value', None) == None:
        sq_state['last_value'] = a*b
    #alternatively, imagine we read a sensor (like a syscall/ioctl)
    else: 
        sq_state['last_value'] += a*b

    value = sq_state['last_value'] 

    return value

@SQify 
def movingAverage(new_input):
    global sq_state

    count = sq_state.get('count', 0)
    average = (sq_state.get('average', 0) * count + new_input) / (count+1)


    sq_state['count'] = count + 1
    sq_state['average'] = average 

    return average
    

@GRAPHify
def streamify_test(trigger):
  a = 1
  b = 2
  with TTClock.root() as root_clock:
      #start node foo; need to attach timing information?
      with TTClock('child1', root_clock, 10, 0) as child:
        # collect a timestamp from a clock; needs a trigger whose arrival will make the timestamp be taken
        start_time = READ_TTCLOCK(trigger, TTClock=root_clock)
        stop_time = start_time + (1000000 * 10) # go for 10 seconds

        # #create a sampling interval 
        sampling_time = VALUES_TO_TTTIME(start_time, stop_time)
        
        # #copy the sampling interval to the input values to the STREAMify node; these input values will be treated as sticky tokens
        a_sample = COPY_TTTIME(a, sampling_time)
        b_sample = COPY_TTTIME(b, sampling_time) 
        sampling_output = COPY_TTTIME(0xc0ffeebabe, sampling_time) #force an output that will show the sampling interval we expect
        x = foo(a_sample, b_sample, TTClock=root_clock, TTPeriod=1000000, TTPhase=0, TTDataIntervalWidth=2000) #this function should be rerun every 5 ticks of the child clock, which runs 1 tick per 10 of the root; the function should execute on the (1 modulo 5) tick. The interval width lets us know how to label the output as it we read a timestamp after sampling a sensor. TTClock as the parameter name may be confusing. Note the kwargs are prepended with TT and do not appear in the function definition; these help specify the firing rule
        # x = foo(a, b, TTClock=root_clock, TTPeriod=100000, TTPhase=50000, TTDataIntervalWidth=200) 

          #TT-kwargs are for parameterizing control layer stuff; not the function itself. THere are no real optional parameters in TTPython (well, maybe there are, but they must be constant valued or meta-variables (e.g. clocks) such that they are not viewed as arcs)
          #when foo (streamify) starts, we mark a time and when it completes, we mark a time. The midpoint is approx. the sampling timestamp. That should reoverride the Time tag within the token, +- the TTDataIntervalWidth (default=1).
            #might decrease the width of the interval timing (clock sync?) uncertainty

        y = movingAverage(x)
        x_out = x+0
        return y
