# Copyright 2021 Carnegie Mellon University
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

'''
A runtime manager is a higher level entity in the TickTalk system that serves to coordinate the setup and teardown of the TickTalk system and runtime, including notifying ``TTEnsembles`` of each other, generating a mapping (with ``TTMapper``) of the graph, distributing the SQs to ensembles, injecting initial tokens into the system to kickstart graph interpretation and logging final output tokens for future analysis. In other words, the runtime manager handles the management plane of the system.

The ``TTRuntimeManager`` is effectively another ``TTEnsemble``, but differs in that it implements an extra process, ``TTRuntimeManagerProcess``. In essence, the TTRuntimeManager is really a wrapper for this process, and is best suited as the user-facing device so the user can see other ensembles in the system connect and personally trigger a graph to be instantiated and interpretation started once the system is setup per their needs.

'''


import sys, math, time
from abc import ABC, abstractmethod
import queue
import simpy
from copy import deepcopy

from Graph import TTGraph

import Ensemble
import DebugLogger
import Mapper
from IPC import *
import SQ
import Token, Time, Clock, Tag

'''
default name for the runtime manager ensemble. Other ensembles generally assume there is one runtime manager, and it goes by this name. This is how they build the first entry to their routing table and send a message to 'Join' the network of ensembles
'''
RUNTIME_MANAGER_ENSEMBLE_NAME = 'runtime-manager'

class TTRuntimeManager(ABC):
    '''
    An entity to manage the environment at runtime. The program starts from here, getting mapped to ensembles either dynamically or according to extant information within the SQs in the graph. This is technically an ensemble in that it has a network interface. Simulated and physical variants exist for this as child classes, similar to the network interfaces.
    '''
    def __init__(self, name=RUNTIME_MANAGER_ENSEMBLE_NAME):
        self.manager_ensemble = Ensemble.TTEnsemble(name, is_runtime_manager=True) # the ensemble will go through ordinary setup procedures, which are somewhat specific to the runtime environment (physical vs. simulation)
        # self.connected_ensembles = [] # this is effectively a copy of the routing table, but may also contain additional metadata about ensemble capabilities

    def pass_message_to_runtime_process(self, msg):
        '''
        Only the runtime manager process will actually interact with the rest of the system; this simply serves as a proxy from the user-level environment (the main process on the machine hsoting the runtime manager)

        :param msg: The message to pass to the actual runtime manager process
        :type msg: IPCMessage
        '''
        self.manager_ensemble.runtime_manager_process.input_msg_to_process(msg)

    def instantiate_and_map_graph(self, graph:TTGraph):
        '''
        Signal the runtime manager process to instanatiate the graph for execution by generating a mapping to of SQs to ensembles and distributing those SQs accordingly

        :param graph: The graph representing a TTPython program to execute
        :type graph: TTGraph
        '''
        #TODO; allow a statically-produced mapping to be provided here as well. In that case, the graph and mapping should be set as the payload in a tuple (graph, mapping).
        graph_msg = IPCMessage(IPCMessageTypeRuntime.InstantiateAndMapGraph, graph, IPCMessageProcessRecipient.ProcessRuntimeManager)
        self.pass_message_to_runtime_process(graph_msg)



class TTRuntimeManagerSim(TTRuntimeManager):
    '''
    A simulated runtime manager. Can directly access any reference to another ensemble, clock, SQ, etc.; uses a simulated network interface. This is is mainly used to configure the ensemble acting as the Runtime Manager

    :param ensembles: A list of the ensembles that compose the system. This may be empty, in the case where the other ensembles are created *after* the runtime manager starts (such that they join the TickTalk system as any physical ensemble would).
    :type ensembles: [TTEnsemble]
    '''
    def __init__(self, ensembles, sim, name=RUNTIME_MANAGER_ENSEMBLE_NAME):
        super().__init__(name=name)
        self.ensembles = ensembles
        self.sim = sim

        self.manager_ensemble.setup_queues(is_sim=True)
        self.manager_ensemble.setup_simulation_processes(sim=self.sim)
        #self.manager_ensemble.enter_steady_state() #this will block the rest of execution until an uncaught exception or KB interrupt occurs

        ens_description = {'name':RUNTIME_MANAGER_ENSEMBLE_NAME, 'address':self.manager_ensemble}

        add_self_to_routing_msg = IPCMessage(IPCMessageTypeRuntime.JoinTickTalkSystem, ens_description, IPCMessageProcessRecipient.ProcessRuntimeManager)
        self.pass_message_to_runtime_process(add_self_to_routing_msg)




