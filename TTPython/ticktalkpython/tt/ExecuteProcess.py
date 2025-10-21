# Copyright 2021 Carnegie Mellon University
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

'''

The ``TTExecuteProcess`` is one of the primary processes that handles runtime mechanisms on a ``TTEnsemble``; specifically, this handles the execution portion of a ``TTSQ``. It implements the ``TTSQExecute`` portion, which runs the code within the SQ. When an SQ has executed, this process sends the output token to the ``TTNetworkManagerProcess``, where it will be forwarded to downstream SQs. For some types of SQs/Firing Rules, this SQ will also send a control token back to the ``TTInputTokenProcess``

All TT*Process classes follows the same design pattern. They implement a singular input queue from which they read new ``IPCMessages``, which self-identify their function.  After processes are created, they exchange interfacing information, primarily in the form of callback functions. After configuring interfaces, the processes start. Each of these processes spends its idle time waiting for new inputs within a 'run loop', responding to messages as they arrive; the responses will modify internal process state and produce new messages for other processes implemented on the Ensemble, which 'owns' the processes.

'''

import sys, pickle, traceback, math
import simpy

import SQ, SQExecute
import queue
import math
import Tag
import Time
import Token
from IPC import *
import Clock

import DebugLogger

from Empty import TTEmpty
import multiprocess as mp

class TTExecutionContext:
    '''
    A ``TTExecutionContext`` contains all necessary information to invoke and execute an SQ (``TTSQExecute``) at runtime. This is entirely free of direct memory references, instead relying on consistent naming to identify the SQ to run the provided set of inputs on.

    :param sq_name: The name of the SQ
    :type sq_name: string
    :param inputs: A list of ``TTTokens`` that the SQ will operate on.
    :type inputs: list(TTToken)
    :param input_time_overlap: The time overlap of the input tokens as determined during synchronization (within ``TTInputTokenProcess`` and ``TTSQSync``)
    :type input_time_overlap: TTTime
    :param estimate_runtime: An estimate of how long it will take to execute an SQ, default as 0
    :type estimate_runtime: int
    '''
    def __init__(self, sq_name, inputs, input_time_overlap, estimate_runtime=0):
        self.sq_name = sq_name
        self.inputs = inputs
        self.input_time_overlap = input_time_overlap
        self.estimate_runtime = estimate_runtime

    def dereference_token_times(self):
        '''
        Convert the ``TTTime```objects within the tag to ``TTTimeSpecs``, which are free of memory references that make inter-process and inter-device exchange of tokens less efficient (we wish to avoid serializing the entire clock tree for every single passed token).
        '''
        for t in self.inputs:
            if isinstance(t, Token.TTToken):
                if isinstance(t.time, Time.TTTime):
                    t.time = Time.TTTimeSpec.fromTime(t.time)
            else: raise ValueError('input to TTExecutionContext is not a token!')

    def rereference_token_times(self, clocks):
        '''
        Convert the ``TTTimeSpec`` objects within the tokens to ``TTTime``; the ``TTExecuteProcess` will expect ``TTTimes``. To do this conversion, we
        provide a set of clocks to revert the ``TTClockSpec`` within the ``TTTimeSpec`` to an actual ``TTClock``

        The main purpose of this is to prevent clocks from being copied. This is problematic w.r.t. consistency, the relation between the root-clock and hardware time. It may also increase the size of messages send, thus requiring more bytes be serialized & deserialized
        '''
        for t in self.inputs:
            if isinstance(t, Token.TTToken):
                t.time = Time.TTTimeSpec.toTime(t.time, clock_list=clocks)
            else: raise ValueError('input to TTExecutionContext is not a token!')

    def __repr__(self):
        return f'<TTExecutionContext {hex(id(self))} - {self.sq_name} execute on {self.inputs}'


class TTSQJob():
    def __init__(self, sq_execute, execute_context, execute_time):
        self.job_id = id(self)
        self.sq_execute = sq_execute
        self.execute_context = execute_context
        self.execute_time = execute_time

    def get_id(self):
        return self.job_id

    def start_job():
        pass


