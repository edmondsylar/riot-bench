# Copyright 2021 Carnegie Mellon University
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


import sys, os, copy, logging, time
import inspect 
import multiprocessing, queue, threading

from enum import Enum
from intervaltree import Interval, IntervalTree

import Tag
import Token
from Instrumentation import TimeLogItem
import DebugLogger

logger = DebugLogger.get_logger(__name__)

def delay_function(token, queue):
    # logger.debug('delay process to sleep for %f seconds before releasing token %s' % (duration, token))
    duration = token.tag.stop - time.time()
    if duration > 0:
        time.sleep(duration) 
    else:
        logger.warning('Deadline for %f ended in the past (current time: %f)' %(token.tag.stop, time.time()))
    queue.put(token)

class InputSynchronizedFunction():

    def __init__(self, wrapped_function, receiver_queue, instrument_queue=None, min_overlap=0, use_deadline=False, queue_max_size=10, typical_interval_width=.125, debug_logging=False):
        self.function_name = wrapped_function.__name__
        self.logger = DebugLogger.get_logger('WaitingMatching.'+self.function_name)
        self.debug_logging = debug_logging

        # self.function = wrapped_function
        self.function_receiver_queue = receiver_queue
        self.instrument_queue = instrument_queue

        self.min_overlap = min_overlap
        self.typical_interval_width = typical_interval_width
        
        # sig = inspect.signature(wrapped_function)
        # print(sig.parameters)
        args, varargs, varkw, defaults = inspect.getargspec(wrapped_function)
        if args[0] == 'self':
            args = args[1:]
        if defaults: 
            args = args[:-len(defaults)]
        # self.parameter_names = [param for param in sig.parameters]
        self.parameter_names = args
        self.n_ports = len(self.parameter_names) # assume all are required functions

        self.use_deadline = use_deadline
        if self.use_deadline:
            self.parameter_names.append('DEADLINE')

        self.waiting_matching = WaitingMatching(self.n_ports, self.parameter_names, use_deadline=self.use_deadline, debug_logging=self.debug_logging)

        self.last_successful_interval = Interval(-sys.maxsize, -sys.maxsize+1)

        self.input_queue = multiprocessing.Queue(maxsize=queue_max_size)
        self.proc = multiprocessing.Process(target=self.listener)
        self.proc.start()

    def receiveToken(self, token):
        '''
        Assuming token has two portions; a time-interval ( a tuple of start, stop values in seconds from time.time()), and a value. Only the interval is used within the waiting-matching. This should be called from another process
        '''        
        self.input_queue.put(token, block=True)
        return

    def checkToken(self, token):
        '''
        Assuming token has two portions; a time-interval ( a tuple of start, stop values in seconds from time.time()), and a value. Only the interval is used within the waiting-matching. This should be called from another process
        '''


        #Check that the token is valid before enqueueing
        if not (isinstance(token, Token.Token) and isinstance(token.tag, Tag.Tag) and token.tag.func_name == self.function_name):
            if self.debug_logging:
                self.logger.error(token)
                self.logger.error(token.tag)
                self.logger.error(token.value)
            raise TypeError("Token should be of form \"token = {'tag':Tag, 'value': Any}\", and the Tag should indicate use for this function")

        if token.tag.port_num:
            if token.tag.port_num > self.n_ports:
                raise TypeError('port number is too large', token)
            elif token.tag.port_num == self.n_ports:
                raise NotImplementedError('Port num == n_ports should only be the case for a deadline token, which is not implemented yet', token)

        elif token.tag.port_name:
            if not token.tag.port_name in self.parameter_names:
                raise TypeError(f'port name {token.tag.port_name} is not valid as a function arg', token)

            elif token.tag.port_name == 'DEADLINE':
                #value should be irrelevant 
                if self.debug_logging:
                    self.logger.debug('deadline token received: %s' % token.tag)

                current_time = time.time()
                if current_time < token.tag.stop:
                    #create new process that will release the deadline shortly
                    delay_duration = token.tag.stop - current_time 
                    if self.debug_logging:
                        self.logger.debug('Deadline is for the future; delay until %f; duration=%f' % (token.tag.stop, delay_duration))

                    # delay_proc = multiprocessing.Process(target=delay_function, args=[token, self.input_queue])
                    # delay_proc.start()

                    delay_thread = threading.Thread(target=delay_function, args=[token, self.input_queue])
                    delay_thread.start()
                    return False
                    
        else:
            raise TypeError('Token tag port info does not match')

        # self.input_queue.put(token, block=True)
        return True


    def listener(self):
        '''
        run as process: 
            proc = multiprocessing.Process(target=self.run)
            proc.start()
        '''
        if self.debug_logging:
            self.logger.info('Waiting-Matching listener starting for %s' % self.function_name)
        if self.instrument_queue:
            self.instrument_queue.put(TimeLogItem(time.time(), 'WM.listener.'+self.function_name, 'Start listening'))
        try:
            while True:
                try:
                    token = self.input_queue.get(block=True, timeout=1)
                    if self.checkToken(token): #False it is was invalid or a deadline token
                        self.processToken(token)
                except queue.Empty:
                    continue
                except:
                    raise

        except BaseException as e:
            self.logger.error(e.with_traceback)
            raise e
        

    def processToken(self, token):
        '''
        Assumed form of token is token = {'start':float, 'stop': float, 'value': Any}, and should *either* have an argument name or port number (index of postional argument)
        '''
        if self.debug_logging:
            self.logger.info('New token to process with tag: ' + str(token.tag))
            self.logger.debug(str(token))
        if self.instrument_queue:
            self.instrument_queue.put(TimeLogItem(time.time(), 'WM.processToken_START.'+self.function_name,  'tag:'+str(token.tag)+', token_id:'+str(token.id)))

        #correct port name for the port number
        if token.tag.port_name and token.tag.port_num == None:
            token.tag.port_num = self.waiting_matching.findPortIndex(token.tag.port_name)
            if token.tag.port_num == -1:
                raise Exception('port name not found for token with tag' + token.tag)

        readied_tokens = None
        overlap = None
        if token.tag.port_name == 'DEADLINE' or 'DEADLINE' in token.tag.port_name:
            if self.debug_logging:
                self.logger.info('Processing deadline token: %s' % token)
                self.logger.info(f"Current time is {time.time()}")
            deadline_interval = Interval(token.tag.start, token.tag.stop, None)
            #TODO; check against self.last_successful_interval to see if deadline already satisfied
            if deadline_interval.begin < self.last_successful_interval.end:
                #deadline was already satisfied
                if self.debug_logging:
                    self.logger.debug('Deadline is for execution that should have already happened, based on the most recent execution; ignoring deadline:  %s' %  str(deadline_interval))
                return 
            elif deadline_interval.begin < self.last_successful_interval.end + self.typical_interval_width/2:
                if self.debug_logging:
                    self.logger.warning("We may need to ignore this deadline: %f" % deadline_interval.begin)

            overlap, readied_tokens = self.waiting_matching.GatherTokensOnTimeout(deadline_interval, self.waiting_matching.ports[:self.n_ports])
            if self.debug_logging:
                self.logger.debug('Timed-out! Process: \n\t\tOverlap %s \n\t\ttoken-set %s' % (str(overlap), str(readied_tokens)))
            # self.logger.debug('Timed-out! Process: \n\t\tOverlap' % (str(overlap)))

        else:
            overlap, readied_tokens = self.waiting_matching.matchTokenOnPort(token, token.tag.port_num, self.waiting_matching.ports[:self.n_ports])

            
            if not overlap or (isinstance(overlap, Interval) and (overlap.end-overlap.begin) < self.min_overlap):
                if self.debug_logging:
                    self.logger.debug('No set of ready-tokens found; adding this one to the ports')
                self.waiting_matching.addTokenOnPort(token, token.tag.port_num)
                return
            else: 
                self.logger.debug('Matching tokens resolved to:\n\t\tOverlap: %s, \n\t\ttoken-set %s' % (str(overlap), str(readied_tokens)))
            
        #if we reach this point, we are ready to use the tokens. They should be removed from the ports and pass the values as arguments

        #remove tokens from WM
        if self.debug_logging:
            self.logger.debug('Found tokens to execute on; evict from WM, and do garbage collection')
        for i, t in enumerate(readied_tokens):
            # self.logger.debug(self.waiting_matching.ports[i].storage)
            if t == token or t == None:
                pass
            else:
                self.waiting_matching.removeTokenFromPort(t, i)

            if self.debug_logging:
                logger.debug("Remaining tokens in port: %d" % len(self.waiting_matching.ports[i].storage.all_intervals))

            #FIXME: is this intended? remove all tokens BEFORE this token from the port as well, under the assumption this in an entirely streaming context, and that if something earlier hasn't finished yet, it never will. This is garbage collection. This could be made less severe by reducing the upper bound by some factor, like stop-start * n for some small n
            if t == None:
                too_old_time = token.tag.start - 3*(token.tag.stop - token.tag.start)
            else:
                too_old_time = t.tag.start - 3*(t.tag.stop - t.tag.start)

            old_tokens = self.waiting_matching.ports[i].storage[:too_old_time]
            for ot in old_tokens:
                self.waiting_matching.removeTokenFromPort(ot.data, i)

        args = list(map(lambda token: None if token == None else token.value, readied_tokens))
        ids = list(map(lambda token: None if token == None else token.id, readied_tokens))

        if len(args) > self.n_ports:
            if self.debug_logging:
                self.logger.warning('Too many arguments!')
            args = args[:self.n_ports] #Don't include the deadlne token, if present
        kwargs = {'time_overlap':overlap}

        self.function_receiver_queue.put((args, kwargs, ids))
        
        if self.instrument_queue:
            self.instrument_queue.put(TimeLogItem(time.time(), 'WM.processToken_CALL.'+self.function_name, 'ids:' + str(ids)))

        #maintain the most recent correct execution interval to help ignore old deadlines
        if self.last_successful_interval and self.last_successful_interval.begin > overlap.begin and self.last_successful_interval.end > overlap.end:
            if self.debug_logging:
                self.logger.warning('Somehow our intervals/executions are out of order; not updating the most-recent tag') 
        else: 
            self.last_successful_interval = overlap


