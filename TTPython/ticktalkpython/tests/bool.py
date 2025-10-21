import pickle
import os, sys, math, traceback
from pprint import pprint
from matplotlib import pyplot as plt
import numpy as np

#who knows where you may run this from. Don't name files identically..
# this only works from the top level of the repo
sys.path.insert(0, os.path.abspath('./tt/'))
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))

from Graph import *
from SQ import *
from SQSync import *
from Token import TTToken
from Tag import *
from Clock import *

import Ensemble
import Component
import Mapper

from Compiler import TTCompile
import DebugLogger, logging
logger = DebugLogger.get_logger('tests.ifelse')

import simpy
import RuntimeManager

def ifelse_sim():
    pass

def ifelse_compile():
    DebugLogger.set_base_logger_level(logging.DEBUG)
    graph = TTCompile('ifelse', True, True, True, use_graphviz=True)

def ifelse_test():
    ifelse_compile()

    return 0

def stream_deadline_compile():
    DebugLogger.set_base_logger_level(logging.DEBUG)
    graph = TTCompile('proposed_deadline_syntax', True, True, True, use_graphviz=True)

def stream_deadline_test():
    stream_deadline_compile()
    return 0

def all_tests():
    # ifelse_test()
    stream_deadline_test()

    print('\n Finished')

if __name__ == "__main__":
    all_tests()
