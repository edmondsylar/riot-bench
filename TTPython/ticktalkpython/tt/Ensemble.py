# Copyright 2021 Carnegie Mellon University
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

'''
An ensemble is defined as a collection of (possibly simulated) hardware elements like processor(s), memory, storage, network interfaces, sensors, actuators, clocks, etc.
It is the catch-all term for a device in the system, though we call them 'ensembles' to better reflect their heterogeneous nature.

The ensembles can be used in simulated and physical environments without relatively little difference from the user's perspective and none from the program-development perspective. The TTEnsemble handles the top-level mechanisms for the ensemble. The main roles include instantiating the processes and their interfaces to each other.
One ensemble exists as a ``TTRuntimeManager``, which helps set up the network among all devices and distribute the graph. That ensemble runs an additional process to handle this management plane.

The Ensemble setup process is as follows:

*  Create a set of thread/process-safe communication channels (queues)
*  Create a set of processes for SQ synchronization, execution, and networking/forwarding
*  Configure the interfaces between each process so they can exchange information at run time
*  Set up the ``TTNetworkInterface`` (within the ``TTNetworkManagerProcess``)
*  Contact the Runtime Manager Ensemble to request this ensemble 'join' the network
*  Configure the network interface to hold routing information to the other Ensembles; this information is provided bythe Runtime Manager
*  Await incoming network messages in a 'steady state'; an example of a message is a new SQ to be instantiated on this ensemble
*  Perform SQ synchronization, execution, and forwarding as input tokens arrive as part of Graph Interpretation
*  Tear down processes and network interfaces after some timeout or shutdown signal

'''

import time, math
import multiprocess
import queue
import simpy
import pickle

import NetworkInterfaceUDP

from Component import TTComponent
from Error import TTComponentError
import InputTokenProcess
import ExecuteProcess
import NetworkManagerProcess
import RuntimeManager
import TimedEventProcess
import Mapper
from IPC import *

import DebugLogger




