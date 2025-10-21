# Copyright 2021 Carnegie Mellon University
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.# TTPython
#
# Framework for formally defining the TickTalk core language concepts
# as extensions to Python 3.x
#
# Created by Bob Iannucci 2021
#

from Time import TTTime
from Clock import TTClock
from Token import TTToken
from SQ import SQify
from Instructions import *
from Deadline import TTDeadline
from PlanB import TTPlanB
from math import sqrt

import time

@SQify
def quadratic_roots(a, b, c):
    sqrt_term = sqrt(b**2 - 4 * a * c)
    a_times_2 = 2 * a
    return ((-b + sqrt_term) / a_times_2, (-b - sqrt_term) / a_times_2),

def planB_handler(exception_type, exception_value, traceback):
    print(f"Entered the PlanB handler for Exception: {exception_value}")
    return

def clock_ancestry():
    # root_clock = TTClock("local_root")
    root_clock = TTClock.root()
    # Create a clock derived from root
    c1 = TTClock("root/c1", root_clock, 2, 1)
    c2 = TTClock("root/c2", root_clock, 5, 4)
    c3 = TTClock("root/c1/c3", c1, 3, 4)
    assert(TTClock.common_ancestor(root_clock,root_clock) == root_clock)
    assert(TTClock.common_ancestor(root_clock,c1) == root_clock)
    assert(TTClock.common_ancestor(c1,c2) == root_clock)
    assert(TTClock.common_ancestor(c1,c3) == c1)
    assert(TTClock.common_ancestor(c2,c3) == root_clock)
    t2_c1 = TTTime(c1, 4, 6)
    assert(t2_c1.ancestor_time(root_clock) == TTTime(root_clock, 9, 13))
    t3_c2 = TTTime(c2, 2, 3)
    assert(t3_c2.ancestor_time(root_clock) == TTTime(root_clock, 14, 19))
    t4_c3 = TTTime(c3, 1, 3)
    assert(t4_c3.ancestor_time(c1) == TTTime(c1, 7, 13))
    assert(t4_c3.ancestor_time(root_clock) == TTTime(root_clock, 15, 27))

def time_creation():
    # root_clock = TTClock("local_root")
    root_clock = TTClock.root()
    t1 = TTTime(root_clock, 0, 1)
    assert(t1.n_ticks() == 1)
    c1 = TTClock("root/c1", root_clock, 2, 1)
    c2 = TTClock("root/c2", root_clock, 5, 4)
    c3 = TTClock("root/c1/c3", c1, 3, 4)
    # Validate the translation of intervals to parent clock domains
    t2_c1 = TTTime(c1, 4, 6)
    assert(t2_c1.ancestor_time(root_clock) == TTTime(root_clock, 9, 13))
    t3_c2 = TTTime(c2, 2, 3)
    assert(t3_c2.ancestor_time(root_clock) == TTTime(root_clock, 14, 19))
    t4_c3 = TTTime(c3, 1, 3)
    assert(t4_c3.ancestor_time(c1) == TTTime(c1, 7, 13))
    assert(t4_c3.ancestor_time(root_clock) == TTTime(root_clock, 15, 27))
    assert(TTTime.common_ancestor_overlap_time(t3_c2, t4_c3) == TTTime(root_clock, 15, 19))
    assert(TTTime.common_ancestor_overlap_time(t2_c1, t4_c3) == None)
    # Check to see that ancestor errors are caught
    try:
        t4_c3.ancestor_time(c2)
    except Exception as error:
        type, description = error.args
        assert(type == "Ancestor")
    time_list = [t1, t2_c1, t3_c2, t4_c3]
    assert(list(map(lambda x: x.start_tick, time_list)) == [0, 4, 2, 1])
    time_list = [t1, t2_c1, t3_c2, t4_c3]
    assert(TTTime.common_ancestor_overlap_time_multi(*time_list) == None)
    time_list = [t3_c2, t1]
    assert(TTTime.common_ancestor_overlap_time_multi(*time_list) == None)
    time_list = [t3_c2, t4_c3]
    assert(TTTime.common_ancestor_overlap_time_multi(*time_list) == TTTime(root_clock, 15, 19))

