# Copyright 2021 Carnegie Mellon University
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


import sys, os, traceback, pickle, time, datetime
import simpy
import threading


sys.path.insert(0, os.path.abspath('..'))
sys.path.insert(0, os.path.abspath('../tt/'))
sys.path.insert(0, os.path.abspath('./tt/'))


import Ensemble
import RuntimeManager
import Graph
from IPC import *
import Time

import DebugLogger, logging
logger = DebugLogger.get_logger('test.runtime-manager')

def check_output_for_quadratic(solution=(3.0, -3.0), timeval=(-Time.TTTime.MAX_TIMESTAMP, Time.TTTime.MAX_TIMESTAMP)):
    correct = True
    line=None
    with open('output.log', 'r') as f:
        for next_line in f.readlines():
            line = next_line


    if line[1:8] == 'TTToken':
        pass
        open_paren = [i for i in range(len(line)) if line.startswith('(', i)]
        close_paren = [i for i in range(len(line)) if line.startswith(')', i)]
        assert len(open_paren) >= 2 and len(close_paren) >= 2
        value_str = line[open_paren[0]:close_paren[0]+1] # +1 for exclusive upper index
        time_str = line[open_paren[1]:close_paren[1]+1]

        if isinstance(eval(value_str), tuple):
            return_values = eval(value_str)
            if return_values == solution:
                logger.critical('The values are good: %s' % value_str)
            else: correct=False
        else: correct=False
        
        if isinstance(eval(time_str), tuple):
            return_times = eval(time_str)
            if return_times == timeval:
                logger.critical('The times are good! %s' % time_str)
            else: correct=False
        else: correct=False


    else: correct=False

    return correct


def unpack_graph(filename='../output/quadratic.pickle'):
    inpickle = open(filename, 'rb')
    graph = pickle.load(inpickle)
    assert isinstance(graph, Graph.TTGraph)
    return graph

def send_input_tokens(graph, runtime_manager: RuntimeManager.TTRuntimeManager, inputs={'a':1,'b':0,'c':-9}):
    execute_graph_message = IPCMessage(IPCMessageTypeRuntime.ExecuteGraphOnInputs, (graph, inputs), IPCMessageProcessRecipient.ProcessRuntimeManager)

    logger.info('Sending token inputs\n\n\n\n\n\n')

    runtime_manager.pass_message_to_runtime_process(execute_graph_message)


def send_graph_sim(runtime_manager, sim):

    # yield sim.timeout(5) #need to wait a bit so that the other ensembles can join; without this (in sim), the runtime manager will map everything to itself. TODO: make the simulated version of processes interrupted when something gets added to their queues, as we'll otherwise get have this issue with race conditions in simulation, and the sim will be slowed down by constantly polling queues. Will add some complexity, though. 
    yield sim.timeout(0)
    logger.info("Distribute Graph to ensembles")
    graph = unpack_graph()
    instantiate_graph_msg = IPCMessage(IPCMessageTypeRuntime.InstantiateAndMapGraph, graph, IPCMessageProcessRecipient.ProcessRuntimeManager)
    runtime_manager.pass_message_to_runtime_process(instantiate_graph_msg)

    yield sim.timeout(0)

    send_input_tokens(graph, runtime_manager)


