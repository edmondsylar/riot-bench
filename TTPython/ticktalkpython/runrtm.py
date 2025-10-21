#!/usr/bin/python

import logging, pickle, simpy, sys, time, traceback

sys.path.append('tt/')
import DebugLogger
import Ensemble
import RuntimeManager
import Graph
import argparse
from IPC import *


def extract_output_info_from_line(line):
    value = None
    source_sq = None
    source_ensemble = None
    t = None
    if line[1:8] == 'TTToken':
        start_T_index = line.find('T:')
        value_str = line[9:start_T_index - 1]
        value = float(value_str)

        open_paren_indices = [i.start() for i in re.finditer('\(', line)]
        close_paren_indices = [i.start() for i in re.finditer('\)', line)]
        timestamps_str = line[open_paren_indices[-1] +
                              1:close_paren_indices[-1]]
        start_time = int(timestamps_str.split(',')[0])
        stop_time = int(timestamps_str.split(',')[1])
        t = (start_time + stop_time) / 2

        start_SQ_index = line.find('from SQ "')
        end_SQ_index = line.find('" on ENS: "')
        source_sq = line[start_SQ_index + len('from SQ "'):end_SQ_index]

        start_ensemble_index = end_SQ_index
        end_ensemble_index = line.find('".')  #not very unique..
        source_ensemble = line[start_ensemble_index +
                               len('" on ENS: "'):end_ensemble_index]

    return value, source_sq, source_ensemble, t


def unpack_graph(filename):
    inpickle = open(filename, 'rb')
    graph = pickle.load(inpickle)
    assert isinstance(graph, Graph.TTGraph)
    return graph


def send_input_tokens(graph,
                      logger,
                      runtime_manager: RuntimeManager.TTRuntimeManager,
                      inputs={'trigger': 0xdeadbeef}):
    execute_graph_message = IPCMessage(
        IPCMessageTypeRuntime.ExecuteGraphOnInputs, (graph, inputs),
        IPCMessageProcessRecipient.ProcessRuntimeManager)

    logger.info('Sending token inputs\n\n\n\n\n\n')

    runtime_manager.pass_message_to_runtime_process(execute_graph_message)


def run_application_rtm(name, graph, ip, port, logger, timeout):
    try:
        with open('./output.log', 'a') as f:
            f.write(f'\nstart execution of phy ({name}) at %f\n' % time.time())

        rtm = RuntimeManager.TTRuntimeManagerPhysical(ip=ip,
                                                      rx_port=port,
                                                      tx_port=port + 1)

        time.sleep(1)
        print('waiting for devices to connect')
        time.sleep(5)
        input('wait for devices to connect... hit enter\n\n')

        graph = unpack_graph(graph)
        instantiate_graph_msg = IPCMessage(
            IPCMessageTypeRuntime.InstantiateAndMapGraph, graph,
            IPCMessageProcessRecipient.ProcessRuntimeManager)
        rtm.pass_message_to_runtime_process(instantiate_graph_msg)

        time.sleep(1)
        input('wait... hit enter to send input\n\n')
        send_input_tokens(graph, logger, rtm)

        rtm.manager_ensemble.enter_steady_state(timeout)

    except KeyboardInterrupt:
        print('KB interrupt; exit physical test')
    except BaseException as e:
        traceback.print_exc()
        raise


def main():
    parser = argparse.ArgumentParser(
        description='instantiate the runtime manager for a TTPython program')

    parser.add_argument('file',
                        metavar='F',
                        type=str,
                        help='the pickled dataflow graph to execute')
    parser.add_argument(
        '--ip',
        default='127.0.0.1',
        help='the ip of the runtime manager (default: localhost:127.0.0.1)')
    parser.add_argument('port', help='the port of the runtime manager')
    parser.add_argument('--timeout',
                        default=60,
                        type=float,
                        help='runtime manager timeout (default: 60 (sec))')

    args = parser.parse_args()
    filename = args.file
    ip = args.ip
    port = int(args.port)
    timeout = args.timeout

    # remove .pickle file extension
    name = filename.split('/')[-1][:-7]

    logger = DebugLogger.get_logger(name)

    input('\n\n\nHit enter to start test\n\n')
    run_application_rtm(name, filename, ip, port, logger, timeout)


if __name__ == "__main__":
    main()
