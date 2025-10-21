#!/usr/bin/python

import logging, pickle, simpy, sys, time
import argparse

sys.path.append('tt/')
import DebugLogger
import Ensemble
import RuntimeManager
import Graph
from IPC import *


def unpack_graph(filename):
    inpickle = open(filename, 'rb')
    graph = pickle.load(inpickle)
    assert isinstance(graph, Graph.TTGraph)
    return graph


def send_input_tokens(graph,
                      runtime_manager,
                      logger,
                      inputs={'trigger': 0xdeadbeef}):
    execute_graph_message = IPCMessage(
        IPCMessageTypeRuntime.ExecuteGraphOnInputs, (graph, inputs),
        IPCMessageProcessRecipient.ProcessRuntimeManager)

    logger.info('Sending token inputs\n\n\n\n\n\n')

    runtime_manager.pass_message_to_runtime_process(execute_graph_message)


def send_graph_sim(runtime_manager, sim, filename, logger, custom_inputs=None):
    yield sim.timeout(0)
    logger.info("Distribute Graph to ensembles")
    graph = unpack_graph(filename)
    instantiate_graph_msg = IPCMessage(
        IPCMessageTypeRuntime.InstantiateAndMapGraph, graph,
        IPCMessageProcessRecipient.ProcessRuntimeManager)
    runtime_manager.pass_message_to_runtime_process(instantiate_graph_msg)

    yield sim.timeout(0)
    if custom_inputs is not None:
        send_input_tokens(graph, runtime_manager, logger, inputs=custom_inputs)
    else:
        send_input_tokens(graph, runtime_manager, logger)


def main():
    parser = argparse.ArgumentParser(
        description=
        'simulate an execution of a compiled TTPython dataflow graph')

    parser.add_argument('file',
                        metavar='F',
                        type=str,
                        help='the pickled dataflow graph to simulate')
    parser.add_argument(
        '--timeout',
        type=int,
        default=60,
        help='simulation timeout (default: 1000000000 (logical ticks))')
    parser.add_argument(
        '--input',
        '-i',
        action='append',
        metavar='KEY=VALUE',
        help='graph input in KEY=VALUE format (can be specified multiple times). Example: -i a=5 -i b=3')
    args = parser.parse_args()
    file = args.file
    timeout = args.timeout
    
    # Parse custom inputs
    custom_inputs = None
    if args.input:
        custom_inputs = {}
        for input_pair in args.input:
            if '=' not in input_pair:
                print(f"Error: Input '{input_pair}' must be in KEY=VALUE format")
                sys.exit(1)
            key, value = input_pair.split('=', 1)
            # Try to parse as int, float, or keep as string
            try:
                custom_inputs[key] = int(value)
            except ValueError:
                try:
                    custom_inputs[key] = float(value)
                except ValueError:
                    custom_inputs[key] = value

    outfile = './output.log'
    name = file.split('/')[-1][:-7]

    logger = DebugLogger.get_logger(name)
    logger.warning("simulation is incompatible with new SQ execution model")

    with open(outfile, 'a') as f:
        f.write(f"\nstart execution of simulation ({name}) at %f\r\n" %
                time.time())

    logger.info('setup sim')
    sim = simpy.Environment(initial_time=0)

    logger.info('setup ensembles')
    rtm = RuntimeManager.TTRuntimeManagerSim([], sim)

    logger.info('send graph inputs')
    sim.process(send_graph_sim(rtm, sim, file, logger, custom_inputs))

    rtm.manager_ensemble.enter_steady_state(timeout=timeout)

    sim.run(until=timeout)


if __name__ == "__main__":
    main()
