import sys, os, traceback, pickle, time, datetime, random
import simpy
import threading


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



def run_application_client(self_ip, self_port, rtm_ip, rtm_port):

    rtm_address = rtm_ip+":"+str(rtm_port)

    ens1 = Ensemble.TTEnsemble('ens'+str(random.randint(0, 10)))
    ens1.setup_queues(is_sim=False)
    ens1.setup_physical_processes(network_ip=self_ip, rx_network_port = self_port, tx_network_port = self_port+1)
    ens1.connect_to_TickTalk_network(rtm_address)

    ens1.enter_steady_state(timeout=90)


def port_and_ip(string):
    ip = string.trim().split(':')[0]
    port = int(string.trim().split(':')[1])

    return ip, port

if __name__ == "__main__":
    argc = len(sys.argv)
    self_ip, self_port, rtm_ip, rtm_port = None, None, None, None
    if argc == 3:
        self_ip, self_port = port_and_ip(sys.argv[1])
        rtm_ip, rtm_port = port_and_ip(sys.argv[2])
    elif argc == 5:
        self_ip = sys.argv[1]
        self_port = int(sys.argv[2])
        rtm_ip = sys.argv[3]
        rtm_port = int(sys.argv[4])
    else:
        raise ValueError('gonna need that ip and port (for self and runtime manager) as CLI args, dawg.')

    input('\n\n\nHit enter to start test\n\n')

    run_application_client(self_ip, self_port, rtm_ip, rtm_port)