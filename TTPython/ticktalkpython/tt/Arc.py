# Copyright 2021 Carnegie Mellon University
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

'''
Arcs describe the connections between SQs within the graph. Arc destinations are a runtime version of an Arc that tells an SQ where it must send its output; a list of these sufficiently describes the *Forwarding* section of an SQ. 

Arcs are generated within the compiler, and are often generated for variables that are assigned values by the output of an expression or function call. Some Arcs are auto-generated when there are multiple simply expressions on the same line. 
'''

import DebugLogger
logger = DebugLogger.get_logger('Arc')

class TTArcDestination():
    '''
    TTArcDestinations carry all the necessary information to generate tags that 
    represent the location a token must be sent to. This information should be 
    filled in when mapping the program to a set of ensembles. An arc's mapping 
    may contain multiple TTArcDestinations, one per port of an SQ that needs to receive a 
    token from the arc this is attached to.

    :param ensemble_name: Name of an ensemble that hosts the recipient SQ
    :type ensemble_name: String
    :param sq_name: Name of the SQ to send output tokens to
    :type sq_name: String
    :param port_number: Index (from 0) of the port with the named SQ the token must be sent to
    :type port_number: int
    '''

    def __init__(self, ensemble_name, sq_name, port_number):

        self.ensemble_name = ensemble_name
        self.sq_name = sq_name
        self.port_number = port_number

    def __repr__(self):
        return f"<TTArcDestination Ens={self.ensemble_name}; SQ-name={self.sq_name}; Port={self.port_number}>"

    def __eq__(self, arc_dest):
        
        return (self.ensemble_name == arc_dest.ensemble_name) and (self.sq_name == arc_dest.sq_name) and (self.port_number == arc_dest.port_number)

class TTArc():
    '''
    TTArcs connect SQs.  Each ``TTArc`` has zero or one source ``TTSQ`` and as
    many destination SQs as needed.  Each can also be associated with
    a program symbol which only serves as a documentation string.

    :param sourceSQ: The SQ that will send its outputs ( ``TTToken`` ) along this arc
    :type sourceSQ: TTSQ
    :param symbol: A symbol name derived from the compiler; generally a variable name
    :type symbol: string
    '''
    def __init__(self, sourceSQ, symbol):   # symbol derives from the scope-disambiguated symbol in the program
        self.sourceSQ = sourceSQ
        self.destSQList = [] #set as a result of compilation
        self.symbol = symbol # must dereference this into a port number for the destination SQs at runtime during mapping
        self.destMapping = [] #set as a result of mapping

    def id(self):
        return id(self)

    def __repr__(self):
        return f"<TTArc {self.symbol} {self.id()}>"

    def add_destination(self, sq):
        '''
        Specify an additional destination SQ that will receive tokens from this arc

        :param sq: The SQ that will receive tokens from this arc at runtime
        :type sq: TTSQ
        '''
        self.destSQList.append(sq)

