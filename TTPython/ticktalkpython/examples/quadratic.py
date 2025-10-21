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
from math import sqrt

# A PlanB handler is just good old Python (no wrapping)
def planB_handler(exception_type, exception_value, traceback):
    print(f"Entered the PlanB handler for Exception: {exception_value}")
    # Returning True will allow execution to continue; False causes a fatal exception
    return False

# SQify wraps a vanilla Python function and processes it with timed token semantics.
# The input arguments are then expected to be timed tokens, and the returned
# result is turned into a timed token.  The time on the output is the max
# overlap of the times on the inputs in terms of the common ancestor clock
@SQify
def quadratic_roots(a, b, c):
    sqrt_term = sqrt(b**2 - 4 * a * c)
    a_times_2 = 2 * a
    return ((-b + sqrt_term) / a_times_2, (-b - sqrt_term) / a_times_2)

# Every TTPython program can have many SQified functions (above), but
# it then has one expression at the end.  This expression must 
# generate the input tokens, and the result will be a token, assuming
# the body of the expression is built solely from SQified functions.
# @GRAPHify
# def main(a, b, c):
#     with TTClock.root() as CLOCK:
#         with TTPlanB(planB_handler):            # will catch deadline errors
#             with TTDeadline(CLOCK, 100):          # set a bogus 1 microsecond deadline so we will trigger the PlanB handler
#                 return quadratic_roots(a, b, c)

# # Execute the program
# print(main(1, 0, -4))

# @GRAPHify
# def main(a, b, c):
#     with TTClock.root() as CLOCK:
#         with TTPlanB(planB_handler):            
#             with TTDeadline(CLOCK, 500):          
#                 const_4 = CONST(a, const=4)
#                 val_ac = MULT(a, c)
#                 val_4ac = MULT(const_4, val_ac)
#                 sqrt_term = SQRT(SUB(MULT(b, b), val_4ac))
#                 a_times_2 = MULT(CONST(a, const=2), a)
#                 neg_b = SUB(CONST(a, const=0), b)
#                 root_1 = DIV(ADD(neg_b, sqrt_term), a_times_2)
#                 root_2 = DIV(SUB(neg_b, sqrt_term), a_times_2)
#                 return TUPLE_2(root_1, root_2)

@GRAPHify
def main(a, b, c):
    with TTClock.root() as CLOCK:
        with TTPlanB(planB_handler):            
            with TTDeadline(CLOCK, 500):        
                sqrt_term = SQRT((b * b) - 4 * a * c)
                a_times_2 = 2 * a
                root_1 = (-b + sqrt_term) / a_times_2
                root_2 = (-b - sqrt_term) / a_times_2
                return TUPLE_2(root_1, root_2)

print(main(1, 0, -4))