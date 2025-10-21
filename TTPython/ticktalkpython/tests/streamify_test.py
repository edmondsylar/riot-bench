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


import DebugLogger, logging
logger = DebugLogger.get_logger('test.streamify-runtime')
DebugLogger.set_base_logger_level(logging.CRITICAL) #must set the logging level early in execution env

import Ensemble
import RuntimeManager
import Graph
from IPC import *



def unpack_graph(filename='../output/streamify_syntax_helper.pickle'):
    inpickle = open(filename, 'rb')
    graph = pickle.load(inpickle)
    assert isinstance(graph, Graph.TTGraph)

    return graph


def send_input_tokens(graph, runtime_manager: RuntimeManager.TTRuntimeManager, inputs={'trigger':0xdeadbeef}):
    execute_graph_message = IPCMessage(IPCMessageTypeRuntime.ExecuteGraphOnInputs, (graph, inputs), IPCMessageProcessRecipient.ProcessRuntimeManager)

    logger.info('Sending token inputs\n\n\n\n\n\n')

    runtime_manager.pass_message_to_runtime_process(execute_graph_message)

def send_graph_sim(runtime_manager, sim):
 
    yield sim.timeout(0)
    logger.info("Distribute Graph to ensembles")
    graph = unpack_graph()
    instantiate_graph_msg = IPCMessage(IPCMessageTypeRuntime.InstantiateAndMapGraph, graph, IPCMessageProcessRecipient.ProcessRuntimeManager)
    runtime_manager.pass_message_to_runtime_process(instantiate_graph_msg)

    yield sim.timeout(0)

    send_input_tokens(graph, runtime_manager)


def streamify_test_sim():
    try:

        with open('./output.log', 'a') as f:
            f.write('\nstart execution of simulation (streamify_test) at %f\r\n' % time.time())

        TIMEOUT = 10000000000


        logger.info('setup sim')
        sim = simpy.Environment(initial_time=0)

        logger.info('setup ensembles')
        rtm = RuntimeManager.TTRuntimeManagerSim([], sim)

        logger.info('send graph inputs')
        sim.process(send_graph_sim(rtm, sim))

        rtm.manager_ensemble.enter_steady_state(timeout=TIMEOUT)

        sim.run(until=TIMEOUT)


    except KeyboardInterrupt:
        print('KB interrupt; exit physical test')
    except BaseException as e:
        traceback.print_exc()
        raise


def streamify_test_phy():
    try:
        with open('./output.log', 'a') as f:
            f.write('\nstart execution of phy (streamify_test) at %f\r\n' % time.time())

        rtm = RuntimeManager.TTRuntimeManagerPhysical(ip='127.0.0.1', rx_port=2009, tx_port=2010)
        rtm_address = '127.0.0.1:2009'

        time.sleep(.01)
        input('wait... hit enter\n\n')

        graph = unpack_graph()
        instantiate_graph_msg = IPCMessage(IPCMessageTypeRuntime.InstantiateAndMapGraph, graph, IPCMessageProcessRecipient.ProcessRuntimeManager)
        rtm.pass_message_to_runtime_process(instantiate_graph_msg)

        time.sleep(.01)

        input('wait... hit enter\n\n')
        send_input_tokens(graph, rtm)


        rtm.manager_ensemble.enter_steady_state(timeout=20)


        process_outputs(sim=False)


    except KeyboardInterrupt:
        print('KB interrupt; exit physical test')
    except BaseException as e:
        traceback.print_exc()
        raise

def main():

    ###Physical
    # streamify_test_phy()

    input('\n\n\nHit enter to continue with simulated test\n\n')
    # time.sleep(5)
    
    logger.critical("\n\n\nFinish physical test\n\n\nStart Simulated\n")

    ###Simulated
    t1 = time.time()
    streamify_test_sim()
    t2 = time.time()
    print(t2-t1)
    logger.critical('\n****Ensemble Process Tests Done****\n')



if __name__ == "__main__":

    main()