class TTRuntimeManagerPhysical(TTRuntimeManager):
    '''
    A runtime manager on a physical device; one ensemble will take on this coordination role.

    :param ip: The IPv4 address of the runtime manager. Must be accessible by all other ensembles that wish to join the system.
    :type ip: string
    :param rx_port: The port the runtime manager ensemble expects to receive input messages from
    :type rx_port: int
    :param tx_port: The port the runtime manager plans to use for sending outputs to other ensembles in the system
    :type tx_port: int
    '''
    def __init__(self, ip, rx_port, tx_port, name=RUNTIME_MANAGER_ENSEMBLE_NAME):
        super().__init__(name=name)

        self.manager_ensemble.setup_queues(is_sim=False)
        self.manager_ensemble.setup_physical_processes(network_ip=ip, rx_network_port=rx_port, tx_network_port=tx_port)
        #self.manager_ensemble.enter_steady_state() #this will block the rest of execution until an uncaught exception or KB interrupt occurs

        ens_description = {'name':RUNTIME_MANAGER_ENSEMBLE_NAME, 'address':f'{ip}:{rx_port}'}

        # add self to the routing table
        add_self_to_routing_msg = IPCMessage(IPCMessageTypeRuntime.JoinTickTalkSystem, ens_description, IPCMessageProcessRecipient.ProcessRuntimeManager)
        self.pass_message_to_runtime_process(add_self_to_routing_msg)


