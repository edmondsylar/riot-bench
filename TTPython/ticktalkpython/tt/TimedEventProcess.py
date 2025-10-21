# Copyright 2021 Carnegie Mellon University
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import sys, math, queue
import simpy
import threading, time

from Clock import TTClock
from Time import TTTime
from Token import TTToken

import DebugLogger
logger = DebugLogger.get_logger('TimedEventProcess')


def delayed_release_phy(duration, released_value, callback_func):
    '''
    A function to delay a physical process by a set amount, calling the callback on the provided value when the delay expires. The physical variant uses time.sleep (which takes a value in seconds) to wait. 

    :param duration: The number of seconds to wait
    :type duration: float
    :param released_value: The value to release
    :type released_value: Any 
    :param callback_func: The function to call with a single argument (``released_valued``)
    :type callback_func: function
    '''
    logger.debug('Wait %f seconds to release %s to function' % (duration, released_value))
    time.sleep(duration)
    callback_func(released_value)


def delayed_release_sim(duration, released_value, callback_func, sim:simpy.Environment):
    '''
    A function to delay a simulated process by a set amount, calling the callback on the provided value when the delay expires. The simulated will yield this function (meaning it is a generator and must be called using sim.process, else the program hangs); the duration is in the number of simulation ticks to delay the process

    :param duration: The number of ticks to wait
    :type duration: float
    :param released_value: The value to release
    :type released_value: Any 
    :param callback_func: The function to call with a single argument (``released_valued``)
    :type callback_func: function
    '''
    logger.debug('Wait %f simulation ticks to release %s to function' % (duration, released_value))
    yield sim.timeout(duration)
    callback_func(released_value)


def wait(duration, released_value, callback_func, sim=None, allow_late=False):
    '''
    Wait for a set duration for calling callback on a singular input

    :param duration: the amount of time to wait, specifically in terms of the root clock
    :type duration: ``float``
    :param released_value: The value to be relased to the callback when the delay expires
    :type released_value: ``Any``, but should be serializable (or pickleizable), depending on usage
    :param callback_func: The function to call with the released_value
    :type callback_fund: ``func``
    :param sim: Optional simulation environment in case of simulated runtime
    :type sim: ``simpy.Environment``

    :rtype: None
    '''
    if duration < 0 and allow_late:
        callback_func(released_value)
    else:
        if sim and isinstance(sim, simpy.Environment):
            sim.process(delayed_release_sim(duration, released_value, callback_func, sim))
        else:
            threading.Thread(target=delayed_release_phy, args=[duration, released_value, callback_func]).start()


def wait_until(clock, release_time, released_value, callback_func, sim=None, allow_late=False):
    '''
    Wait for until some time to call a callback on a singular input

    :param clock: The reference clock for the release time; this should be the ROOT clock at this time. 
    :type clock: ``Clock.TTClock``
    :param release_time: the time to release the value, specifically in terms of the root clock
    :type duration: ``float``
    :param released_value: The value to be relased to the callback when the delay expires
    :type released_value: ``Any``, but should be serializable (or pickleizable), depending on usage
    :param callback_func: The function to call with the released_value
    :type callback_fund: ``func``
    :param sim: Optional simulation environment in case of simulated runtime
    :type sim: ``simpy.Environment``

    :rtype: None
    '''
    assert clock.is_root(), 'Non-root waiting is not currently supported'
    current_time = clock.now() 
    duration = (release_time - current_time)/clock.ticks_per_second() #assume the release time is in the same timeline as the root clock

    if duration > 0:
        wait(duration, released_value, callback_func, sim=sim, allow_late=allow_late)
    elif allow_late:
        callback_func(released_value)