def token_processing():
    # root_clock = TTClock("local_root")
    root_clock = TTClock.root()
    # Create a time-tagged token using that interval and the derived clock
    time_1 = TTTime(root_clock, 2, 1024)
    token_1 = TTToken(2, time_1)
    assert(token_1.value == 2)
    assert(token_1.time.start_tick == 2)

    # Here is the TTPython equivalent of "Hello, World" -- the first processing of tokens through an SQ:
    result_token_list = ADD(token_1, token_1)
    assert(len(result_token_list) == 1)
    result_token = result_token_list[0]
    assert(result_token.value == 4)
    assert(result_token.time == time_1)

    # Now let's try with two different tokens, same time
    token_2 = TTToken(42, time_1)
    result_token_list = ADD(token_1, token_2)
    assert(len(result_token_list) == 1)
    result_token = result_token_list[0]
    assert(len(result_token_list) == 1)
    assert(result_token.value == 44)
    assert(result_token.time == time_1)

    # Two different, staggered but overlapping, time ranges
    time_3 = TTTime(root_clock, 1000, 2000)
    token_3 = TTToken(100, time_3)
    result_token_list = ADD(token_1, token_3)
    assert(len(result_token_list) == 1)
    result_token = result_token_list[0]
    assert(result_token.value == 102)
    assert(result_token.time.start_tick == 1000)
    assert(result_token.time.stop_tick == 1024)

    # Here is a two-instruction TTPython program:
    result_token_list = ADD(ADD(token_1, token_2)[0], token_3)
    assert(len(result_token_list) == 1)
    result_token = result_token_list[0]
    assert(result_token.value == 144)
    assert(result_token.time.start_tick == 1000)
    assert(result_token.time.stop_tick == 1024)

    token_4 = (TTToken(0, TTTime(root_clock, 123456, 123457)))
    # Check to see that token-time-mismatch errors are caught
    try:
        result_token_list = ADD(token_1, token_4)
    except Exception as error:
        type, description = error.args
        assert(type == "Time")

    c1 = TTClock("root/c1", root_clock, 2, 1)
    c2 = TTClock("root/c2", root_clock, 5, 4)
    c3 = TTClock("root/c1/c3", c1, 3, 4)
    t3_c2 = TTTime(c2, 2, 3)
    t4_c3 = TTTime(c3, 1, 3)
    token_t2_c1 = TTToken(2, t3_c2)
    token_t4_c3 = TTToken(3, t4_c3)
    result_token_list = ADD(token_t2_c1, token_t4_c3)
    assert(len(result_token_list) == 1)
    result_token = result_token_list[0]
    assert(result_token.value == 5)
    assert(result_token.time == TTTime(root_clock, 15, 19))

    # Three input tokens to a slightly more complicated Python SQ body
    token_a = TTToken(1, time_1)
    token_b = TTToken(0, time_1)
    token_c = TTToken(-4, time_1)
    result_token_list = quadratic_roots(token_a, token_b, token_c)
    assert(len(result_token_list) == 1)
    result_token = result_token_list[0]
    assert(result_token.value == (2.0, -2.0))

    # The first deadline-including TTPython program -- here, the deadline will always trigger
    try:
        with TTDeadline(c3, 0):
            time.sleep(0.005)
            quadratic_roots(token_a, token_b, token_c)
        raise Exception("UntriggeredError", "Deadline should have triggered an error but did not")
    except Exception as error:
        type, description = error.args
        assert(type == "Deadline")

    # And now with PlanB:
    with TTPlanB(planB_handler):
        with TTDeadline(c3, 1000):
            quadratic_roots(token_a, token_b, token_c)


def all_tests():
    clock_ancestry()
    time_creation()
    token_processing()
    # Will only get here if there are no assertion failures
    print("All tests PASSED")

if __name__ == "__main__":
    all_tests()
