# Copyright 2021 Carnegie Mellon University
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
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
logger = DebugLogger.get_logger('tests.ens_query')

def quadratic_test(a=-1, b=0, c=1):
    DebugLogger.set_base_logger_level(logging.DEBUG)
    TTCompile('quadratic', False, True)
    #load pickle
    inpickle = open('./output/quadratic.pickle', 'rb')
    graph = pickle.load(inpickle)

    ens1 = Ensemble.TTEnsemble(name='ens1')
    ens2 = Ensemble.TTEnsemble(name='ens2')
    ensemble_set = [ens1, ens2]

    return 0


def quadratic_ens_test(a=-1, b=0, c=1):
    DebugLogger.set_base_logger_level(logging.DEBUG)
    TTCompile('quadratic_ens', True, True)
    #load pickle
    inpickle = open('./output/quadratic_ens.pickle', 'rb')
    graph = pickle.load(inpickle)

    ens1 = Ensemble.TTEnsemble(name='ens1')
    ens1.addComponents(Component.TTComponent('waterHeight'))
    ens2 = Ensemble.TTEnsemble(name='ens2')
    ens2.addComponents(Component.TTComponent('mic'))
    ensemble_set = [ens1, ens2]

    mapping = Mapper.simple_static_mapping(graph, ensemble_set)
    logger.info(mapping)
    # mapping2 = Mapper.TTMapper.trivial_mapping(graph, ens1)
    # logger.info(mapping2)

    return 0


def graph_sim_merge_simple_streams(do_plot=False):
    DebugLogger.set_base_logger_level(logging.ERROR)

    TTCompile('merge_simple_streams', False, True)
    inpickle = open('./output/merge_simple_streams.pickle', 'rb')
    graph = pickle.load(inpickle)

    ens1 = Ensemble.TTEnsemble(name='ens1')
    ens2 = Ensemble.TTEnsemble(name='ens2')
    ensemble_set = [ens1, ens2]

    graph_sim = TTGraphSimulator(graph, ensemble_set)

    try:
        import time
        # t1 = time.time()
        graph_sim.start_sim(timeout=1002, trigger=1)
        # print(time.time()-t1)
    except KeyboardInterrupt:
        logger.info('Exited simulation due to keyboard interrupt. Show output')
    except BaseException as e:
        logger.error(traceback.format_exc())
        raise e


    # key = list(graph.output_arc_dict().keys())[0]
    # print(key)
    output_tokens = graph_sim.outputs['output']
    # pprint(output_tokens)
    output_times = list(map(lambda x: x.time, output_tokens))
    output_timestamps = np.asarray(list(map(lambda x: x.start_tick, output_times)))
    sorted_ind = np.argsort(output_timestamps)
    output_values = np.asarray(list(map(lambda x: x.value, output_tokens)))

    # output_timestamps = output_timestamps[sorted_ind] # TODO: remove this; it's just for checking. Order should be preserved in the production of a stream
    # output_values = output_values[sorted_ind] #TODO: remove this; it's just for checking. Order should be preserved in stream production (and processing?)

    truth_timestamps = list(range(0,100))
    import math
    truth_values = list([math.sin(math.pi*t/10) + math.sin(math.pi*t/20) for t in truth_timestamps])
    # truth_values = list([math.sin(math.pi*t/10) for t in truth_timestamps])
    assert truth_timestamps == list(output_timestamps) and truth_values == list(output_values)

    if do_plot:

        sorted_ind = np.argsort(output_timestamps)


        output_values = np.asarray(list(map(lambda x: x.value, output_tokens)))

        plt.figure()
        # plt.plot(output_timestamps[sorted_ind], output_values[sorted_ind])
        plt.plot(output_timestamps, output_values)
        # plt.title('sin(2*pi*f/20)+sin(2*pi*f/40) --- No Resampling, resorted by timestamp')
        plt.xlabel('Amplitude')
        plt.ylabel('Time (root domain)')
        plt.show()

    return output_tokens


def all_tests():
    quadratic_ens_test()

    print('\n Finished')

if __name__ == "__main__":
    all_tests()