def intervalIntersection(i1, i2):
    data = i1.data
    if i1.begin < i2.begin:
        lower = i1
        higher = i2 
    else:
        lower = i2
        higher = i1
    if lower.end < higher.begin:
        # No overlap
        return None
    return Interval(higher.begin, min(lower.end, higher.end), data)

def intervalUnion(i1, i2):
    data = i1.data
    if i1.begin < i2.begin:
        lower = i1
        higher = i2 
    else:
        lower = i2
        higher = i1
    return Interval(lower.begin, max(lower.end, higher.end), data)

class PortType(Enum):
    '''
    The port type is necessary for streaming graphs and certain types of firing rules. 
    
    Vanilla ports are normal; a token comes in, synchronizes with others, and gets consumed in execution. It will be removed.
    Sticky ports will force the token to stick around for more than one iteration so that it can be reused. These are necessary for periodic sources (TimedRetrigger firing rule) and when a streaming SQ receives input from streaming and non-streaming sources.
    Control ports are extra special, in that they receive from arcs that are not within the compiled graph; they exist to *control* the mechanisms to force sequentiality or release a token/execution context on a timed schedule, e.g. stateful SQ or a deadline, resp.
    '''

    Vanilla = 0
    Sticky = 1
    Control = 2 #used for retriggering; not described by graph itself

