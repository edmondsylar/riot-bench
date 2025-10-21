# Copyright 2021 Carnegie Mellon University
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import sys, os, traceback, pickle, time
import re


sys.path.insert(0, os.path.abspath('..'))
sys.path.insert(0, os.path.abspath('../tt/'))
sys.path.insert(0, os.path.abspath('./tt/'))


import Ensemble
import RuntimeManager
import Graph
from IPC import *
import DebugLogger, logging
DebugLogger.set_base_logger_level(logging.INFO)
logger = DebugLogger.get_logger('test.runtime-manager')

import numpy
from matplotlib import pyplot as plt

def extract_output_info_from_line(line):
    value = None
    source_sq = None
    source_ensemble = None
    t = None
    if line[1:8] == 'TTToken':
        start_T_index = line.find('T:')
        value_str = line[9:start_T_index-1]
        value =  float(value_str)
        
        
        open_paren_indices = [ i.start() for i in re.finditer('\(', line)]
        close_paren_indices = [ i.start() for i in re.finditer('\)', line)]
        timestamps_str = line[open_paren_indices[-1]+1 : close_paren_indices[-1]]
        start_time = int(timestamps_str.split(',')[0])
        stop_time = int(timestamps_str.split(',')[1])
        t = (start_time +stop_time) / 2 
   
        start_SQ_index = line.find('from SQ "')
        end_SQ_index = line.find('" on ENS: "' )
        source_sq = line[start_SQ_index+len('from SQ "') : end_SQ_index]
        
        start_ensemble_index = end_SQ_index
        end_ensemble_index = line.find('".') #not very unique..
        source_ensemble = line[start_ensemble_index+len('" on ENS: "') : end_ensemble_index]

    return value, source_sq, source_ensemble, t




def process_outputs(sim=False, output_file='./output.log', output_SQ_names=['ADD-16', 'movingAverage-17']):
    phy_or_sim_str = 'phy'
    if sim: phy_or_sim_str = 'simulation'
    values = [[] for i in range(len(output_SQ_names))]
    times = [[] for i in range(len(output_SQ_names))]
    source_ensembles = [None for i in range(len(values))]
    with open(output_file, 'r') as f:
        lines = f.readlines()
        header_lines = []
        for i, line in enumerate(lines):
            if f'start execution of {phy_or_sim_str} (streaming_merge)' in line:
                header_lines.append(i)

        most_recent_set = lines[header_lines[-1]:]
        for line in most_recent_set:
            val, sq, ens, timestamp = extract_output_info_from_line(line)
            if val != None:
                try:   
                    sq_index = output_SQ_names.index(sq)

                    values[sq_index].append(val)
                    times[sq_index].append(timestamp)
                    source_ensembles[sq_index] = ens #assume this cannot be more than one
                except: pass
            

    print(output_SQ_names)
    print(source_ensembles)
    for i, sq_name in enumerate(output_SQ_names):
        plt.plot(times[i], values[i], 'b.')
        plt.title("'" + sq_name + "' output from Ensemble '" + source_ensembles[i] + "'")
        plt.ylabel('Token Value') #we're just going to assume numeric
        plt.xlabel('Time')
        plt.show()


def unpack_graph(filename='../output/streaming_merge.pickle'):
    inpickle = open(filename, 'rb')
    graph = pickle.load(inpickle)
    assert isinstance(graph, Graph.TTGraph)

    return graph



def send_input_tokens(graph, runtime_manager: RuntimeManager.TTRuntimeManager, inputs={'trigger':0xdeadbeef}):
    execute_graph_message = IPCMessage(IPCMessageTypeRuntime.ExecuteGraphOnInputs, (graph, inputs), IPCMessageProcessRecipient.ProcessRuntimeManager)

    logger.info('Sending token inputs\n\n\n\n\n\n')

    runtime_manager.pass_message_to_runtime_process(execute_graph_message)

def run_application_rtm(ip, port):
    try:
        with open('./output.log', 'a') as f:
            f.write('\nstart execution of phy (streaming_merge) at %f\n' % time.time())

        rtm = RuntimeManager.TTRuntimeManagerPhysical(ip=ip, rx_port=port, tx_port=port+1)

        time.sleep(1)
        print('waiting for devices to connect')
        time.sleep(5)
        input('wait for devices to connect... hit enter\n\n')

        graph = unpack_graph()
        instantiate_graph_msg = IPCMessage(IPCMessageTypeRuntime.InstantiateAndMapGraph, graph, IPCMessageProcessRecipient.ProcessRuntimeManager)
        rtm.pass_message_to_runtime_process(instantiate_graph_msg)

        time.sleep(1)
        input('wait... hit enter to send input\n\n')
        send_input_tokens(graph, rtm)

        rtm.manager_ensemble.enter_steady_state(timeout=60)

        process_outputs()

    except KeyboardInterrupt:
        print('KB interrupt; exit physical test')
    except BaseException as e:
        traceback.print_exc()
        raise

    

if __name__ == "__main__":
    argc = len(sys.argv)
    ip, port = None, None

    if argc == 2:
        ip_port = sys.argv[1]
        ip = ip_port.trim().split(':')[0]
        port = int(ip_port.trim().split(':')[1])
    elif argc == 3:
        ip = sys.argv[1]
        port = int(sys.argv[2])
    else:
        raise ValueError('gonna need that ip and port as CLI args, dawg. ')

    input('\n\n\nHit enter to start test\n\n')

    run_application_rtm(ip, port)
