# Copyright 2021 Carnegie Mellon University
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# Created by Bob Iannucci 2021
#

# TTPlanB is intended as a wrapper that invokes a handler if a timing or functional
# error is encountered when processing a block of code.  
class TTPlanB():
    '''
    ``TTPlanB`` objects are used as part of a ``with...`` construct
    to establish an error handler that encompasses a block
    of TTPython code.

    NOTE: the current implementation is experimental and subject to change

    :param handler: a function that is invoked if an error is signalled; defined with the parameter list ``(exception_type, exception_value, traceback)``
    :type handler: function 
    '''
    def __init__(self, handler):
        self.handler = handler

    def __enter__(self):
        return

    def __exit__(self, exception_type, exception_value, traceback):
        if exception_type:
            return self.handler(exception_type, exception_value, traceback)
        else:
            return True