class InputPort():
    '''
    A InputPort holds tokens for a port, and is enumerated with a port type to better distinguish how to handle values as they are inserted/removed from the port.
    '''
    def __init__(self, port_type, variable_name=None):
        self.port_type = port_type
        self.storage = IntervalTree() #TODO: separate by application context. or even a level up at SQInputTokenStorage within SQSync
        self.name = variable_name
   
    def __repr__(self):
        return f'<InputPort{self.port_type} -- {hex(id(self))}'

class WaitingMatching():
    # For each input port to this SQ, allocate an IntervalTree
    def __init__(self, n_ports, variable_names, use_deadline=False, debug_logging=False):
        self.ports = []
        self.variable_names = variable_names
        self.debug_logging = debug_logging
        assert len(variable_names) == n_ports or (len(variable_names) == n_ports+1 and variable_names[-1]=='DEADLINE'), (variable_names, n_ports)

        for i in range(n_ports):
            self.ports.append(InputPort(PortType.Vanilla, variable_name=self.variable_names[i]))

        #Add control port for deadlines/timeout
        if use_deadline:
            self.ports.append(InputPort(PortType.Control, variable_name='DEADLINE'))

        # logger.debug(self.ports)        

    def findPortIndex(self, port_name):
        for i, p in enumerate(self.ports):
            if port_name == p.name and port_name != None:
                return i

        return -1

    # Insert the token into the appropriate (based on port number) IntervalTree
    # using ticks of the root clock as the basis for representing the interval
    # associated with this token
    def addTokenOnPort(self, token, port_number):
        self.ports[port_number].storage[token.tag.start:token.tag.stop] = token
        # logger.info(self.ports[port_number].storage.all_intervals)

    def removeTokenFromPort(self, token, port_number):
        interval = Interval(token.tag.start, token.tag.stop, data=token) 
        self.ports[port_number].storage.remove(interval)


    def matchTokenOnPort(self, token, port_number, ports):
        '''
        Try to find a set of candidate tokens that all align in time with the input token
        '''
        # Find a match to this token's start time
        other_ports = ports[:port_number] + ports[port_number+1:]
        trees_to_match = list(map(lambda x: x.storage, other_ports))
        interval_set = {Interval(token.tag.start, token.tag.stop)}
        for tree in trees_to_match:

            new_interval_set = set()
            for interval in interval_set:

                # Retrieve the intervals in the tree that match intervals in the set
                overlap_set = tree[interval.begin:interval.end]
                # Intersect the interval with each of the results in the set
                new_interval_set = new_interval_set.union(set(map(lambda x: intervalIntersection(x, interval), overlap_set)))
                
            interval_set = new_interval_set
        
        #take the first one, but there may be multiple
        if len(interval_set) > 0:
            #may need to do something more intelligent here; get the largest and earliest interval
            matching_interval = list(interval_set)[0]
            if len(interval_set) > 1:
                if self.debug_logging:
                    logger.warning("More intervals are possible: %s" % str(list(interval_set[1:])))
                interval_list = list(interval_set)
                max_size = 0
                max_ind = 0
                for i, interv in enumerate(interval_list):
                    size = interv.end - interv.begin
                    if size > max_size: 
                        max_size = size
                        max_ind = i

                matching_interval = interval_list[max_ind]


            # Return a tuple: first element is the overlap interval, second is the list of tokens including the input token)
            # overlap_time = Time(token.time.clock, matching_interval.begin, matching_interval.end)
            overlap_time = matching_interval
            matched_token_list = list(map(lambda x: list(x[matching_interval.begin:matching_interval.end])[0].data, trees_to_match))
            # all_token_list = matched_token_list[:port_number] + [token] + matched_token_list[port_number+1:] # no need to only use beyond port_number+1; port_number: is fine because we used fewer trees for matching
            all_token_list = matched_token_list[:port_number] + [token] + matched_token_list[port_number:]
            return overlap_time, all_token_list
        else:
            return None, None


    def GatherTokensOnTimeout(self, deadline_interval, ports):
        deadline_start = deadline_interval.begin
        deadline_stop = deadline_interval.end

        readied_tokens = [None for i in range(len(ports))]

        for i, port in enumerate(ports):

            #we're removing ANYTHING that's older than the deadline's start
            waiting_token_intervals = port.storage[-sys.maxsize:deadline_start]
            #but we'll keep the token 
            token_intervals_since_deadine_start = port.storage[deadline_start:deadline_stop]
            for interval in waiting_token_intervals:
                token = interval.data
                if interval in token_intervals_since_deadine_start:
                    #a bit dangerous for this to be the only criterion; 
                    if readied_tokens[i] != None:
                        #Shouldn't have this case if we have nonintersecting intervals stamped on tokens
                        if readied_tokens[i].tag.start < interval.begin:
                            #elect to take the earliest one, so skip if condition is met
                            continue
                    readied_tokens[i] = token

                else:
                    #remove only those that haven't been created within or since the deadline started
                    self.removeTokenFromPort(token, i)


        overlap = Interval(deadline_start, deadline_start, 'deadline_overlap')
        for t in readied_tokens:
            if t == None:
                continue

            overlap = intervalUnion(overlap, Interval(t.tag.start, t.tag.stop))
            
        return overlap, readied_tokens