def runtime_test_sim():
    try:

        TIMEOUT = 10000

        time_str = str(datetime.datetime.fromtimestamp(time.time()))
        with open('./output.log', 'a') as f:
            f.write('\r\nNew runtime manager test on simulated ensembles at %s\r\n' % time_str)

        logger.info('setup sim')
        sim = simpy.Environment(initial_time=0)

        logger.info('setup ensembles')
        rtm = RuntimeManager.TTRuntimeManagerSim([], sim)

        ens1 = Ensemble.TTEnsemble('ens1')
        ens1.setup_queues(is_sim=True)
        ens1.setup_simulation_processes(sim)
        ens1.connect_to_TickTalk_network(rtm.manager_ensemble)
        ens1.enter_steady_state(timeout=TIMEOUT)

        ens2 = Ensemble.TTEnsemble('ens2')
        ens2.setup_queues(is_sim=True)
        ens2.setup_simulation_processes(sim)
        ens2.connect_to_TickTalk_network(rtm.manager_ensemble)
        ens2.enter_steady_state(timeout=TIMEOUT)

        #incomplete test!
        # graph = unpack_graph()
        # instantiate_graph_msg = IPCMessage(IPCMessageTypeRuntime.InstantiateAndMapGraph, graph, IPCMessageProcessRecipient.ProcessRuntimeManager)
        # rtm.pass_message_to_runtime_process(instantiate_graph_msg)
        logger.info('send graph inputs')
        sim.process(send_graph_sim(rtm, sim))


        rtm.manager_ensemble.enter_steady_state(timeout=TIMEOUT)

        sim.run(until=TIMEOUT)

    except KeyboardInterrupt:
        print('KB interrupt; exit physical test')
    except BaseException as e:
        traceback.print_exc()
        raise
    finally:
        if check_output_for_quadratic():
            logger.critical('\n\nTest in simulated domain passed!')
            return True
        else: return False


def runtime_test_phy():
    try:
        time_str = str(datetime.datetime.fromtimestamp(time.time()))
        with open('./output.log', 'a') as f:
            f.write('\r\nNew runtime manager test on physical ensembles at %s\r\n' % time_str)

        logger.warning('NB: local runtime test may fail if any of the ports are currently in use; look at netstat | grep "LISTEN"')
        rtm = RuntimeManager.TTRuntimeManagerPhysical(ip='127.0.0.1', rx_port=2009, tx_port=2010)
        rtm_address = '127.0.0.1:2009'

        #setup an ensemble
        ens1 = Ensemble.TTEnsemble('ens1')
        ens1.setup_queues(is_sim=False)
        ens1.setup_physical_processes(network_ip='127.0.0.1', rx_network_port = 20011, tx_network_port = 20012)
        ens1.connect_to_TickTalk_network(rtm_address)

        # time.sleep(2)

        #setup another ensemble
        ens2 = Ensemble.TTEnsemble('ens2')
        ens2.setup_queues(is_sim=False)
        ens2.setup_physical_processes(network_ip='127.0.0.1', rx_network_port = 20013, tx_network_port = 20014)
        ens2.connect_to_TickTalk_network(rtm_address)

        #manage the program itself
        time.sleep(2)

        graph = unpack_graph()
        instantiate_graph_msg = IPCMessage(IPCMessageTypeRuntime.InstantiateAndMapGraph, graph, IPCMessageProcessRecipient.ProcessRuntimeManager)
        rtm.pass_message_to_runtime_process(instantiate_graph_msg)

        time.sleep(2)

        send_input_tokens(graph, rtm)


        #put the system into a steady state while it executes the rest of the program 
        thread = threading.Thread(target=ens1.enter_steady_state, kwargs={'timeout':10}) #maintain steady state in a separate thread
        thread.setDaemon(True)
        thread.start() #this is actually pretty dangerous... multiprocessing won't work as the ensemble has unserializable members (queues/process handles)  
        thread2 = threading.Thread(target=ens2.enter_steady_state, kwargs={'timeout':10}) #maintain steady state in a separate thread
        thread2.setDaemon(True)
        thread2.start() 
        rtm.manager_ensemble.enter_steady_state(timeout=10)
    except KeyboardInterrupt:
        print('KB interrupt; exit physical test')
    except BaseException as e:
        traceback.print_exc()
        raise

    finally:
        if check_output_for_quadratic():
            logger.critical('\n\nTest in physical domain passed!')
            return True
        else: return False


def main():

    DebugLogger.set_base_logger_level(logging.DEBUG)

    ###Physical
    result_phy = runtime_test_phy()

    # input('\n\n\nHit enter to continue\n\n')
    time.sleep(5)
    
    logger.critical("\n\n\nFinish physical test\n\n\nStart Simulated\n")

    ###Simulated
    result_sim =  runtime_test_sim()

    logger.critical('\n****Ensemble Process Tests Done****\n')

    time.sleep(2)
    DebugLogger.set_base_logger_level(logging.CRITICAL)


    return result_sim and result_phy


if __name__ == "__main__":

    result = main()
    logger.critical('Graph interpretation passed? %s' % result)
    print(result)