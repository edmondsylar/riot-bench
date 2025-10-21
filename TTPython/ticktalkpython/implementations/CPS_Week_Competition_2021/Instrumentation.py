# Copyright 2021 Carnegie Mellon University
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import os, time
import multiprocessing 
import queue
import Tag

class TimeLogItem():
    def __init__(self, timestamp, function_name:str, context_str:str):
        '''
        Create an item that will be logged as part of timing instrumentation
        
        timestamp: A timestamp, nominally in seconds as read from time.time(). This should reflect system time
        function_name: A function name to provide context for where in the code this log item was generated. It does not need to actually be the function name, but should give enough context to figure where this entry originated
        context_str: Any additional context to help describe this item, such as a token tag, a message ID, a value, a sequence number, etc.
        '''

        self.timestamp = timestamp
        self.function_name = function_name
        self.context_str = context_str
    
    def __repr__(self):
        return str(self.timestamp) + "," + self.function_name + ',' + self.context_str + "\r\n"

class TimeInstrument():

    def __init__(self, name:str):
        '''
        A class to manage time-based instrumentation for a device. The name should reflect the device this was generated on. We should plan to use the log files for post-processing; it could also be used to route messages/log entries to a run-tie process that displays information about timing int he application as it comes in

        Since we're using a multi-process programming model to better utilize multi-core devices, every process needs to be able to provide entries for the log. We could do this with a shared, but that requires locks and expensive opens/writes. We are instead opting for another (low-priority) process that will accept items to log, and write them as needed. When the program is stopped, all of those entries will be written.
        '''
        self.device_name = name
        self.queue = multiprocessing.Queue(maxsize=100)

        self.listener = multiprocessing.Process(target=self.listen)
        self.listener.start()

    def listen(self):
        # os.nice(10)#lower priority; won't work on windows! Only UNIX... 
        self.reduce_writer_priority()
        f = open(self.device_name+'_instrument.log', 'a')
        MAX_TIME_TO_FLUSH = 5
        last_write_time = time.time()
        try: 
            while True:
                try:
                    item = self.queue.get(block=True, timeout=1)
                    self.log(f, item)
                except queue.Empty:
                    continue

                # except: 
                #     raise
                if time.time() - last_write_time > MAX_TIME_TO_FLUSH:
                    # print('close and reopen file')
                    f.close()
                    f = open(self.device_name+'_instrument.log', 'a')
                    last_write_time = time.time()
        finally:
            f.write('================================\r\n')
            f.close()

    def reduce_writer_priority(self):
        import sys
        try: 
            sys.getwindowsversion()
            # import win 
        except AttributeError:
            os.nice(10)


    def log(self, fd, item):
        fd.write(str(item))