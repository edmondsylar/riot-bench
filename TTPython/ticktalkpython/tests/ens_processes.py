# Copyright 2021 Carnegie Mellon University
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# Created by Reese Grimsley July 2021


from copy import deepcopy
import sys, os, traceback, pickle, time
import simpy

sys.path.insert(0, os.path.abspath('..'))
sys.path.insert(0, os.path.abspath('../tt/'))
sys.path.insert(0, os.path.abspath('./tt/'))

import DebugLogger, logging
logger = DebugLogger.get_logger('test.ens_processes')
# DebugLogger.set_base_logger_level(15)
# logger.setLevel(15)

import Ensemble
import Network
import Graph
import SQ
from IPC import *
import Arc
import NetworkInterfaceUDP

import Clock
import Time
import Tag
import Token


# DebugLogger.set_base_logger_level(1)
# # logger = DebugLogger.get_logger('TEST.ens_processes')
# logger = DebugLogger.get_base_logger()
# logger.setLevel(1)
# import logging
# logging.basicConfig(level=1)
# logger = logging.getLogger('TEST:ens_processes')
# logger.setLevel(1)


def unpack_graph(filename='../output/quadratic.pickle'):
    inpickle = open(filename, 'rb')
    graph = pickle.load(inpickle)
    return graph

def get_example_sq(graph:Graph.TTGraph):
    sq = None
    for i, sq in enumerate(graph.sqList):
        sq_name = sq.sq_name
        if sq.output_arc != None and 'CONST' not in sq_name and 'TIME_TOKEN' not in sq_name:
            return sq
            
def inject_messages(ensemble: Ensemble.TTEnsemble, is_sim=False):
    sq = get_example_sq(unpack_graph())
    assert isinstance(sq, SQ.TTSQ)

    #### Control inputs
    #Add SQ
    sync_instantiate_message = IPCMessage(IPCMessageTypeSync.InstantiateSQ, sq.sync, IPCMessageProcessRecipient.ProcessInputTokens)
    ensemble.input_token_queue.put(sync_instantiate_message)
    execute_instantiate_message = IPCMessage(IPCMessageTypeExecute.InstantiateSQ, sq.execute, IPCMessageProcessRecipient.ProcessExecute)
    ensemble.execute_queue.put(execute_instantiate_message)

    dest_ensemble_name = ensemble.name
    payload = (sq.sq_name, [Arc.TTArcDestination(dest_ensemble_name, 'MULT-8', 0), Arc.TTArcDestination(dest_ensemble_name, 'ADD-9', 1)])
    network_mapping_instantiate_message = IPCMessage(IPCMessageTypeNetwork.InstantiateSQ, payload, IPCMessageProcessRecipient.ProcessNetwork)
    ensemble.network_manager_queue.put(network_mapping_instantiate_message)

    print('injected SQ instantiation messages')

    #Add Clocks
    root_clock = Clock.TTClock('root', None, 1, 0)
    child_1 = Clock.TTClock('child1', root_clock, 1, 0)
    child_2 = Clock.TTClock('child2', root_clock, 1, 0)
    child_3 = Clock.TTClock('childchild1', child_1, 1, 0)
    clocks = [root_clock, child_1, child_2, child_3]

    sync_add_clocks_message = IPCMessage(IPCMessageTypeSync.AddClocks, clocks, IPCMessageProcessRecipient.ProcessInputTokens)
    ensemble.input_token_queue.put(sync_add_clocks_message)

    execute_add_clocks_message = IPCMessage(IPCMessageTypeExecute.AddClocks, clocks, IPCMessageProcessRecipient.ProcessExecute)
    ensemble.execute_queue.put(execute_add_clocks_message)

    #### MGMT layer inputs
    if is_sim:
        routing_table = {ensemble.name:ensemble}
    else:
        # routing_table = {'ens1':'173.145.9.12:8425', 'ens2':'173.145.9.13:8425', 'ens3':'173.145.9.14:8425'}
        routing_table = {ensemble.name:'127.0.0.1:8225'}
    add_routing_message = IPCMessage(IPCMessageTypeNetwork.AddRoutingTableEntry, routing_table, IPCMessageProcessRecipient.ProcessNetwork)
    ensemble.network_manager_queue.put(add_routing_message)

    #### Data layer inputs

    #insert token
    root_clock_spec = Clock.TTClockSpec('root')
    time_spec = Time.TTTimeSpec(root_clock_spec, 0, 10)
    tag = Tag.TTTag(context='u1', sq=sq.sq_name, port=0, ensemble_name=ensemble.name)
    token = Token.TTToken(2, time_spec, tag=tag)

    token_input_message = IPCMessage(IPCMessageTypeSync.InputToken, token, IPCMessageProcessRecipient.ProcessInputTokens)
    ensemble.input_token_queue.put(token_input_message)

    second_tag = deepcopy(tag)
    second_tag.p = 1
    second_token = Token.TTToken(3, time_spec, tag=second_tag)
    token_input_message = IPCMessage(IPCMessageTypeSync.InputToken, second_token, IPCMessageProcessRecipient.ProcessInputTokens)
    ensemble.input_token_queue.put(token_input_message)


    
