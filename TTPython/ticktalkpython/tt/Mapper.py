# Copyright 2021 Carnegie Mellon University
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

'''
Mapping relates the graph of SQs to the physical system: SQs are assigned to ensembles and told where their outputs should be sent. Mapping is done after compilation and before graph interpretation/execution.

Mapping is done based for a known network of ensembles. There may be constraints on mapping from the graph itself, and it is the Mapper's responsibility to satisfy these constraints. These constraints may restrict SQs to only run on specific Ensembles (or types of Ensembles) or may specify some multi-SQ constraints like an upper bound on latency.

Within the runtime environment, the mapping should be done using either a static system description or a runtime-generated description provided by the runtime manager (RTM). The RTM should handle mapping as part of the graph instantiation process before it kicks off interpretation by injecting initial input tokens.
'''

from typing import Union

import Arc
import Graph
import Ensemble
import DebugLogger
import random
import Query
logger = DebugLogger.get_logger('Mapper')

def simple_static_mapping(graph, ensembles):
    '''
    Given that the graph has SQs with annotated constraints (from TTQuery
        within the program), the mapping returned will ensure that
        mapped SQs have a corresponding compatible ensemble

    :param graph: The graph to map entirely onto a singular ensemble
    :type graph: TTGraph
    :param ensembles: The ensembles to map the entire graph onto
    :type ensembles: [TTEnsemble]

    :return: A dictionary using SQ names as keys and ensemble names as values,
        to represent which SQ the ensemble is mapped onto. This is used to
        instantiate all the SQs on their correponding ensemble. An SQ is
        uniquely named and uniquely mapped to one ensemble.
    :rtype: dict
    '''
    static_map = {}

    for sq in graph.sqList:
        print(sq.constraints)
        filtered_ens = [
            ens.name for ens in ensembles if len(sq.constraints) == 0
            or Query.TTQuery(sq.constraints, Query.QueryOp.AND).test(ens)
        ]
        # TODO: pick one through heuristics instead of the first one
        static_map[sq.sq_name] = filtered_ens[0]

    return static_map

# stateful function, overwrties arc destination mappings
def assign_mapping(graph: Graph.TTGraph, mapping):
    '''
    Updates the arcs in the given graph with the provided mapping

    :param graph: The graph to map entirely onto a singular ensemble
    :type graph: TTGraph
    :param mapping: The ensemble to map the entire graph onto
    :type mapping: TTEnsemble

    :return: list of TTArcDestinations
    :rtype: list
    '''
    for arc in graph.symbolTable.values():
        for dest_sq in arc.destSQList:
            for pn in dest_sq.port_number_of_input_symbol(arc.symbol):
                arc_destination = Arc.TTArcDestination(
                    mapping[dest_sq.sq_name], dest_sq.sq_name, pn)
                arc.destMapping.append(arc_destination)
                logger.debug(
                    f"Adding arc_destination {arc_destination} to"
                    " intermediate-arc symbol {arc.symbol}"
                )

    return mapping

