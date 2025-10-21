# Copyright 2021 Carnegie Mellon University
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# Created by Bob Iannucci 2021
#

'''
The TTPython Graph Compiler takes a TTPython source file, reads it, creates an abstract syntax tree, walks the tree, and translates it into a TTPython graph.  Here's the compilation process, in a nutshell:

* Read the file
* Find all ``@SQify``-ed functions (and any others with valid TTPython decorators), including those that might be found via ``import``. :ref:`Instructions.py<instructions>` contains several examples.
* Build a table of them, indexed by their name, and attach to each the function body
* Find the ``@GRAPHify``-ed function
* Extract and record the arguments as graph inputs
* Walk the abstract syntax tree of the body, translating function calls into ``SQ`` instances and interconnect these with ``TTArc`` instances to represent the flow of values from ``SQ`` outputs to ``SQ`` inputs. There will be one ``TTArc`` instance per ``SQ`` output, and the ``TTArc`` will record the ``SQ`` instances to which it delivers values (fan-out). 
* Once complete, write out a representation of the graph (``SQ`` instances and ``TTArc`` instances)
'''

import ast
from pprint import pprint
import astor   # be sure to pip install this...
import ast_scope

import networkx as nx
## added by Mohammad
from networkx.drawing.nx_agraph import write_dot
import graphviz
##

import matplotlib.pyplot as plt
from CompilerRules import *
from SQ import TTSQContext, TTSQ
from Error import *
from Graph import *
from functools import reduce
from sys import exit
import json
import pickle

import DebugLogger
logger = DebugLogger.get_logger('Compiler')

# A useful tool:  https://python-ast-explorer.com

def add_topological_label(graph, node):
    # print(f"Node {node} is at level {graph.nodes[node]['level']}")
    if graph.nodes[node]['level'] != -1:
        return graph.nodes[node]['level']
    else:
        max_predecessor_level = -1
        for predecessor in graph.predecessors(node):
            predecessor_level = add_topological_label(graph, predecessor)
            max_predecessor_level = max(max_predecessor_level, predecessor_level)

        my_level = max_predecessor_level + 1

        # predecessors = graph.predecessors(node)
        # print(f"Predecessors of {node} are {predecessors}")
        # predecessor_levels = map(lambda x: add_topological_label(graph, x), predecessors)
        # if len(predecessor_levels) == 0:
        #     my_level = 1
        # else:
        #     my_level = 1 + reduce(max, predecessor_levels)

        # print(f"Setting level to {my_level}")
        graph.nodes[node]['level'] = my_level
        return my_level

def add_topological_labels(graph, node_list):
    for node in node_list:
        add_topological_label(graph, node)


## Added by Mohammad
def draw(file='./output/graph.dot'):
    # For drawing to work, you need pygraphviz and graphviz installed. This is not always easy. See documentation here:https://pygraphviz.github.io/documentation/stable/install.html

    # This function is called when the use_graphviz option is called for the compiler
    #TODO: make this color different types of SQs differntly. It is not immediatley clear how to do so, but it could be feasible to embed some self-identifing strings into some of the graph nodes, and use that to set the fillcolor
    A = graphviz.Source.from_file(file, format='pdf', engine='dot')
    src = A.source
    ## add LR
    res = src.find('rankdir=LR;')
    if res == -1:
        B, C = src.split("{")
        D = B + "{\n \trankdir=LR;\n" + C
        A.source = D

    ## add same rank
    res = src.find("rank=same")
    if res == -1:
        i = 0
        ranks = []
        names = []
        src = A.source
        for lines in src.splitlines():
            if not lines.find('level') == -1:
                s1, s2 = lines.split("[level=")
                s3, s4 = s2.split("];")
                ranks.append(int(s3))
                names.append(s1)
        N = max(ranks)

        all = ""
        for i in range(N):
            same = "rank=same"
            for j in range(len(ranks)):
                if ranks[j] == i:
                    same = same + str("; ") + str(names[j])
            all = all + "{" + same + ";}\n"
        s1, s2 = src.split("}")
        src = s1 + all + "}" + s2

    ##color
    res = src.find("green")
    if res == -1:
        for i in range(N+1):
            s1 = "level=" + str(i)
            s2 = "level=" + str(i) + ", fillcolor = red, style=filled"
            s3 = "level=" + str(i) + ", fillcolor = red, style=filled"
            s4 = "level=" + str(i) + ", fillcolor = green, style=filled"
            if i == 0:
                src = src.replace(s1, s2)
            elif i == N:
                src = src.replace(s1, s3)
            elif True:
                src = src.replace(s1, s4)
    A.source = src
    A.view()
##


