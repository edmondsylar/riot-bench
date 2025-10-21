# Copyright 2021 Carnegie Mellon University
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Created by Bob Iannucci 2021
#

from Clock import TTClock

###FIXME: This entire mechanism, from compilation to runtime, needs to be
# redesigned and properly implemented. Deadlines are a bit hard because unless
# we only set the deadline once, we need to produce new ones relative to some
# start time... how do we describe that start time and communicate it to the SQ
# that will handle its expiry? Leveraging periodicity is one attractive option,
# especially when the network can fail, but may be underspecified (especially
# if the graph can branch based on conditions (which doesn't seem to be possible
# as of this writing)). -Reese 7/26/21

# Deadlines are always with reference to a specific clock and are
# expressed in terms of ticks of that clock
class TTFinishByOtherwise():
    def __init__(self, data_value, time_deadline, planB, will_return):
        self.data_value = data_value
        self.time_deadline = time_deadline
        self.planB = planB
        self.will_return = will_return

class TTDeadline():
    '''
    ``TTDeadline`` objects are used as part of a ``with...`` construct
    to annotate an ``SQ`` with deadline information.  Each ``SQ`` tagged with
    a ``TTDeadline`` must only be so tagged within the context of a ``TTPlanB`` handler.

    :param clock: the clock to be used in implementing this deadline
    :type clock: TTClock
    :param interval: the number of ticks of ``clock`` that indicates the **maximum** time that can elapse before a deadline violation is signalled
    :type interval: int
    '''
    def __init__(self, clock, interval):
        self.clock = clock
        self.deadline_interval = interval

    def __enter__(self):
        self.time_started = self.clock.now()
        return

    def __exit__(self, exception_type, exception_value, traceback):
        self.time_ended = self.clock.now()
        actual_interval = self.time_ended - self.time_started
        if (actual_interval > self.deadline_interval):
            raise Exception('Deadline', f"Actual: {actual_interval} ticks   Deadline: {self.deadline_interval} ticks")
        return
