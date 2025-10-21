import pickle
import os, sys, math, traceback
from pprint import pprint
from matplotlib import pyplot as plt
import numpy as np

#who knows where you may run this from. Don't name files identically..
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
import matplotlib.pyplot as plt
import DebugLogger, logging
logger = DebugLogger.get_logger('tests.deadline')

def deadline_test():
    DebugLogger.set_base_logger_level(logging.DEBUG)
    TTCompile('proposed_deadline_syntax', True, True)
    #load pickle
    inpickle = open('./output/deadline.pickle', 'rb')
    graph = pickle.load(inpickle)

    # ens1 = Ensemble.TTEnsemble(name='ens1')
    # ens1.addComponents(Component.TTComponent('waterHeight'))
    # ens2 = Ensemble.TTEnsemble(name='ens2')
    # ens2.addComponents(Component.TTComponent('mic'))
    # ensemble_set = [ens1, ens2]

    # mapping = Mapper.static_mapping(graph, ensemble_set)
    # logger.info(mapping)
    return 0

def all_tests():
    deadline_test()

    print('\n Finished')

if __name__ == "__main__":
    all_tests()
