# Copyright 2021 Carnegie Mellon University
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


class Tag():
    def __init__(self, func_name:str, port_num_or_name:(int, str), start:float, stop:float):
        self.func_name = func_name
        if isinstance(port_num_or_name, str):
            self.port_name = port_num_or_name
            self.port_num = None
        elif isinstance(port_num_or_name, int) and port_num_or_name >= 0:
            self.port_number = port_num_or_name
            self.port_name = None
        else:
            raise TypeError('Invalid port given')
    
        self.start = start
        self.stop = stop
        if stop < start:
            raise TypeError('Stop value of interval is less than Start; this is not a valid time interval')

    def __repr__(self):
        #TODO: conditional on port name vs. num

        return '<TTCompTag:: id:' + hex(id(self)) + " func: " + self.func_name + " p-name: " + self.port_name + " p-num: " + str(self.port_num) + f' time:({self.start}, {self.stop})>>'
