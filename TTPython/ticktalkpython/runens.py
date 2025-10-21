#!/usr/bin/python

import logging, pickle, random, simpy, sys, time, traceback
import argparse

sys.path.append('tt/')
import Ensemble
import Graph
from IPC import *


def run_application_client(name, self_ip, self_port, rtm_ip, rtm_port,
                           timeout):

    rtm_address = rtm_ip + ":" + str(rtm_port)

    ens1 = Ensemble.TTEnsemble(name)
    ens1.setup_queues(is_sim=False)
    ens1.setup_physical_processes(network_ip=self_ip,
                                  rx_network_port=self_port,
                                  tx_network_port=self_port + 1)
    ens1.connect_to_TickTalk_network(rtm_address)

    ens1.enter_steady_state(timeout=timeout)


def main():
    parser = argparse.ArgumentParser(
        description='instantiate an ensemble for a TTPython program')

    parser.add_argument('name', help="the name of the ensemble")
    parser.add_argument(
        '--ip',
        default='127.0.0.1',
        help='the ip of the ensemble (default: localhost:127.0.0.1)')
    parser.add_argument('--rtm_ip',
                        default='127.0.0.1',
                        help=("the runtime manager's ip to connect to"
                              " (default: localhost:127.0.0.1)"))
    parser.add_argument(
        'port',
        type=int,
        help='the port of the ensemble. reserves both the port number p and p+1'
    )
    parser.add_argument('--rtm_port',
                        type=int,
                        required=True,
                        help='the port of the runtime manager')
    parser.add_argument('--timeout',
                        default=60,
                        type=int,
                        help='ensemble timeout (default: 60 (sec))')

    args = parser.parse_args()
    name = args.name
    ip = args.ip
    port = args.port
    rtm_ip = args.rtm_ip
    rtm_port = args.rtm_port
    timeout = args.timeout

    input('\n\n\nHit enter to start test\n\n')
    run_application_client(name, ip, port, rtm_ip, rtm_port, timeout)


if __name__ == '__main__':
    main()