def inject_messages_quadratic_program(ensemble, sim=None, include_timed_messages=True):
    graph = unpack_graph()

    ###setup clocks
    root_clock = Clock.TTClock.root()
    child_1 = Clock.TTClock('child1', root_clock, 10, 5)
    child_2 = Clock.TTClock('child2', root_clock, 5, 0)
    child_3 = Clock.TTClock('childchild1', child_1, 10, 1)
    clocks = [root_clock, child_1, child_2, child_3]
    # if simulated, the clock's root needs to be changed now so we can call clock.now()
    if sim: 
        Clock.TTClock.__set_root_now__(now_func=lambda: sim.now, ticks_per_second=1, root=root_clock) #will 'self' work here? This may be called from a different context


    sync_add_clocks_message = IPCMessage(IPCMessageTypeSync.AddClocks, clocks, IPCMessageProcessRecipient.ProcessInputTokens)
    ensemble.input_token_queue.put(sync_add_clocks_message)

    execute_add_clocks_message = IPCMessage(IPCMessageTypeExecute.AddClocks, clocks, IPCMessageProcessRecipient.ProcessExecute)
    ensemble.execute_queue.put(execute_add_clocks_message)

    ### setup routing table
    if sim:
        routing_table = {ensemble.name:ensemble}
    else:
        # routing_table = {'ens1':'173.145.9.12:8425', 'ens2':'173.145.9.13:8425', 'ens3':'173.145.9.14:8425'}
        routing_table = {ensemble.name:'127.0.0.1:8225'}
    add_routing_message = IPCMessage(IPCMessageTypeNetwork.AddRoutingTableEntry, routing_table, IPCMessageProcessRecipient.ProcessNetwork)
    ensemble.network_manager_queue.put(add_routing_message)


    ###Instantiate SQs
    for sq in graph.sqList:

        #sync
        sync_instantiate_message = IPCMessage(IPCMessageTypeSync.InstantiateSQ, sq.sync, IPCMessageProcessRecipient.ProcessInputTokens)
        ensemble.input_token_queue.put(sync_instantiate_message)

        #execute
        execute_instantiate_message = IPCMessage(IPCMessageTypeExecute.InstantiateSQ, sq.execute, IPCMessageProcessRecipient.ProcessExecute)
        ensemble.execute_queue.put(execute_instantiate_message)

        #forwarding
        downstream_destinations = []
        for dest_sq in sq.output_arc.destSQList:
            port_number = dest_sq.port_number_of_input_symbol(sq.output_arc.symbol)
            for pn in port_number: # loop is necessary if an output arc connects to multiple input arcs *in the same SQ* (like squaring a number by MULTiplying)
                # possibly mulitple instances of the same symbol at the same SQ!
                arc_destination = Arc.TTArcDestination(ensemble.name, dest_sq.sq_name, pn)
                if not arc_destination in downstream_destinations:
                    logger.debug('Adding arc_destination %s to intermediate-arc symbol %s' % (arc_destination, sq.output_arc.symbol)) 
                    downstream_destinations.append(arc_destination)
        if len(downstream_destinations) > 0:
            payload = (sq.sq_name, downstream_destinations)
            network_mapping_instantiate_message = IPCMessage(IPCMessageTypeNetwork.InstantiateSQ, payload, IPCMessageProcessRecipient.ProcessNetwork)
            ensemble.network_manager_queue.put(network_mapping_instantiate_message)
        else: 
            logger.info('No downstream SQ for symbol %s; must be an output arc' % sq.output_arc.symbol)

    # let things settle

    time.sleep(1)
    #### input data values
    a = 1
    b = 0
    c = -4
    base_time = Time.TTTimeSpec(Clock.TTClockSpec.fromClock(root_clock), 0, 1)
    input_vals = [a,b,c]
    #iterate over the input arcs and their destinations to provide the input values
    for i, input_arc_key in enumerate(graph.input_arc_dict().keys()):
        # break
        arc = graph.input_arc_dict().get(input_arc_key)
        input_val = input_vals[i]

        base_tag = Tag.TTTag(context='u1')
        base_token = Token.TTToken(input_val, base_time, tag=base_tag)

        for dest in arc.destSQList:
            port_numbers = dest.port_number_of_input_symbol(arc.symbol)
            for port_number in port_numbers:
                token_to_send = base_token.copy_token()
                token_to_send.tag.sq = dest.sq_name
                token_to_send.tag.p = port_number
                token_to_send.tag.e = ensemble.name
                token_input_IPC_message = IPCMessage(IPCMessageTypeSync.InputToken, token_to_send, IPCMessageProcessRecipient.ProcessInputTokens)
                # ensemble.input_token_queue.put(token_input_IPC_message)
                token_input_network_message = Network.TTNetworkMessage(token_input_IPC_message, ensemble.name)

                ensemble.network_manager_queue.put(token_input_network_message)

    if include_timed_messages:
        time.sleep(5)
        logger.critical('\n\n\n\n\nSending timed inputs')
        input_vals[2] = -9
        now = root_clock.now()+2
        release_time = now + 10*root_clock.ticks_per_second()
        base_time = Time.TTTimeSpec(Clock.TTClockSpec.fromClock(root_clock), now, release_time)

        for i, input_arc_key in enumerate(graph.input_arc_dict().keys()):
            arc = graph.input_arc_dict().get(input_arc_key)
            input_val = input_vals[i]

            base_tag = Tag.TTTag(context='u1')
            base_token = Token.TTToken(input_val, base_time, tag=base_tag)

            for dest in arc.destSQList:
                port_numbers = dest.port_number_of_input_symbol(arc.symbol)
                for port_number in port_numbers:
                    token_to_send = base_token.copy_token()
                    token_to_send.tag.sq = dest.sq_name
                    token_to_send.tag.p = port_number
                    token_to_send.tag.e = ensemble.name
                    token_input_IPC_message = IPCMessage(IPCMessageTypeSync.TimedInput, token_to_send, IPCMessageProcessRecipient.ProcessInputTokens)
                    # ensemble.input_token_queue.put(token_input_IPC_message)
                    token_input_network_message = Network.TTNetworkMessage(token_input_IPC_message, ensemble.name)

                    ensemble.network_manager_queue.put(token_input_network_message)
        