class TTMapper():
    '''
    The TTMapper handles mapping based on a system description (a set of ensembles) and a graph. The exact format of the system description is subject to change, and will likely become more complex as mapping algorithms become more sophisticated

    :param graph: The compiled graph representing a TTPython program, which is ready to be mapped to the set of ensembles
    :type graph: TTGraph
    :param ensembles: A set of ensembles composing the system; this is the system description
    :type ensembles: list(TTEnsembles)
    '''

    def __init__(self, graph: Graph.TTGraph, ensembles=[]):

        self.graph = graph
        self.ensembles = ensembles #This should be expanded into a more complete system description. At least contain information about what ensembles contain and their networking interface. It probably does not need to include a full network model, as this is challenging (if not impossible) to accurately produce

    @staticmethod
    def trivial_mapping(graph, ensemble):
        '''
        Trivial mapping puts all SQs onto the same ensemble. It is the simplest form of mapping, and is useful for testing basic elements of the graph interpretation and/or code execution. Most of the work here is setting the arc destinations so that we know how to tag output tokens.

        :param graph: The graph to map entirely onto a singular ensemble
        :type graph: TTGraph
        :param ensemble: The ensemble to map the entire graph onto
        :type ensemble: TTEnsemble

        :return: A dictionary using SQ names as keys and ensemble names as values, to represent which SQ the ensemble is mapped onto. This is used to instantiate all the SQs on their correponding ensemble. An SQ is uniquely named and uniquely mapped to one ensemble.
        :rtype: dict

        '''
        mapped_graph = {}

        if isinstance(ensemble, Ensemble.TTEnsemble):
            ensemble_name = ensemble.name
        elif isinstance(ensemble, dict):
            ensemble_name = ensemble['name']

        # Setup destination mappings for the input arcs
        input_arc_dict = graph.input_arc_dict()
        for input_symbol in input_arc_dict:
            input_arc = input_arc_dict[input_symbol]

            for dest_sq in input_arc.destSQList:
                port_number = dest_sq.port_number_of_input_symbol(input_arc.symbol)
                for pn in port_number:
                    arc_destination = Arc.TTArcDestination(ensemble_name, dest_sq.sq_name, pn)
                    # if not arc_destination in input_arc.destMapping:
                    #     logger.debug('Adding arc_destination %s to input-arc symbol %s' % (arc_destination, input_arc.symbol))
                    #     input_arc.destMapping.append(arc_destination)
                    logger.debug(
                        'Adding arc_destination %s to input-arc symbol %s' % (arc_destination, input_arc.symbol))
                    input_arc.destMapping.append(arc_destination)

        for sq in graph.sqList:
            #for each arc, search for the set of destinations, and create a ``TTArcDestination``
            ## must deference the symbol name to a port number
            #Assume there is only one output arc per SQ
            for output_arc in sq.output_arcs:
                for dest_sq in output_arc.destSQList:
                    port_number = dest_sq.port_number_of_input_symbol(output_arc.symbol)
                    for pn in port_number:
                        # possibly mulitple instances of the same symbol at the same SQ!
                        arc_destination = Arc.TTArcDestination(ensemble_name, dest_sq.sq_name, pn)
                        if not arc_destination in output_arc.destMapping:
                            logger.debug('Adding arc_destination %s to intermediate-arc symbol %s' % (arc_destination, output_arc.symbol))
                            output_arc.destMapping.append(arc_destination)

            # ensemble.instantiate_sq(sq) #don't instantiate let; the network should initiate this
            mapped_graph[sq.sq_name] =  ensemble_name


        return mapped_graph

    @staticmethod
    def random_mapping(graph: Graph.TTGraph, ensembles: Union[dict, list]):
        '''
        Produce a random mapping of the graph onto the ensembles

        :param graph: The graph to map
        :type graph: TTGraph
        :param ensembles: The set of ensembles to map the graph onto; this
            is the system description
        :type ensemblese: list(TTEnsemble) | dict

        '''
        # Assumes all sqs have at least one input arc
        graph_levels = {0:[]}
        graph_node_to_levels = {}
        up_to_down = {}
        down_to_up = {} # keys: sq.sq_name for sq in graph.sqList
        mapping = {}


        # I'll be honest, this is way too complex for a 'random' mapping. Just generate a random number and use that to index among ensembles. No clue what the levels are doing here. This is meant to be an easy way to test a graph on a network of ensembles, without worrying about the exact composition. The data structures are overspecified. -Reese
        for arc in graph.symbolTable.values(): # arcs
            sourceSQ = arc.sourceSQ
            if not sourceSQ and len(arc.destSQList)>0:
                #if this is an input arc...
                graph_levels[0].append(arc.symbol)
                graph_node_to_levels[arc.symbol] = 0
                up_to_down[arc.symbol] = [sq.sq_name for sq in arc.destSQList] #fill entry in dict of which destinations (using sq names) receive from this arc
                for sq in arc.destSQList:
                    if sq.sq_name not in down_to_up:
                        down_to_up[sq.sq_name] = []
                    down_to_up[sq.sq_name].append(arc.symbol) # add information about SQ source to this dictionary
            elif len(arc.destSQList)>0:
                #if this is not an input arc, but also not an ouput arc... it is intermediate.
                up_to_down[sourceSQ.sq_name] = [sq.sq_name for sq in arc.destSQList]
                for sq in arc.destSQList:
                    if sq.sq_name not in down_to_up:
                        down_to_up[sq.sq_name] = []
                    down_to_up[sq.sq_name].append(sourceSQ.sq_name)
            elif not sourceSQ and len(arc.destSQList)==0:
                raise Exception("TopologicalError")

        def helper(node):
            #what's the purpose of this?
            # Seems top be for organizing the 'levels' of the graph, which seems to pertain to a 'distance' from the input arcs
            if node in graph_node_to_levels:
                return graph_node_to_levels[node]

            level = max([helper(n) for n in down_to_up[node]])+1
            graph_node_to_levels[node] = level
            if level not in graph_levels:
                graph_levels[level] = []
            graph_levels[level].append(node)
            return level

        for sq in down_to_up:
            if sq not in graph_node_to_levels:
                helper(sq)

        def random_ensemble_selector(ensembles):
            #help gloss over the difference between list and dictionary of ensembles. just select a random device
            index = random.randrange(0,len(ensembles))
            if isinstance(ensembles, dict):

                ens =  ensembles[list(ensembles.keys())[index]]
            else:
                ens =  ensembles[index]

            if isinstance(ens, Ensemble.TTEnsemble):
                ensemble_name = ens.name
            elif isinstance(ens, dict):
                ensemble_name = ens['name'] #ensembles are dictionaries? Part of an alternate specification of ensembles?

            return ensemble_name

        sq_names = [sq.sq_name for sq in graph.sqList]
        # Do the actual mapping of SQs to ensembles; the mapping is a dictionary based on the sq name (key) and ensemble name (value)
        ## This is more complex than necessary; seems to
        for level in sorted(graph_levels.keys()):
            if level > 0:
                for sq in graph_levels[level]:
                    assert sq in sq_names
                    if level == 1:
                        mapping[sq] = random_ensemble_selector(ensembles)
                    else:
                        upstreams = set(down_to_up[sq]) - set(graph_levels[0])
                        sources = set([mapping[node] for node in upstreams]) #ensembles that have a source SQ of an input arc maeed to them
                        if random.random() < 0.6: #with 60% chance, map the SQ to an ensemble that already has a source SQ (randomly among them)
                            mapping[sq] = random.choice(tuple(sources))
                        else:
                            mapping[sq] = random_ensemble_selector(ensembles)

        #Build out the set of arc destination so SQs know where to send their outputs. This assumes decentralized routing. pub-sub is an alternative, and doesn't require routing tables be propagated about the network.
        for arc in graph.symbolTable.values():
            for dest_sq in arc.destSQList:
                for pn in dest_sq.port_number_of_input_symbol(arc.symbol):
                    arc_destination = Arc.TTArcDestination(mapping[dest_sq.sq_name], dest_sq.sq_name, pn)
                    arc.destMapping.append(arc_destination)
                    logger.debug('Adding arc_destination %s to intermediate-arc symbol %s' % (arc_destination, arc.symbol))

        logger.debug(mapping)

        return mapping