class TTRuntimeManagerProcess():
    '''
    A priveleged process included only on the runtime manager ensemble that can receive from and send into the ``TTNetworkManagerProcess`` local to itself. It is responsible for forwarding routing-table additions to all connected ensembles, mapping SQs from the graph (and sending the corresponding messages), sending initial input tokens to trigger graph execution, and logging output tokens.

    All TT*Process classes follows the same design patterns. They implement a singular input queue from which they read new ``IPCMessages``, which self-identify their function.  After processes are created, they exchange interfacing information, primarily in the form of callback functions. After configuring interfaces, the processes start. Each of these processes spends its idle time waiting for new inputs within a 'run loop', responding to messages as they arrive; the responses will modify internal process state and produce new messages for other processes implemented on the Ensemble, which 'owns' the processes.


    :param input_queue: An input queue to serve new data (as ``IPCMessages``) to this process
    :type input_queue: queue.Queue | multiprocessing.Queue
    :param ensemble_name: The name of this ensemble
    :type ensemble_name: string
    '''

    def __init__(self, input_queue, mapping_func, ensemble_name=None, output_file='./output.log'):
        self.input_queue = input_queue
        self.connected_ensembles = {} # this is effectively a copy of the routing table, but may also contain additional metadata about ensemble capabilities to inform mapping
        self.output_file = output_file

        self.instantiated_graphs = {}

        self.mapping_func = mapping_func

        self.ensemble_name = ensemble_name
        self.sim = None
        self.sim_process = None

        self.logger = DebugLogger.get_logger('TTRuntimeManagerProcess-'+ensemble_name)

    def setup_process_interface(self, input_network_func, sim_process=None):
        '''
        Configure the interface to this process, meaning the callback functions for sending outputs to the other processes. This process needs a callback for each other runtime process, as it may receive inputs for any other process through the network.

        :param input_network_func: A callback function for providing ``IPCMessage`` inputs to the ``TTNetworkManagerProcess``
        :type input_network_func: functiond process that this class runs inside of. Mainly used for interrupting the simulated variant on input messages. dDefaults to None
        :param sim_process: A reference to the simulated process that this class runs inside of. Mainly used for interrupting the simulated variant on input messages. dDefaults to None
        :type sim_process: ``simpy.Process`` | None
        '''
        self.input_network_func = input_network_func
        self.sim_process = sim_process

    def input_msg_to_process(self, message):
        '''
        Callback use to provide messages to this process's input queue.

        If this is a simulated environment, we interrupt the process, which is otherwise waiting indefinitely for data to arrive on the queue.

        :param message: The message intended for this same ensemble
        :type message: IPCMessage
        '''
        self.input_queue.put(message)
        if self.sim and self.sim_process and self.sim.active_process != self.sim_process:
            self.logger.log(2, 'Interrupting!: t=%f' % self.sim.now)
            self.sim_process.interrupt() #would this generate too many interrupts if there are many inputs all at one time?



    def get_next_input(self):
        '''
        Pull the next input off the input queue.
        '''
        if self.sim:
            return self.input_queue.get_nowait()
        else:
            return self.input_queue.get(block=True, timeout=1) #FIXME: timeout value should be more configurable

    def run_sim(self, sim):
        '''
        The main run loop for a runtime environment using simulated processes, which runs on a single core and can implement many ensembles. Must be run as a ``simpy.Process``
        '''
        self.sim = sim
        self.logger.info('run sim loop RuntimeManager')
        next_msg = None
        try:
            while True:
                try:
                    next_msg = self.get_next_input()

                except queue.Empty:
                    try:
                        yield self.sim.timeout(math.inf)
                    except simpy.Interrupt:
                        continue
                except simpy.Interrupt:
                    continue
                if next_msg:
                    self.handle_message(next_msg)
                next_msg = None
        except KeyboardInterrupt:
            raise
        except BaseException as e:
            raise

    def run_phy(self):
        '''
        The main run loop for a runtime environment using physical processes, which can take advantage of multi-core processors.
        '''
        self.logger.info('run phy loop RuntimeManager')
        try:
            while True:
                try:
                    next_msg = self.get_next_input()
                except queue.Empty:
                    continue

                if next_msg:
                    self.handle_message(next_msg)

        except KeyboardInterrupt:
            return
        except BaseException as e:
            raise

    def handle_message(self, msg):
        '''
        Respond to an incoming message meant for this process. If the message type and recipient do not match expectations, this will return without notification
        '''

        if not isinstance(msg, IPCMessage): return
        if not isinstance(msg.msg_type, IPCMessageTypeRuntime): return
        if not msg.process_recipient == IPCMessageProcessRecipient.ProcessRuntimeManager: return

        msg_type = msg.msg_type
        self.logger.info('New message of type %s', msg_type)
        self.logger.debug('New message %s', msg)

        if msg_type == IPCMessageTypeRuntime.LogOutputToken:
            # an output token was produced and needs to be logged somewhere. Write in a common format so we can retrieve timestamps, values, and origin (SQ and ensemble)
            token, source_sq_name, source_ensemble_name = msg.payload
            with open(self.output_file, 'a') as f: #TODO: make this output file configurable. Maybe related to a particular graph. filename would need to be provided to the ensemble and passed from there, since that owns this runtime-manager process
                f.write(str(token)+'from SQ "' + source_sq_name + '" on ENS: "' + source_ensemble_name +  '".\r\n')

        elif msg_type == IPCMessageTypeRuntime.InstantiateAndMapGraph:
            # Instantiate the graph by mapping it to ensembles. Currently, that mapping happens here at runtime, but it could be done statically prior to this, so long as the set of ensembles in the expected system match those that are actually connected by the time this message arrives
            if type(msg.payload) != tuple:
                graph = msg.payload
            else:
                #TODO: define the format; may be an already-mapped graph
                graph = msg.payload[0]

            assert isinstance(graph, TTGraph), 'Graph should be a TTGraph, output from the compiler'

            #FIXME: provide more mapping options
            mapped_sqs = Mapper.TTMapper.random_mapping(graph, self.connected_ensembles)

            #distribute the clocks to each ensemble. This is before sending SQs because the SQ instantiation process often searches for a clock that will be used for marking new TTTime's or setting local timeouts. The clocks should already be known to those ensembles.
            # FIXME: only send the necessaary clocks to each ensemble
            for ens_name in list(self.connected_ensembles.keys()):
                self.logger.debug('Send clocks to ens: %s' % ens_name)
                msg_clocks_sync = IPCMessage(IPCMessageTypeSync.AddClocks, list(graph.clockDictionary.values()), IPCMessageProcessRecipient.ProcessInputTokens)
                msg_clocks_execute = IPCMessage(IPCMessageTypeExecute.AddClocks, list(graph.clockDictionary.values()), IPCMessageProcessRecipient.ProcessExecute)
                # Should the network manager have any knowledge of clocks? potential TODO.

                network_payload = (ens_name, [msg_clocks_sync, msg_clocks_execute])
                network_ipc_msg = IPCMessage(IPCMessageTypeNetwork.ForwardNetworkMessage, network_payload, IPCMessageProcessRecipient.ProcessNetwork)
                self.input_network_func(network_ipc_msg)

            #for each SQ, make a message to send the sync and execute parts. Arc destinations should be held in the output_arc's list of destinations, which go into the SQForward. Send the 3 messages to the same recipient ensemble (all wrapped into an array of IPCMessages)
            for sq in graph.sqList:
                assert isinstance(sq, SQ.TTSQ), 'graph.sqList should only contain TTSQ\'s'
                ensemble_name = mapped_sqs[sq.sq_name] #key is SQ name, value is the name of the ensemble it should be mapped to

                msg_instatiate_sync = IPCMessage(
                    IPCMessageTypeSync.InstantiateSQ, sq.sync,
                    IPCMessageProcessRecipient.ProcessInputTokens)
                msg_instantiate_execute = IPCMessage(
                    IPCMessageTypeExecute.InstantiateSQ, sq.execute,
                    IPCMessageProcessRecipient.ProcessExecute)
                msg_instantiate_forwarding = IPCMessage(
                    IPCMessageTypeNetwork.InstantiateSQ,
                    (sq.sq_name,
                     [output_arc.destMapping
                      for output_arc in sq.output_arcs]),
                    IPCMessageProcessRecipient.ProcessNetwork)

                network_payload = (ensemble_name, [msg_instatiate_sync, msg_instantiate_execute, msg_instantiate_forwarding])
                network_ipc_msg = IPCMessage(IPCMessageTypeNetwork.ForwardNetworkMessage, network_payload, IPCMessageProcessRecipient.ProcessNetwork)
                self.input_network_func(network_ipc_msg)


            self.instantiated_graphs[graph.graph_name] = (graph, mapped_sqs)
            # raise


        elif msg_type == IPCMessageTypeRuntime.ExecuteGraphOnInputs:
            #Start execution of the graph by sending the set of provided inputs to all SQs that receive from graph inputs. Tokens will be produced and percolate throughout the graph. Expected format is a graph and a dictionary whose keys are input-arc symbols and values are initial token values.
            graph = msg.payload[0]
            assert isinstance(graph, TTGraph)
            input_dict = msg.payload[1]
            graph_name = graph.graph_name

            graph_instance, mapping = self.instantiated_graphs.get(graph_name)

            self.logger.info('Prepare for execution of graph %s on inputs %s' % (graph_name, input_dict))

            # check inputs vs. the input arcs
            assert len(input_dict) == len(graph.input_arc_dict()), 'The number of input values and input arcs must be identical'

            for input_symbol in graph.input_arc_dict().keys():
                input_value = input_dict.get(input_symbol, 'Value not found')
                if input_value == 'Value not found':
                    raise ValueError('Input value for symbol %s not found in set of inputs; remember: there are no optional inputs to a graph' % input_symbol)

            self.logger.debug('Input check passed')

            ## find root clock for initial time values
            root_clock = None
            for clock_name in graph.clockDictionary.keys():
                clock = graph.clockDictionary.get(clock_name)
                if clock.is_root():
                    root_clock = clock

            # initial inputs carry infinite timestamps -- synchronization will be trivial
            clock_spec = Clock.TTClockSpec.fromClock(root_clock)
            base_time = Time.TTTimeSpec.infinite(clock_spec)

            for input_symbol in input_dict.keys():
                #find the input arc and value
                input_arc = graph.input_arc_dict()[input_symbol]
                input_value = input_dict.get(input_symbol)

                #create a token; we'll replicate it for each SQ
                base_tag = Tag.TTTag(context=Tag.DEFAULT_CONTEXT_ID)
                base_token = Token.TTToken(input_value, base_time, streaming=False, tag=base_tag)

                for dest in input_arc.destSQList:
                    port_numbers = dest.port_number_of_input_symbol(input_symbol) #one output arc may have be used more than once in the same downstream SQ. We support this.
                    for port_num in port_numbers:
                        # duplicate the token and set tag components for where exactly this token should go
                        token_to_send = base_token.copy_token()
                        token_to_send.tag.sq = dest.sq_name
                        token_to_send.tag.p = port_num
                        token_to_send.tag.e = mapping[dest.sq_name]

                        # create a message to carry this token into the network interface on this ensemble then into the synchornization process on the recipient ensemble.
                        token_input_IPC_message = IPCMessage(IPCMessageTypeSync.InputToken, token_to_send, IPCMessageProcessRecipient.ProcessInputTokens)
                        network_msg_payload = (mapping[dest.sq_name], token_input_IPC_message)
                        token_input_network_message = IPCMessage(IPCMessageTypeNetwork.ForwardNetworkMessage, network_msg_payload, IPCMessageProcessRecipient.ProcessNetwork)

                        self.input_network_func(token_input_network_message)

        elif msg_type == IPCMessageTypeRuntime.JoinTickTalkSystem:
            # an ensemble has asked to join the network. It's request includes its name and the address it prefers to receive on (this is used to add an entry to the routing table)
            ensemble_info = msg.payload
            self.connected_ensembles[ensemble_info['name']] = ensemble_info #what does this message actually contain? Must at least include a name and routing information (in sim, a TTEnsemble reference; in phy, a network address)

            #add this ensemble to the routing table
            add_to_routing_table_message = IPCMessage(IPCMessageTypeNetwork.AddRoutingTableEntry, (ensemble_info['name'], ensemble_info['address']), IPCMessageProcessRecipient.ProcessNetwork)
            self.input_network_func(add_to_routing_table_message)

            #propagate the rest of the routing table
            propagate_routing_table_message = IPCMessage(IPCMessageTypeNetwork.PropagateRoutingTable, ensemble_info['name'], IPCMessageProcessRecipient.ProcessNetwork)
            self.input_network_func(propagate_routing_table_message)
