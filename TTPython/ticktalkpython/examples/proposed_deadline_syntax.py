# Copyright 2021 Carnegie Mellon University
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## Example streamify
from Deadline import TTFinishByOtherwise
from Instructions import READ_TTCLOCK
from SQ import STREAMify, GRAPHify
from Instructions import *

@STREAMify #streamify is meant for generating sampled data streams
def foo(a, b):
  global sq_state

  #alternatively, imagine we read a sensor (like a syscall/ioctl)
  if sq_state.get('last_value', None) == None:
    sq_state['last_value'] = 1

  value = sq_state['last_value']
  sq_state['last_value'] += a*b

  return value

def bar(a, b):
    return a*b

def callback(x):
  if x % 2 == 1:
    return 1
  return 0

@SQify
def timed_multiply(x, y):
  import time
  time.sleep(0.1)
  return x * y

@SQify
def const_val():
  return 0

@GRAPHify
def deadline_test(trigger):
  a = 1
  b = 2
  # with TTClock('ROOT', None, 1, 0) as root_clock:
  with TTClock('ROOT') as root_clock:
      #start node foo; need to attach timing information?
    start_time = READ_TTCLOCK(trigger, TTClock=root_clock)
    stop_time = start_time + (1000000 * 1) # go for 1 second

    # #create a sampling interval
    sampling_time = VALUES_TO_TTTIME(start_time, stop_time)

    # #copy the sampling interval to the input values to the STREAMify node; these input values will be treated as sticky tokens
    a_sample = COPY_TTTIME(a, sampling_time)
    b_sample = COPY_TTTIME(b, sampling_time)
    x = foo(a_sample, b_sample, TTClock=root_clock, TTPeriod=400000, TTPhase=500, TTDataIntervalWidth=1000)

    t = READ_TTCLOCK(x, TTClock=root_clock) + 100 # extract timestamp from tag into the data plane (value field)
    y = timed_multiply(x, 2)
    #should TTDeadline be its own special SQ? We say yes; either returns y or whatever the TTPlanB returns (if any). t's stop_tick ditates when the timeout expires.
    # q = TTFinishByOtherwise(y, TTTimeDeadline=t, TTPlanB=lambda asdf: 1, TTWillContinue=True) #if deadline fails, it produces a separate value (similar to ternary operation: a = y if clock.now < t else None)
    s = TTFinishByOtherwise(y, TTTimeDeadline=t, TTPlanB=const_val(), TTWillContinue=True) #does callback return? Use a flag
    return s
    # z = bar(q, s) #bar(a, b), bar(None, b), bar(a, None), bar(None, None)
