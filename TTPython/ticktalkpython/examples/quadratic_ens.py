# Copyright 2021 Carnegie Mellon University
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# TTPython
#
# Framework for formally defining the TickTalk core language concepts
# as extensions to Python 3.x
#
# Copyright (c) 2021 by Bob Iannucci.  All rights reserved worldwide.

from tt.Time import TTTime
from tt.Clock import TTClock
from tt.Token import TTToken
from tt.SQ import SQify
from tt.SQ import GRAPHify
from tt.Instructions import *
from tt.Deadline import TTDeadline
from tt.PlanB import TTPlanB
from tt.Query import TTConstraint
from math import sqrt

@SQify
def quadratic_roots(a, b, c):
    sqrt_term = sqrt(b**2 - 4 * a * c)
    a_times_2 = 2 * a
    return ((-b + sqrt_term) / a_times_2, (-b - sqrt_term) / a_times_2)

@GRAPHify
def main(a, b, c):
    with TTClock.root() as CLOCK:
        with TTConstraint(components=["waterHeight"]):
            sqrt_term = SQRT((b * b) - 4 * a * c)
            a_times_2 = 2 * a
        with TTConstraint(name="ens2"):
            root_1 = (-b + sqrt_term) / a_times_2
            root_2 = (-b - sqrt_term) / a_times_2
        return TUPLE_2(root_1, root_2)