def graphit(ttgraph,use_graphviz=False):
    # Create and display the TTGraph 
    graph_input_nodes = []
    graph_output_nodes = []
    graph_internal_nodes = []
    graph = nx.DiGraph()
    graph.add_nodes_from(ttgraph.sqList, level=-1)
    graph_edge_label_dict = {}

    # Every arc in the symbol table should either have
    #   a source and at least one destination:  normal SQ
    #   a source but no destination:            graph output
    #   a destination but no source:            graph input
    for i, (symbol, arc) in enumerate(ttgraph.symbolTable.items()):
        sourceSQ = arc.sourceSQ
        if sourceSQ and arc.destSQList != []:
            graph_internal_nodes.append(sourceSQ)
            # Draw inter-SQ links
            for destSQ in arc.destSQList:
                graph.add_edge(sourceSQ, destSQ)
                graph_edge_label_dict[(sourceSQ, destSQ)] = arc.symbol
        elif arc.destSQList != []:
            # Create virtual source nodes for graph inputs as additional nodes
            graph_input_nodes.append(symbol)
            graph.add_node(symbol, level=0)
            for destSQ in arc.destSQList:
                graph.add_edge(symbol, destSQ)
                graph_edge_label_dict[(symbol, destSQ)] = symbol
        elif sourceSQ:
            # Create virtual sink node
            graph_output_nodes.append(symbol)
            graph.add_node(symbol, level=-1)  # **Temporary** -- need to topologically sort the graph
            graph.add_edge(sourceSQ, symbol)
            graph_edge_label_dict[(sourceSQ, symbol)] = symbol
        else:
            raise Exception("TopologicalError", f"Found an arc for symbol {symbol} that has neither source nor sink")

    # Colorize the graph: inputs and outputs are different from internal nodes
    color_map = []
    for node in graph:
        if isinstance(node, TTSQ):
            if node.is_streaming:
                color_map.append('lightblue')
            else:
                color_map.append('green')
        else:
            color_map.append('red')

    plt.figure(figsize=(20, 10))
    plt.subplot(111)

    add_topological_labels(graph, graph_internal_nodes)
    add_topological_labels(graph, graph_output_nodes)
    pos = nx.multipartite_layout(graph, subset_key='level')
    ## added by Mohammad
    if use_graphviz:
        write_dot(graph, "./output/graph.dot")
        draw()
    ##
    nx.draw(graph, pos, node_color=color_map, with_labels=True, node_size=2000, connectionstyle="arc3,rad=0.2")
    #nx.draw(graph, pos, node_color=color_map, with_labels=True, node_size=2000)
    nx.draw_networkx_edge_labels(graph,pos,edge_labels=graph_edge_label_dict)


def TTCompile(filename, inpath="./examples/", outpath="./output/", printAST=True, showGraph=True, writeJSON=False, writePickle=True, use_graphviz=False):
    '''
    Read a TTPython file and convert it to a ``TTGraph`` . Save the graph in one or several output formats.

    :param filename: the compilation name ({filename}.py TTPython source and {filename}.json/name.pickle graph)
    :param inpath: the folder location of the TTPython source file
    :param outpath: the folder location to dump the graph
    :type clock: string
    :param printAST: *True* to print out the abstract syntax tree during compilation (debug usage)
    :type printAST: bool
    :param showGraph: *True* to print a simple depiction of the compiled graph.  The graph will be topologically sorted left-to-right.  Inputs and outpus will be shown in red.  Internal SQ instances will be shown in green.  Arcs will be labeled with their symbol. Defaults to True
    :type showGraph: bool
    :param writeJSON: @deprecated. *True* writes a representation of the graph in JSON format in the same directory as the source file with the name ``<source>.json``. Defaults to False
    :type writeJSON: bool
    :param writePickle: *True* writes a representation of the graph in Pickle format in the same directory as the source file with the name ``<source>.pickle``. Defaults to
    :type writePickle: bool

    :return: Return the compiled graph
    :rtype: TTGraph
    '''


    # pathname = f"/Users/bob/Documents/bitbucket/ticktalkpython/{filename}.py"
    inpath = f"{inpath}{filename}.py"
    picklepath = f"{outpath}{filename}.pickle"
    outpath = f"{outpath}{filename}.json"
    with open(inpath, "r") as source:
        module = ast.parse(source.read())

    with open(inpath, "r") as source:
        source_list = source.readlines()

    # Displays the AST body
    if printAST:
        logger.info(astor.dump_tree(module))
        logger.info('')

    # Initialize the graph data structure
    graph = TTGraph()

    # Import the core BinOp library
    import_sqified_functions_from_module('tt.Instructions', graph)
    try:
        # TTGraph holds the state of the translation
        compileVisitor = TTGraphCompilationVisitor(graph, debug=True, source=source_list, pathname=inpath)
        compileVisitor.visit(module)
        graph.set_flattened_constraints(compileVisitor.flattened_constraints)

        logger.info(f"Compilation successful")

        if writePickle:
            logger.info(f"Writing {picklepath}")
            with open(picklepath, 'wb') as pickle_out:
                pickle.dump(graph, pickle_out)

        # If we did not error out, TTGraph contains the compiled graph.
        # Write it out as JSON:
        if writeJSON:
            logger.warning("WRITING JSON MAY FAIL DESPITE SUCCESSFUL COMPILATION!! \n\tThis is because we save keyword arguments directly within SQs, which may contain objects that lack a JSON serialization format")
            logger.info(f"Writing {outpath}")
            with open(outpath, "w") as json_out:
                json.dump(graph.json(), json_out, indent=4)

        # For fun and sanity checking, display it graphically
        if showGraph:
            graphit(graph, use_graphviz=use_graphviz)

    except TTSyntaxError as error:
        logger.error(repr(error))

    return graph