def create_processes_physical(ip='127.0.0.1', rx_port=NetworkInterfaceUDP.RX_PORT, tx_port=NetworkInterfaceUDP.TX_PORT): #8425: TICK on 10-digit keypad

    logger.log(15, 'Start physical processes test')

    ens = Ensemble.TTEnsemble(name='physical-ensemble')
    ens.setup_queues(is_sim=False)
    ens.setup_physical_processes(network_ip=ip, rx_network_port=rx_port, tx_network_port=tx_port)

    # add any runtime inputs/messages
    # inject_messages(ens, is_sim=False)
    inject_messages_quadratic_program(ens, sim=False)

    logger.log(15, 'processes started; enter steady state')
    ens.enter_steady_state()
    logger.log(15, 'End physical processes test')


def create_processes_simulated():
    logger.log(15, 'Start simulated processes test')

    sim = simpy.Environment()

    ens = Ensemble.TTEnsemble(name='simulated-ensemble')
    ens.setup_queues(is_sim=True)

    ens.setup_simulation_processes(sim)
    ens.enter_steady_state()

    # add any runtime inputs/messages
    # inject_messages(ens, is_sim=True)
    inject_messages_quadratic_program(ens, sim=sim, include_timed_messages=True)


    sim.run()

    logger.log(15, 'End simulated processes test')
    

def main():
    DebugLogger.set_base_logger_level(logging.DEBUG)


    ###Physical
    try:
        create_processes_physical()
        pass    
    except KeyboardInterrupt:
        print('KB interrupt; exit physical test')
    except BaseException as e:
        traceback.print_exc()
        raise

    print("\n\n\nFinish physical test\n\n\nStart Simulated\n")

    ###Simulated
    try:
        create_processes_simulated()
        pass
    except (KeyboardInterrupt) as e:
        logger.warning('KB interrupt; exit simulated test')
    except BaseException as e:
        traceback.print_exc()
        pass

    logger.critical('\n\n\n****Ensemble Process Tests Done****\n')

if __name__ == '__main__':
    main()