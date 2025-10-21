import sys, os, traceback, pickle, time, datetime
import simpy
import threading

sys.path.insert(0, os.path.abspath('..'))
sys.path.insert(0, os.path.abspath('../tt/'))
sys.path.insert(0, os.path.abspath('./tt/'))

import DebugLogger, logging

logger = DebugLogger.get_logger('test.test-harness-runtime')
DebugLogger.set_base_logger_level(
    logging.DEBUG)  #must set the logging level early in execution env

import Ensemble
import RuntimeManager
import Graph
from IPC import *

import numpy
from matplotlib import pyplot as plt


def extract_value_from_line(line):
    if line[1:8] == 'TTToken':
        start_T_index = line.find('T:')
        value_str = line[9:start_T_index - 1]
        return value_str
    else:
        return None


def process_outputs(sim=False, output_file='./output.log'):
    phy_or_sim_str = 'phy'
    if sim: phy_or_sim_str = 'simulation'

    values = []

    with open(output_file, 'r') as f:
        lines = f.readlines()
        header_lines = []
        for i, line in enumerate(lines):
            if f'start execution of {phy_or_sim_str} (streaming_merge)' in line:
                header_lines.append(i)

        most_recent_set = lines[header_lines[-1]:]
        for line in most_recent_set:
            val = extract_value_from_line(line)
            if val != None:
                values.append(val)

    print(values)
    return values

def unpack_graph(filename):
    inpickle = open(filename, 'rb')
    graph = pickle.load(inpickle)
    assert isinstance(graph, Graph.TTGraph)

    return graph


def send_input_tokens(graph,
                      runtime_manager: RuntimeManager.TTRuntimeManager,
                      inputs={'trigger': 0xdeadbeef}):
    execute_graph_message = IPCMessage(
        IPCMessageTypeRuntime.ExecuteGraphOnInputs, (graph, inputs),
        IPCMessageProcessRecipient.ProcessRuntimeManager)

    logger.info('Sending token inputs\n\n\n\n\n\n')

    runtime_manager.pass_message_to_runtime_process(execute_graph_message)


def send_graph_sim(runtime_manager, sim, filename):

    yield sim.timeout(0)
    logger.info("Distribute Graph to ensembles")
    graph = unpack_graph(filename)
    instantiate_graph_msg = IPCMessage(
        IPCMessageTypeRuntime.InstantiateAndMapGraph, graph,
        IPCMessageProcessRecipient.ProcessRuntimeManager)
    runtime_manager.pass_message_to_runtime_process(instantiate_graph_msg)

    yield sim.timeout(0)

    send_input_tokens(graph, runtime_manager)


def simulated_run(filename, TIMEOUT=10000000000):
    try:

        with open('./output.log', 'a') as f:
            f.write('\nstart execution of simulation (streaming_merge) at %f\n' %
                    time.time())

        logger.info('setup sim')
        sim = simpy.Environment(initial_time=0)

        logger.info('setup ensembles')
        rtm = RuntimeManager.TTRuntimeManagerSim([], sim)

        logger.info('send graph inputs')
        sim.process(send_graph_sim(rtm, sim, filename))

        rtm.manager_ensemble.enter_steady_state(timeout=TIMEOUT)

        sim.run(until=TIMEOUT)

        output_list = process_outputs(sim=True)

    except KeyboardInterrupt:
        print('KB interrupt; exit physical test')
    except BaseException as e:
        traceback.print_exc()
        raise

    return output_list


def streaming_merge_phy(filename):
    try:
        with open('./output.log', 'a') as f:
            f.write('\nstart execution of phy (streaming_merge) at %f\n' %
                    time.time())

        rtm = RuntimeManager.TTRuntimeManagerPhysical(ip='127.0.0.1',
                                                      rx_port=2009,
                                                      tx_port=2010)
        rtm_address = '127.0.0.1:2009'

        time.sleep(.01)

        #setup an ensemble
        ens1 = Ensemble.TTEnsemble('ens1')
        ens1.setup_queues(is_sim=False)
        ens1.setup_physical_processes(network_ip='127.0.0.1',
                                      rx_network_port=20011,
                                      tx_network_port=20012)
        ens1.connect_to_TickTalk_network(rtm_address)
        # ens1.enter_steady_state(timeout=90)
        # input('finished 1st ensemble setup. hit enter\n\n')

        # time.sleep(2)

        #setup another ensemble
        ens2 = Ensemble.TTEnsemble('ens2')
        ens2.setup_queues(is_sim=False)
        ens2.setup_physical_processes(network_ip='127.0.0.1',
                                      rx_network_port=20013,
                                      tx_network_port=20014)
        ens2.connect_to_TickTalk_network(rtm_address)
        # ens2.enter_steady_state(timeout=90)
        input('finished 2nd ensemble setup. hit enter\n\n')
        # put the system into a steady state while it executes the rest of the program

        time.sleep(.01)

        graph = unpack_graph(filename)
        instantiate_graph_msg = IPCMessage(
            IPCMessageTypeRuntime.InstantiateAndMapGraph, graph,
            IPCMessageProcessRecipient.ProcessRuntimeManager)
        rtm.pass_message_to_runtime_process(instantiate_graph_msg)

        time.sleep(.01)

        input('wait... hit enter\n\n')
        send_input_tokens(graph, rtm)

        thread = threading.Thread(target=ens1.enter_steady_state, kwargs={'timeout':10}) #maintain steady state in a separate thread
        thread.setDaemon(True)
        thread.start() #this is actually pretty dangerous... multiprocessing won't work as the ensemble has unserializable members (queues/process handles)
        thread2 = threading.Thread(target=ens2.enter_steady_state, kwargs={'timeout':10}) #maintain steady state in a separate thread
        thread2.setDaemon(True)
        thread2.start()
        rtm.manager_ensemble.enter_steady_state(timeout=60)

        output_list = process_outputs(sim=False)

    except KeyboardInterrupt:
        print('KB interrupt; exit physical test')
    except BaseException as e:
        traceback.print_exc()
        raise

    return output_list


def main():

    ###Physical
    # streaming_merge_phy()

    # input('\n\n\nHit enter to continue with simulated test\n\n')
    # logger.critical("\n\n\nFinish physical test\n\n\nStart Simulated\n")

    ###Simulated
    t1 = time.time()
    # simulated_run("../output/ifelse.pickle")
    # streaming_merge_phy("../output/ifelse.pickle")
    streaming_merge_phy("../output/proposed_deadline_syntax.pickle")
    t2 = time.time()
    print(t2 - t1)

    logger.critical('\n****Ensemble Process Tests Done****\n')


if __name__ == "__main__":

    main()