class TTEnsemble():
    '''
    Each device in a TTPython graph interpretation environment is represented by an instance of ``TTEnsemble`` or an 'ensemble' in our parlance.

    An Ensemble also contains a collection of ``TTComponent`` instances representing the device's capabilities.
    These can be added, removed, and queried for using ``TTComponent`` instances. As such, a ``TTEnsemble`` should
    be viewed as both the specification and realization of a TTPython-compliant device.

    Each ``TTEnsemble`` implements a set of communicating processes (i.e., ``TTInputTokenProcess``, ``TTExecuteProcess``, and ``TTNetworkManagerProcess``),
    which follow the same paradigm: each reads data (in the form of ``IPCMessages``) from a single input queue, and the data self-describes its function,
    which the process handles in turn; these processes handle nearly all runtime operations. ``TTEnsemble`` creates and manages these processes

    :param name: A **unique** name for the ensemble. This is used to globally refer to an ensemble in the system
    :type name: string
    :param is_runtime_manager: An indicator to tell this ensemble to act as a runtime manager, which entails an additional runtime proceess (``TTRuntimeManagerProcess``)
    :type is_runtime_manager: bool, optional
    '''
    def __init__(self, name, is_runtime_manager=False):
        self.sqs = []
        self.name = name
        self.component_name_map = {}
        self.components = []

        self.sim = None
        self.logger = DebugLogger.get_logger('Ensemble-'+name)

        self.is_runtime_manager = is_runtime_manager


    def connect_to_TickTalk_network(self, runtime_manager_address, runtime_manager_name=RuntimeManager.RUNTIME_MANAGER_ENSEMBLE_NAME):
        '''
        Initiate a connection to the TickTalk network by sending a message to the Runtime Manager ensemble, whose address must be provided.
        To join the network, this ensemble will send a message over the network to the runtime manager, including its own address so the runtime
        manager can add that information to its routing table and propagate that information to all other connected ensembles. That version of
        the routing table will be propagated to this ensemble.

        :param runtime_manager_address: The address that the runtime manager can be access from over the network. In a simulated environment, this is simply a reference to that ensemble object (assuming the simulation environment is simpy, which runs in a single process). In a 'physical' environment (i.e., using a real network interface), this should be a port and ip (ip:port, e.g. '127.0.0.1:8425')
        :type runtime_manager_address: TTEnsemble | string
        :param runtime_manager_name: The name of the runtime manager ensemble. Defaults to RuntimeManager.RUNTIME_MANAGER_ENSEMBLE_NAME
        :type runtime_manager_name: string
        '''

        #add the runtime manager to the routing table first
        runtime_manager_routing_table_entry =  (runtime_manager_name, runtime_manager_address) #better get this right, or we'll fail to join entirely
        add_runtime_to_routing_table_msg = IPCMessage(IPCMessageTypeNetwork.AddRoutingTableEntry, runtime_manager_routing_table_entry, IPCMessageProcessRecipient.ProcessNetwork)
        self.network_manager_process.input_msg_to_process(add_runtime_to_routing_table_msg)

        #send a message to said runtime manager to join the network; must be sent over the network, so encapsulte IPCMessage in TTNetworkMessage
        self_info = {'name':self.name, 'address':self.address}
        join_msg = IPCMessage(IPCMessageTypeRuntime.JoinTickTalkSystem, self_info, IPCMessageProcessRecipient.ProcessRuntimeManager)
        network_msg_payload = (runtime_manager_name, join_msg)
        network_ipc_msg = IPCMessage(IPCMessageTypeNetwork.ForwardNetworkMessage, network_msg_payload, IPCMessageProcessRecipient.ProcessNetwork)
        self.network_manager_process.input_msg_to_process(network_ipc_msg)



    def addComponents(self, *components):
        '''
        Add one or more ``TTComponent`` instances to this ``TTEnsemble``
        If a component is already present as a member of the ensemble, it will be ignored,
        unless it is a different instance or TTComponent with the same 'name' property.

        :param components: a list of TTComponent objects.
        :type components: TTComponent

        '''
        for component in components:
            if(isinstance(component, TTComponent)):
                if(component.name in self.component_name_map):
                    if(id(component) != id(self.component_name_map[component.name])):
                        raise TTComponentError("A different TTComponent named '" + component.name + "' is already a part of this TTEnsemble.")
                else:
                    self.components.append(component)
                    self.component_name_map[component.name] = component
                    if(len(component.children) > 0):
                        self.addComponents(*component.children)
            else:
                raise TTComponentError("Only objects of type TTComponent can be added to an Ensemble.")

    def findComponent(self, query):
        '''
        :param query: a TTQuery object for a given device or devices.
        :type query: TTQuery
        '''
        result = []
        for component in self.components:
            if(query.test(component)): result.append(component)
        return result

    def pickleToFile(self, path):
        #unclear why this is part of TTEnsemble..
        file = open(path, "wb")
        pickle.dump(self, file)
        file.close()

    def removeComponent(self, component):
        '''
        :param component: the TTComponent instance to be removed
        :type component: TTComponent
        '''
        raise NotImplementedError('removeComponent is not yet implemented. When would we remove hardware from an ensemble?')


    def setup_queues(self, is_sim=False):
        '''
        Create the set of inter-process communication queues for this ensemble; there is one per process.
        In the simulated environment, we use the ordinary queue (which is faster than multiprocess.Queue due to virtual memory isolation).
        In the physical (non-simulated) environment, each process runs as a distinct process in the OS, so we use the multiprocess version of Queue.

        :param is_sim: a boolean indicator to tell whether this is a simulated runtime environment or not. Defaults to False
        :type is_sim: bool, optional
        :return: None
        '''
        if is_sim:
            q = queue.Queue
        else:
            q = multiprocess.Queue

        self.network_manager_queue = q()
        self.input_token_queue = q()
        self.execute_queue = q()
        if self.is_runtime_manager:
            self.runtime_manager_queue = q()
        else:
            self.runtime_manager_queue = None

    def setup_simulation_processes(self, sim):
        '''
        Setup the simulated processes for this ensemble, including one to handle & synchronize all arriving
        input tokens and another to schedule and execute enabled SQs.

        :param sim: A reference to a Simpy Environment, which is the backbone of simulation time and causality in the standalone graph simulator
        :type sim: ``simpy.Environment``
        :return: None
        '''
        ### These processes are implemented as threads within the same Python 3 process, unlike the 'phy' version which uses multiple processes at the OS level. That has higher overhead, but can utilize multiple cores. That is not an option here, since all ensembles need to access the same simpy execution environment.
        if self.execute_queue is None:
            raise ValueError('Queues should be setup before creating processes: call TTEnsemble.setup_queues first')

        self.sim = sim
        if self.sim is None:
            raise ValueError('Simulation environment (with simpy) must be configured before creating the processes')

        self.address = self #the address in the simulated version is actually

        #create the custom process objects
        self.input_token_process = InputTokenProcess.TTInputTokenProcess(self.input_token_queue, ensemble_name=self.name, wait_func=TimedEventProcess.wait, wait_until_func=TimedEventProcess.wait_until)
        self.execute_process = ExecuteProcess.TTExecuteProcess(self.execute_queue, ensemble_name=self.name)
        self.network_manager_process = NetworkManagerProcess.TTNetworkManagerProcess(self.network_manager_queue, ensemble_name=self.name)

        #start the processes within the simulation environment. They will not run until self.sim.run() does
        self.input_token_process_handle = self.sim.process(self.input_token_process.run_sim(self.sim))
        self.execute_process_handle = self.sim.process(self.execute_process.run_sim(self.sim))
        # self.timed_event_process_handle = self.sim.process(self.timed_event_process.run())
        self.network_manager_process_handle = self.sim.process(self.network_manager_process.run_sim(self.sim))

        # keep track of each process
        self.process_pool = [self.input_token_process_handle, self.execute_process_handle, self.network_manager_process_handle]

        #if this is a runtime manager, we need an additional process to handle that management plane
        if self.is_runtime_manager:
            mapping_function = Mapper.TTMapper.random_mapping
            if False:
                mapping_function = Mapper.simple_static_mapping
            self.runtime_manager_process = RuntimeManager.TTRuntimeManagerProcess(
                self.runtime_manager_queue,
                mapping_func=mapping_function,
                ensemble_name=self.name)
            self.runtime_manager_process_handle = self.sim.process(self.runtime_manager_process.run_sim(self.sim))
            self.process_pool.append(self.runtime_manager_process_handle)

        # Setup the process interfaces, primarily meaning the functions they should call to pass values to each other. We do this after creating them so they can hold onto a reference to their own process (mainly to avoiding interrupting themselves and throwing RuntimeErrors)
        self.input_token_process.setup_process_interface(self.execute_process.input_msg_to_process, sim_process=self.input_token_process_handle)
        self.execute_process.setup_process_interface(self.input_token_process.input_msg_to_process, self.network_manager_process.input_msg_to_process, sim_process=self.execute_process_handle)

        # if this is a runtime manager, then setup that interface; that process and the network manager directly communicate with each other
        if self.is_runtime_manager:
            self.network_manager_process.setup_process_interface(self.input_token_process.input_msg_to_process, self.execute_process.input_msg_to_process,input_runtime_manager_func=self.runtime_manager_process.input_msg_to_process, sim_process=self.network_manager_process_handle)
            self.runtime_manager_process.setup_process_interface(self.network_manager_process.input_msg_to_process, sim_process=self.runtime_manager_process_handle)
        else:
            self.network_manager_process.setup_process_interface(self.input_token_process.input_msg_to_process, self.execute_process.input_msg_to_process, sim_process=self.network_manager_process_handle)



    def setup_physical_processes(self, network_ip, rx_network_port=NetworkInterfaceUDP.RX_PORT, tx_network_port=NetworkInterfaceUDP.TX_PORT):
        '''
        Setup the distinct processes that will manage the SQ synchronization (input tokens), execution,
        and network managemement. These are implemented to take advantage of multicore ensembles like a Jetson TX/TX2.

        They must communicate using queues, which need to be created and shared between them *before*
        starting the processes to prevent runtime errors related to memory sharing.

        Setting up these processes includes setting up the ``TTNetworkManagerProcess``, which uses a UDP interface by default.
        It's configuration requires a network IP and ports for transmit and receive

        :param network_ip: the IP (v4) address of this ensemble
        :type network_ip: string (format 255.255.255.255)
        :param rx_network_port: The port this ensemble will expect to receive inputs from the network on. Defaults to ``NetworkInterfaceUDP.RX_PORT``
        :type rx_network_port: int, optional
        :param tx_network_port: The port this ensemble will use to send inputs. Our implementation of a UDP stack includes handshaking and acknowledged delivery; using a single port helps accomplish this. Defaults to ``NetworkInterfaceUDP.TX_PORT``
        :type tx_network_port: int, optional

        :return: None
        '''
        ### These processes do not directly share any memory, although the ``InputTokenProcess`` and ``ExecuteProcess`` both use the same syscalls to access the synchronized clock (of which the ``TTClocks`` derive their current timestamps from). This is an architectural decision meant to provide consistency and easily extensible interfaces. However, this abstraction does carry nontrivial overhead, particularly in terms of how long it takes to send data between processes (copying virtual memory, serializing objects, context-switching at the OS level). Implementing these processes as threads reduces context-switching and memory-sharing overhead, but prevents efficient use of multi-core processors.
        if self.execute_queue == None:
            raise ValueError('Queues should be setup before creating processes: call TTEnsemble.setup_queues first')

        self.address = network_ip + ':' + str(rx_network_port)

        ##Create the process classes
        self.input_token_process = InputTokenProcess.TTInputTokenProcess(self.input_token_queue, ensemble_name=self.name, wait_func=TimedEventProcess.wait, wait_until_func=TimedEventProcess.wait_until)
        self.execute_process = ExecuteProcess.TTExecuteProcess(self.execute_queue, ensemble_name=self.name)
        self.network_manager_process = NetworkManagerProcess.TTNetworkManagerProcess(self.network_manager_queue, ensemble_name=self.name)


        ##configure the interrfaces BEFORE starting processes; for simulated, setup the interfaces afterwards.
        self.input_token_process.setup_process_interface(self.execute_process.input_msg_to_process)
        self.execute_process.setup_process_interface(self.input_token_process.input_msg_to_process, self.network_manager_process.input_msg_to_process)

        if self.is_runtime_manager:
            mapping_function = Mapper.TTMapper.random_mapping
            if False:
                mapping_function = Mapper.simple_static_mapping
            self.runtime_manager_process = RuntimeManager.TTRuntimeManagerProcess(
                self.runtime_manager_queue,
                mapping_func=mapping_function,
                ensemble_name=self.name)
            self.runtime_manager_process.setup_process_interface(self.network_manager_process.input_msg_to_process)

            self.network_manager_process.setup_process_interface(self.input_token_process.input_msg_to_process, self.execute_process.input_msg_to_process, input_runtime_manager_func=self.runtime_manager_process.input_msg_to_process)
        else:
            self.network_manager_process.setup_process_interface(self.input_token_process.input_msg_to_process, self.execute_process.input_msg_to_process)


        ##Create the actual processes for the CPU/OS
        self.input_token_process_handle = multiprocess.Process(target=self.input_token_process.run_phy, args=[])
        # self.timed_event_process_handle = self.sim.process(self.timed_event_process.run())
        self.execute_process_handle = multiprocess.Process(target=self.execute_process.run_phy, args=[])
        self.network_manager_process_handle = multiprocess.Process(target=self.network_manager_process.run_phy, args=[network_ip, rx_network_port, tx_network_port])

        self.process_pool = [self.input_token_process_handle, self.execute_process_handle, self.network_manager_process_handle]


        if self.is_runtime_manager:
            self.runtime_manager_process_handle = multiprocess.Process(target=self.runtime_manager_process.run_phy, args=[])
            self.process_pool.append(self.runtime_manager_process_handle)
            self.runtime_manager_process_handle.start()

        # and start!
        self.input_token_process_handle.start()
        self.execute_process_handle.start()
        self.network_manager_process_handle.start()

        self.logger.info("processes started")

    def enter_steady_state(self, timeout=math.inf):
        '''
        Put the ensemble into a steady state after all processes have been spawned. This will let them receive and exchange messages through their IPC queues, but the processes will not return or join unless an error has occurred.

        This should NOT return unless a process fails or ends.

        :param timeout: The amount of time before the ensemble will end the processes and exit, defaults to no timeout (math.inf)
        :type timeout: float | int
        :return: None
        '''
        self.logger.info('Begin steady state')
        if self.sim:
            # the function contain s a 'yield', so it must be created as a simulted process. We will return after this.
            self.sim.process(self._enter_steady_state_simulated(timeout=timeout))
        else:
            # This function will block until timeout expiry or an error is triggered
            self._enter_steady_state_physical(timeout=timeout)

    def _enter_steady_state_simulated(self, timeout=math.inf):
        # Setup the ensemble to behave in a waiting state such that if a timeout expires or an internal process fails, the ensemble will signal error and exit
        ## for simulated environment, this means yielding to any

        if self.sim:
            #using simulated version; yield on processes. Environment should already be running (self.sim.run() called somewhere higher in the simulation environment (graph simulator))

            try:
                self.logger.info('Entering ensemble steady state (simulated)')
                yield simpy.AnyOf(self.sim, [simpy.events.AnyOf(self.sim, self.process_pool), self.sim.timeout(timeout)]) #if any return, kill the other processes and destruct
                self.logger.info('Exiting ensemble steady state(simulated)')

            except BaseException as e:
                import traceback
                self.logger.error(f"Exception in steady state: {e}")
                self.logger.error(traceback.format_exc())
                raise

            finally:
                self.logger.warning("Shutting down child processes")
                for proc in self.process_pool:
                    try:
                        proc.interrupt('Process returned --> Failure somewhere. Exit')
                    except (RuntimeError, KeyboardInterrupt):
                        pass
        else:
            raise ValueError("Using simulated mode in the steady state, but a simulation environment does not exist!")


    def _enter_steady_state_physical(self, timeout=math.inf):
        # Setup the ensemble to behave in a waiting state such that if a timeout expires or an internal process fails, the ensemble will signal error and exit
        ## For physical environment, we'll simply poke the instantiated proocess periodically to see if they're alive. If so, keep going (but also check for timeout)
        if not self.sim:
            #using real processes; suspend the main thread/process until something fails
            start_time = time.time()
            try:
                self.logger.info('Entering ensemble steady state')
                while True:
                    for proc in self.process_pool:
                        try:
                            proc.join(timeout=5) #longish timeout on awaiting join (only happens if process returns) to ensure we don't add much load to the processor
                            if not proc.is_alive():
                                break  # a process died; something must be wrong
                            if time.time() >= start_time + timeout:
                                self.logger.critical('Timeout of %f hit (started at %.0f, end at %f); exiting ensemble' % (timeout, start_time, time.time()))
                                raise TimeoutError
                        except: raise

            except TimeoutError: pass
            except KeyboardInterrupt:
                self.logger.critical('*****Keyboard interrupt; exiting steady state****')
            finally:
                self.logger.warning('Exiting ensemble steady state')
                self.logger.warning("Shutting down child processes")
                for proc in self.process_pool:
                    # proc.close()
                    try:
                        proc.kill()
                    # except KeyboardInterrupt:
                    #     pass
                    except BaseException as e:
                        self.logger.error(e.with_traceback('bleh'))
                    finally:
                        pass
        else:
            raise ValueError("Using physical mode in the steady state, but a simulation environment exists!")


    def receive_network_message(self, message):
        # this is really only used by the simulated environment since we directly share ensemble references in lieu of a real network interface
        self.network_manager_process.input_msg_to_process(message)