class TTSQClosure():
    def __init__(self, id, state, f):
        self.id = id
        self.f = f
        self.state = state


class TTSQOutput():
    def __init__(self, id, state, output):
        self.id = id
        self.state = state
        self.output = output


class TTExecuteProcess:
    '''
    A process to handle the execution of SQ's specifically the ``TTSQExecute`` portion. This process is owned and managed by the ``TTEnsemble``.

    The process maintains a dictionary of these and the relevant clocks; these are populated as SQs are instantiated at runtime.
    It is fed data via an input queue from other processes (``TTNetworkManagerProcess`` for instantiating clocks & SQs and
    ``TTInputTokenProcess`` for sets of inputs to execute an SQ on).

    This process also maintains a singular root clock that it uses to read 'real' time.

    :param input_queue: The input queue that this process will receive inputs on
    :type input_queue: ``queue.Queue`` | ``multiprocess.Queue``


    '''
    def __init__(self, input_queue, ensemble_name=None):
        self.input_queue = input_queue
        self.sqs = {} #dictionary of sqs; the sq name is the key, and the value is a TTSQExecute object
        self.clocks = []
        self.root_clock = None #perhaps we should generalize this? The root_clock has a 'now' function to read the current time. We may want to instead just have a clock associated with each SQ (that needs one).

        self.ensemble_name = ensemble_name
        self.logger = DebugLogger.get_logger('ExecutionProcess-'+ensemble_name)

        self.sim = None # currently, local clock is read from simpy.now
        self.sim_process= None

        self.sq_jobs = {}
        self.sq_output_queue = mp.Queue()


    def add_sq(self, sq_name, specification):
        # currently not in use; consider deprecated. We send TTSQExecute objects in picklized form instead of the JSON spec (it is simply easier and probably lower overhead)
        self.sqs[sq_name] = SQExecute.TTSQExecute.from_json(specification)

    def remove_sq(self, sq_name):
        '''
        Evict an SQ from the process; use the SQ's name to identify it

        :param sq_name: The name of an SQ
        :type sq_name: string
        '''
        if sq_name in self.sqs:
            del self.sqs[sq_name]

    def get_sq(self, sq_name):
        '''
        Retreive an SQ based on its name

        :param sq_name: The name of an SQ
        :type sq_name: string
        :return: The SQ of interest; return None if not present
        :rtype: TTSQExecute | None
        '''
        return self.sqs.get(sq_name, None)

    def setup_process_interface(self, input_token_func, input_network_func, sim_process=None):
        '''
        Configure the interface to this process, meaning the callback functions for sending outputs to the ``TTInputTokenProcess`` or ``TTNetworkManagerProcess``

        :param input_token_func: A callback function for providing ``IPCMessage`` inputs to the ``TTInputTokenProcess``
        :type input_token_func: function
        :param input_network_func: A callback function for providing ``IPCMessage`` inputs to the ``TTNetworkManagerProcess``
        :type input_network_func: function
        :param sim_process: A reference to the simulated process that this class runs inside of. Mainly used for interrupting the simulated variant on input messages. Defaults to None
        :type sim_process: ``simpy.Process`` | None
        '''
        self.input_token_func = input_token_func # used only for feedback control tokens
        self.input_network_func = input_network_func

        self.sim_process = sim_process # used to interrupt processes so that awaiting inputs on queues can wait indefinitely without advancing sim time

    def input_msg_to_process(self, message):
        '''
        Input an ``IPCMessage`` to this process. If running in a simulation environment, this will interrupt

        :param message: A message to provide to this process. Does not need to be called within the same process (i.e. it is not only thread-safe but inter-process safe)
        :type message: IPCMessage
        '''
        self.input_queue.put(message)
        if self.sim and self.sim_process and self.sim.active_process != self.sim_process:
            self.logger.log(2, 'Interrupting!: t=%f' % self.sim.now)
            self.sim_process.interrupt()

    def get_next_input(self):
        '''
        Pull the next input off the input queue.
        '''
        if self.sim:
            return self.input_queue.get_nowait() # If this is a simulation, don't bother waiting here; let the ``run_sim`` function handle that`
        else:
            return self.input_queue.get(block=False)


    def run_sim(self, sim):
        '''
        The main run loop for a runtime environment using simulated processes, which runs on a single core and can implement many ensembles.
        This will listen to the input queue and call a handler for any messages that arrive

        This must be instantiated using the sim.process() interface, as this function is technically a generator due to its usage of 'yield' (an essential component of simpy event processing)

        This will listen to the input queue and call a hanlder for any messages that arrive.
        '''
        # TODO: sim is broken with the new SQ execution
        # multiprocess model. The simpy env does not wait
        # for the SQ execute processes.
        # FIX: Change from multiprocess into a simpy.process?
        self.logger.warning(
            "simulation is incompatible with new SQ execution model")

        self.sim = sim

        self.logger.info('run sim loop Execute')
        next_msg = None
        try:
            while True:
                try:
                    next_msg = self.get_next_input()

                except queue.Empty:
                    try:
                        yield self.sim.timeout(math.inf) #we wait infinitely because an arriving input should simpy interrupt the process
                    except simpy.Interrupt:
                        continue
                except simpy.Interrupt:
                    # this should not actually occur since simpy is a single-threaded event loop and get_next_input does nto wait
                    continue

                if next_msg:
                    try:
                        self.handle_message(next_msg)
                    except BaseException as e:
                        print('caught an error; could nuke process, but won\'t')
                        traceback.print_exc()

                try:
                    job_output = self.check_jobs()
                except queue.Empty:
                    job_output = None

                if job_output:
                    sq_job = self.get_job(job_output.id)
                    state = job_output.state
                    self.handle_sq_output(sq_job, state, job_output.output)

        except KeyboardInterrupt:
            raise
        except BaseException as e:
            raise

    def run_phy(self):
        '''
        The main run loop for a runtime environment using physical processes, which can take advantage of multi-core processors.

        It is expected that this will run in its own distinct ``multiprocess.Process`` (at the level of the OS with its own virtual memory).

        This will listen to the input queue and call a handler for any messages that arrive.

        '''
        self.logger.info('run phy loop Execute')
        try:
            while True:
                # TODO: check the specific queue rather than checking all queues
                mp.connection.wait(
                    [self.input_queue._reader, self.sq_output_queue._reader])
                try:
                    next_msg = self.get_next_input()
                except queue.Empty:
                    next_msg = None

                if next_msg:
                    self.handle_message(next_msg)

                try:
                    job_output = self.check_jobs()
                except queue.Empty:
                    job_output = None

                if job_output:
                    sq_job = self.get_job(job_output.id)
                    state = job_output.state
                    self.handle_sq_output(sq_job, state, job_output.output)

        except KeyboardInterrupt:
            return
        except BaseException as e:
            raise

    def handle_message(self, msg):
        '''
        This will handle IPC (Inter Process Communication) messages arriving
        to this process via the singular input queue. This will include
        messages at the data, control, and management planes, which will have
        designators to specify how they should be handled
        (using process-specific enumeration)

        The execution process will handle messages to instantiate/remove SQs
        (only the execution portion) and to run an SQ's execution section on
        a ``TTExecutionContext`` received from the synchronization
        (input token) process. When this completes, it will stamp tokens with
        a new tag and send to the network manager process, which will
        communicate them to downstream SQs on whichever ensembles they are mapped

        :param msg: A message read off of the input queue. This must be an
            ``IPCMessage`` with a msg_type of ``IPCMessageTypeExecute`` and
            process_recipient of ``ProcessExecute``, else it will be ignored
            without notification

        :type msg: IPCMessage

        :return: None; any 'return-like' behavior will produce an IPC message
            for another process
        '''
        if not isinstance(msg, IPCMessage): return
        if not isinstance(msg.msg_type, IPCMessageTypeExecute): return
        if not msg.process_recipient == IPCMessageProcessRecipient.ProcessExecute: return

        msg_type = msg.msg_type
        self.logger.info('New message of type %s', msg_type)
        self.logger.debug('New message %s', msg)

        if msg_type == IPCMessageTypeExecute.NewExecutionContext:
            execution_context = msg.payload
            assert isinstance(execution_context, TTExecutionContext), 'Not an execution context'
            execution_context.rereference_token_times(self.clocks)
            self.spawn_sq_job(execution_context) #execute on the named SQ within the execution_context on the inputs provided

        elif msg_type == IPCMessageTypeExecute.StatefulExecutionContext:

            execution_context = msg.payload
            self.spawn_sq_job(execution_context) #FIXME: anything extra to do for stateful? This may be an overspecification

        elif msg_type == IPCMessageTypeExecute.InstantiateSQ:
            if not isinstance(msg.payload, SQExecute.TTSQExecute):
                sq_execute = SQExecute.TTSQExecute.from_json(msg.payload) #not acutally in use..
            else:
                sq_execute = msg.payload

            assert isinstance(sq_execute, SQExecute.TTSQExecute), 'IPC message for SQ instantiation at the ExecutionProcess must be of type SQExecute.TTSQExecute; was %s' % type(sq_execute)

            # The sq needs to be provided some instantiation information at runtime, including clocks
            ## this is also when we prepare the SQ for invocation by setting up a namespace and analyzing keyword argments
            self.logger.info('Instantiate SQ %s' % sq_execute.sq_name)

            sq_execute.instantiate_at_runtime(self.clocks)
            self.sqs[sq_execute.sq_name] = sq_execute


        elif msg_type == IPCMessageTypeExecute.UpdateCode:
            pass
            raise NotImplementedError

        elif msg_type == IPCMessageTypeExecute.RemoveSQ:
            pass
            raise NotImplementedError

            # del self.sqs[msg.payload]

        elif msg_type == IPCMessageTypeExecute.AddClocks:
            # add a set of clocks to be held by this process; ideally, this is identical to what the InputTokenProcess has
            new_clocks = msg.payload
            for c in new_clocks:
                if c.is_root():
                    if self.root_clock != None: self.logger.warning("Root clock is getting overwritten!")

                    self.root_clock = c
                    if self.sim != None:
                        now_func = lambda : self.sim.now
                        Clock.TTClock.__set_root_now__(now_func=lambda: self.sim.now*1000000, ticks_per_second=1000000, root=c) #the explicit 1,000,000 are not ideal, but they are otherwise present in defaults.. Still hacky to handle it in this way. TODO: improve solution. Relevant functions are right here, as well as wait/wait_until in TimedEventProcess.
                    else:
                        #uses default 'now' function , which calls time.time(). May require more customization here in physical case
                        Clock.TTClock.__set_root_now__(root = self.root_clock)

                    self.logger.debug('Added new root clock: %s' % self.root_clock)
                    self.logger.debug("Current time on root clock: %d" % self.root_clock.now())

            self.clocks.extend(new_clocks) #must be a list of TTClocks. Should this check for duplicates and only append new ones?

        elif msg_type == IPCMessageTypeExecute.RemoveClocks:
            # There is not yet a case for this. It may involve traversing the set of SQs and making sure they do not carry a reference to the removed clock
            raise NotImplementedError

        elif msg_type == IPCMessageTypeExecute.UpdateClocks:
            #There is not yet a case for this. We assume TTClocks are effectively immuatable at runtime (even if there are no protections...)
            raise NotImplementedError

    ### An interesting choice would be to spawn a thread for each running SQ, mainly to handle IO lock. The saying goes to use processes when you are processor/memory locked, and threads when IO locked (the latter has much lower overhead and allows concurrently accessible virtual memory). A programmer is free to include delays and polling within their own SQ. Often, this is a poor practice and misses the point of TickTalk and SQs, but some hardware will nonetheless take time to receive data over an interface, such as UART (imagine SDI-12, a half-duplex bus running at the speed of molasses: 1200 baud. That's a long time to stall the execution of *all* SQs). Alternatively, Python swaps threads based on execution time or instruction counts -- maybe a poor decision due to overhead if we have a couple of compute-heavy SQs running in parallel rather than sequentially. This is not entirely unique to Python 3 runtime, but that environment does impose harder restricts than some runtimes might. NB: the simulation environment may not be friendly to delays within SQs due to the interruption mechanics used at each process's interface (when a new value is inserted, the process interrupts, which acts as an exception. If possible, an easy fix would be effecitvely 'turn off interrupts' as is ordinarily done in 'critical' sections). -Reese
    def spawn_sq_job(self, execute_context: TTExecutionContext):
        '''
        Execute a ``TTSQExecute`` on a new execution context. This will
        provide the inputs (in the execute_context) and set of stored
        keyword arguments (within the TTSQExecute) to be executed in a private
        namespace with access this SQ's state
        '''
        #mark when we started
        execute_time = self.root_clock.now()

        #find SQ to execute
        try:
            sq_execute = self.get_sq(execute_context.sq_name)
            assert isinstance(
                sq_execute, SQExecute.TTSQExecute
            ), 'SQ to execute must of type ``SQExecute.TTExecute``'
        except KeyError:
            self.logger.error('Failed to find SQ named %' % execute_context.sq_name)
            return

        self.logger.info('Execute for SQ %s' % sq_execute.sq_name)
        assert isinstance(sq_execute.interpreter, SQ.TTInterpreter), "Unsupported interpreter"
        if sq_execute.interpreter == SQ.TTInterpreter.Python3:

            # The sq should have already been instantiated (or at least 'prepared')
            if not hasattr(sq_execute, 'namespace'):
                #TODO: should the namespace be distinct based on the context tag 'u' within the set of tokens?
                sq_execute.instantiate_at_runtime(self.clocks)

            if len(execute_context.inputs) != sq_execute.num_inputs:
                #raise error instead? Likely that a runtime error will be thrown.
                #If we provided some default or null (None) input, those should still be here in the proper index
                self.logger.warning("Execute SQ %s on %d inputs -- %d exepected" % (sq_execute.sq_name, len(execute_context.inputs), sq_execute.num_inputs))

            sq_job = TTSQJob(sq_execute, execute_context, execute_time)
            sq_closure = TTSQClosure(sq_job.get_id(), sq_execute.state,
                                     sq_execute.function)
            self.add_job(sq_job)

            p = mp.Process(
                target=self.run_job,
                args=[sq_closure, execute_context.inputs, sq_execute.kwargs])
            p.start()

        else:
            raise ValueError('Interpreter not supported')


    def run_job(self, closure:TTSQClosure, args, kwargs):
        # needs the state: sq_execute.state
        sq_output = closure.f(*args, **kwargs)
        self.sq_output_queue.put(
            TTSQOutput(closure.id, closure.state, sq_output))
        return


    def add_job(self, sq_job:TTSQJob):
        self.sq_jobs[sq_job.get_id()] = sq_job


    def get_job(self, sq_id:int) -> TTSQJob:
        return self.sq_jobs[sq_id]


    def remove_job(self, sq_job:TTSQJob):
        del self.sq_jobs[sq_job.get_id()]


    def check_jobs(self) -> TTSQOutput:
        return self.sq_output_queue.get(block=False)


    def handle_sq_output(self, sq_job:TTSQJob, new_state, return_token_list):
        sq_execute = sq_job.sq_execute
        execute_context = sq_job.execute_context
        execute_time = sq_job.execute_time

        self.logger.info('returned %s' % return_token_list)

        # if self.sim and sq_context.estimate_runtime > 0: #if simulation, it would be nice to wait for this period, but that is difficult; simpy uses 'yield' to insert delays, but that would make this function a generator such that it will not complete in the phy version. If we need that functionality, it should be carefully designed. Nonessential for now. TODO.
        #     self.wait_function(sq_context.estimate_runtime)

        completion_time = self.root_clock.now()

        sq_execute.state.update(new_state)

        ipc_token_list = []
        for return_token in return_token_list:
            sent_sequential_token = False
            self.logger.debug('SQ %s produced token: %s' % (sq_execute.sq_name, return_token))

            # The SQ returned a value; let's put together
            if return_token is not None:
                # create the basis for a tag, starting from the application
                # context. The rest will be filled in when forwarding to
                # all arc destinations
                return_token.tag = Tag.TTTag(execute_context.inputs[0].tag.u)

                # If this is a STREAMify or timed self-retriggering node,
                # modify the TTTime based on the data_validity_interval
                # (retrived from a keyword in the TTPython program)
                if sq_execute.pattern == SQ.TTSQPattern.TriggerInNOut and sq_execute.data_validity_interval:
                    # let's estimate that the value we generated was
                    # create approximately halfway between when we started
                    # this function and when it returned.
                    est_sampling_timestamp = (execute_time +
                                                completion_time) // 2

                    #if this is a sampling node and it has a
                    # data-validity-interval, then recalculate the time based
                    # on an approximate sampling time
                    return_token.time = Time.TTTime(
                        self.root_clock, est_sampling_timestamp -
                        math.ceil(sq_execute.data_validity_interval / 2),
                        est_sampling_timestamp +
                        math.ceil(sq_execute.data_validity_interval / 2)
                    ) # if the interval is odd, then this will actually be
                    # a bit shorter; maybe do a ceiling and floor

                #replace with a TTTimeSpec before sending it to the next process
                return_token.time = Time.TTTimeSpec.fromTime(
                    return_token.time)
                send_token_payload = {
                    'token': return_token,
                    'source_sq': sq_execute.sq_name
                }

                #time-sensitive bits (not entirely necessary)
                send_token_payload['execute_time'] = execute_time
                send_token_payload['completion_time'] = completion_time

                # enable conditional sending
                if type(return_token.value) is TTEmpty:
                    token_type = IPCMessageTypeNetwork.EmptyToken
                else:
                    token_type = IPCMessageTypeNetwork.SendToken

                send_token_msg = IPCMessage(
                    token_type, send_token_payload,
                    IPCMessageProcessRecipient.ProcessNetwork)
                # Send the token to the outputs
                # if sq_context.sq.output_arc:
                #     self.ensemble.send_token_on_arc(rt, sq_context.sq.output_arc)

                ipc_token_list.append(send_token_msg)

                # if sequential (accesses state across invocations and operates
                # on streams but isn't generating them), send a token back to
                # the input-token process. This is a control token
                if sq_execute.is_sequential and not sent_sequential_token:
                    sent_sequential_token = True
                    time_overlap = execute_context.input_time_overlap
                    # the next invocation must be on tokens that are strictly
                    # older than than the ones used for this invocation. We
                    # want to process in chronological order
                    # TODO: find a way to make this less susceptible to
                    # TODO: skipping iterations. May require deadlines or
                    # TODO: assumption (could be learned) about how far apart
                    # TODO: stream values are generated (assuming periodic)
                    # TODO: and how long they take to arrive(??). May require
                    # TODO: extra specification in TTPython program with kwargs
                    time = Time.TTTimeSpec(
                        Clock.TTClockSpec.fromClock(time_overlap.clock),
                        time_overlap.start_tick, Time.TTTime.MAX_TIMESTAMP)
                    # create a tag for the feedback token; let's assume the
                    # control port is at a port starting at the number of inputs
                    # for execution
                    tag = Tag.TTTag(context=return_token.tag.u,
                                    sq=sq_execute.sq_name,
                                    port=sq_execute.num_inputs,
                                    ensemble_name=self.ensemble_name)
                    feedback_sequence_token = Token.TTToken(None,
                                                            time,
                                                            tag=tag)
                    self.logger.info(
                        'Sending sequential retriggering token back to input token process:  %s'
                        % feedback_sequence_token)

                    feedback_token_msg = IPCMessage(
                        IPCMessageTypeSync.InputToken,
                        feedback_sequence_token,
                        IPCMessageProcessRecipient.ProcessInputTokens)
                    self.input_token_func(feedback_token_msg)

        self.input_network_func(IPCSendTokenList(ipc_token_list))

        self.remove_job(sq_job)
