# Copyright 2021 Carnegie Mellon University
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# Created by Bob Iannucci 2021
#

'''
SQs are the core of TTPython programs -- they are the nodes of the dataflow
graph that encodes the application.

SQs contain a Synchronization (``TTSQSync``), Execution (``TTSQExecute``) and
Forwarding/Tagging (based on mapping and ``TTTag``/``TTTime``) portions, hence
the organization of the runtime environment into three processes that
correspond to each part of the SQ.

SQs are built from ordinary python functions with a decorator
(e.g. ``SQify`` or ``STREAMify``), which encapsulate the user-level function
into a form that handles the boilerplate SQ operations. These functions compose
the body of an SQ (i.e., Execution), and are executed when a firing rule
(``TTFiringRule``) is satisifed by the input value-carrying tokens and state
of internal clocks. This firing rule is a synchronization barrier, and is
ordinarily untouched by the user. In some cases, they may provide parameters
to the barrier for the function they are calling with the TTPython program
(which is itself a function with a ``GRAPHify`` decorator). This is primarily
used to dictate behaviors like periodic triggering for stream generation or
deadlines/timeouts on synchronization

SQs may also be made stateful (similar to 'static' variables in other languages)
by declaring 'global sq_state' in the SQify'd function. This variable is a
dictionary that will persist between invocations of the same SQ, but will not
affect any other SQs in the system. Such SQs are given special firing rule
mechanisms to enforce chronological processing of data
(though some iterations may be skipped)
'''
from copy import deepcopy
import pickle
from Token import TTToken
from Time import TTTime, TTTimeSpec
from Clock import TTClock, TTClockSpec
import SQSync, SQExecute
from enum import Enum
from Error import *
import astunparse, ast  # need to pip install this
from intervaltree import *
from functools import wraps

from inspect import signature

from FiringRule import TTFiringRule, TTFiringRuleType

import DebugLogger
logger = DebugLogger.get_logger('SQ')

# TTSQs are wrappers for functions implemented as Python function decorators.
#
# A TTSQ has three parts:
#
#    Trigger and metadata -- unpacking tokens to values
#    Body                 -- Executable function that takes token values as inputs
#    Epilog               -- Packaging of the returned value into a token with
#                            appropriate timestamp

# SQification is a function decorator that wraps a normal Python function by
#    Computing the overlap in time windows across all the arguments
#    If there is a non-empty overlap, it computes the function on the values
#    of the tokens and returns a new token with the value and the new time
# stamp representing the overlap of the input arguments

# Instructions (in TTInstructions.py) are the most simple of examples in which
# normal operations like add and subtract are realized with simple Python
# functions that operate on normal Python parameters, but SQification wraps
# these functions so that the inputs and outputs are timed tokens.

# SQified functions are COMPOSABLE in that the input to one should be the
# output of another (tokens-in, tokens-out)

class TTInterpreter(Enum):
    ''''''
    IoTA = 0
    Python3 = 1

class TTSQPattern(Enum):
    '''
    An enumeration for different types of SQs in terms of their input-output
    characteristics
    '''
    NInNOut = 0
    TriggerInNOut = 1
    NInZeroOut = 2 # is this necessary to describe? Is it actually a special case?


class TTSQContext():
    '''
    An SQ Context refers to contextual information that surrounds the SQ,
    similar to scoping in more traditional sequential programming languages.

    The mechanisms within the context are based on TTPython synxtax from 'with'
    constructs, which are used to specify clocks, backup (plan B)
    callbacks/handlers, deadlines, mapping constraints, etc. Multiple SQs may
    use the same context
    '''
    def __init__(self,
                 name="(no name)",
                 clockspec=None,
                 planB_handler=None,
                 deadline=None,
                 base_context=None,
                 constraints=[]):
        if base_context:
            self.name = base_context.name
            self.clockspec = base_context.clockspec
            self.planB_handler = base_context.planB_handler
            self.deadline = base_context.deadline
            self.constraints = base_context.constraints
        else:
            self.name = name
            self.clockspec = clockspec
            self.planB_handler = planB_handler
            self.deadline = deadline
            self.constraints = constraints # list(TTQCComponentName)

    def id(self):
        return id(self)

    def __repr__(self):
        return f"<TTSQContext {self.name} {self.id()}>"

    def json(self):
        j = {}
        j['name'] = self.name
        if self.clockspec:
            # print(f"Here is the clockspec: {self.clockspec}")
            j['clockspec'] = self.clockspec.json()
        if self.planB_handler:
            j['planB_handler'] = self.planB_handler.json()
        if self.deadline:
            j['deadline'] = self.deadline.json()
        return j


# Including runtime methods so that the graph interpreter can simply use this same
# class on un-pickled TTSQs
class TTSQ():
    '''
    The TTSQ is used to create a node in the graph during the compilation
    process by analyzing the input symbols (which are arcs in the graph), the
    abstract syntax tree (AST) for the GRAPHify'd TTPython function AND the
    SQify'd Python function (including keyword/optional arguments), and the
    surrounding context.

    The TTSQ is broken into two parts for synchronization and execution
    (Forwarding/tagging is a function of how the program is mapped). Part of
    this process involves parsing through keyword arguments in the AST's of
    the function definition and its usage in the graph; keywords beginning
    with 'TT' are often metasyntax for parameterizing firing rules or control
    mechanisms. Otherwise, any keyword arguments in the definition and function
    call are respected in the SQ at runtime
    (but must be constant valued parameters; **not** arcs!).

    :param astNode: The abstract syntax tree node (generally, a Call object)
        from the GRAPHify-cation
    :type astNode: ``ast.AST`` (may be one of several subtypes, like _ast.Call)
    :param functionASTnode: The abstract syntax tree node for the function
        decorated with SQify or STREAMify
    :type functionASTnode: ``ast.FunctionDef``
    :param context: The context surround the SQ
    :type context: TTSQContext
    :param sq_name: The name of the SQ; this should be unique within the graph.
        This is accomplished during compilation by appending a counter to the
        end of the function name
    :type sq_name: string
    :param input_arcs:  A list of input arcs that represent the symbols or
        variable defined in the graph
    :type input_arcs: list(TTArc)
    :param constraints: Contraints on the mapping of this SQ
    :type constraints: list(str)
    :param interpreter: An enumerated variable describing the environment that
        must be used to interpret the SQ's TTSQExecute portion. Currently,
        this only supports Python3
    :type interpreter: TTInterpreter
    :param firing_rule_type: A desgnator for the type of the firing rule,
        defaulting to 'Timed' (which looks for any amount of overlap in the
        time interval in the token ``TTTag``)
    :type firing_rule_type: TTFiringRuleType
    :param clock_dict: A dictionary of clocks defined in the graph, default
        to empty (``{}``)
    :type clock_dict: dict
    '''
    def __init__(self,
                 astNode,
                 functionASTnode,
                 context,
                 sq_name,
                 input_arcs,
                 constraints,
                 input_control_arc=None,
                 interpreter=TTInterpreter.Python3,
                 firing_rule_type=TTFiringRuleType.Timed,
                 clock_dict = {}):
        if astNode:
            #AST basics and input copying
            self.astNode = astNode
            self.functionASTnode = functionASTnode
            self.context = context
            self.function_name = astNode.func.id #the generic name of the SQified function
            self.function_source = astunparse.unparse(functionASTnode)
            self.sq_name = sq_name #specific to this instance of the SQ. Based on astNode.func.id + a distinct number
            self.constraints = constraints

            #output arcs will be filled in later, but we define them now
            self.output_arcs = []
            self.input_control_arc = input_control_arc
            self.output_control_arc = None #used for retriggering, sending deadlne notifications(?)

            #pattern defaults
            self.is_streaming = False
            self.pattern = TTSQPattern.NInNOut

            # streaming designation should propagate; check by tracing to the
            # input arc, assuming the graph is constructed s.t. every new SQ
            # receives input from SQs that have already been created
            # (and their arcs defined)
            for input_arc in input_arcs:
                input_arc.add_destination(self)
                if input_arc.sourceSQ != None and input_arc.sourceSQ.is_streaming:
                    self.is_streaming = True #streaming designation propagates

            # if this is decorated with 'STREAMify', then it should be expected
            # to retrigger itself periodically such that it generates a stream
            # of data. The parameters (e.g., period, phase) will be extracted
            # while analyzing keyword arguemnts
            if any([
                    decorator.id == 'STREAMify'
                    for decorator in self.functionASTnode.decorator_list
            ]):
                self.is_streaming = True
                self.pattern = TTSQPattern.TriggerInNOut
                if firing_rule_type != TTFiringRuleType.TimedRetrigger:
                    logger.warning(
                        'Firing rule type should have been timed retrigger for a STREAMify node; was %s. Resetting to timed retrigger'
                        % firing_rule_type)
                    firing_rule_type = TTFiringRuleType.TimedRetrigger

            # Must this run sequentially (chronologically)?
            self.run_sequentially = False
            if (("global sq_state" in self.function_source
                 or firing_rule_type == TTFiringRuleType.SequentialRetrigger)
                    and self.is_streaming
                    and self.pattern != TTSQPattern.TriggerInNOut):

                self.run_sequentially = True
                firing_rule_type = TTFiringRuleType.SequentialRetrigger

            if not firing_rule_type in TTFiringRuleType:
                raise Exception(
                    "SpecificationError",
                    f"Invalid firing rule {firing_rule_type} specified for {self.function_name} on line {self.astNode.lineno}"
                )
            self.firing_rule_type = firing_rule_type

            # analyze and setup arguments (keyword args, that is) for firing
            # rule (TTSQSync) and execution (TTSQExecute)
            self.firing_rule_kwargs = {}
            self.execution_kwargs ={}
            self.setup_args(astNode, functionASTnode, clock_dict=clock_dict)
            # self.setup_kwargs(astNode, firing_rule_type=self.firing_rule_type, clock_dict=clock_dict)

            # Configure synchronization portion
            self.set_input_arcs(input_arcs)
            self.firing_rule = TTFiringRule(
                firing_rule_type,
                self.firing_rule_kwargs,
                self.pattern,
                is_sequential=self.run_sequentially,
                use_deadline=False)
            # TODO: fix hack
            # * self.n_input_ports can actually be 1 if 0,
            # * but no triggerless functions are allowed
            self.sync = SQSync.TTSQSync(self.firing_rule,
                                        max(self.n_input_ports, 1),
                                        self,
                                        is_streaming=self.is_streaming,
                                        use_deadline=False)

            #setup the execution portion
            if not interpreter in TTInterpreter:
                raise Exception(
                    "SpecificationError",
                    f"Invalid interpreter {interpreter} specified for {self.function_name} on line {self.astNode.lineno}"
                )
            self.interpreter = interpreter
            self.execute = SQExecute.TTSQExecute(
                self.sq_name,
                interpreter,
                self.function_source,
                self.function_name,
                self.pattern,
                self.n_input_ports,
                execution_kwargs=self.execution_kwargs,
                is_sequential=self.run_sequentially)


        else:
            self.function_name = "(unknown)"


    def id(self):
        return id(self)

    def __repr__(self):
        return f"<SQ {self.sq_name} {id(self)}>"

    def __str__(self):
        return f"{self.sq_name}"

    def setup_args(self, astNode, functionAstNode, firing_ryle_type=TTFiringRuleType.Timed, clock_dict={}):
        '''
        Analyze the arguments in the function and graph, specifically the arguments with default values, as these are not arcs, but parameters (potentially meta-parameters for the TTPython runtime)

        :param astNode: The abstract syntax tree node (generally, a Call object) from the GRAPHify-cation
        :type astNode: ``ast.AST`` (may be one of several subtypes, like _ast.Call)
        :param functionASTnode: The abstract syntax tree node for the function decorated with SQify or STREAMify
        :type functionASTnode: ``ast.FunctionDef``
        :param firing_rule_type: A desgnator for the type of the firing rule, defaulting to 'Timed' (which looks for any amount of overlap in the time interval in the token ``TTTag``)
        :type firing_rule_type: TTFiringRuleType
        :param clock_dict: A dictionary of clocks defined in the graph, default to empty (``{}``)
        :type clock_dict: dict
        '''

        # some functions will have keywords arguments (identifed based on default values); these are not arcs!
        given_kwargs = [(kw.arg, kw.value) for kw in astNode.keywords] if hasattr(astNode, 'keywords') else []
        num_default_function_args = len(functionAstNode.args.defaults)
        if num_default_function_args == 0:
            function_args_with_defaults = []
        else:
            #defaults only apply to the last N arguments, ao ignore the first M-N (for M total)
            function_args_with_defaults = functionAstNode.args.args[-num_default_function_args:]

        # Look for kwargs (i.e., those with defaults) that match the SQ definition and the runtime argument. These will be used at runtime with the value from the GRAPHify'd version
        for FAN_arg in function_args_with_defaults: # functionASTNode -> FAN
            for kwarg in given_kwargs:
                kwarg_name = kwarg[0]
                kwarg_value = kwarg[1]
                try:
                    if FAN_arg.arg == kwarg_name and not isinstance(kwarg_value, ast.Name):
                        pickle.dumps(kwarg_value) #ensure we can picklize the value, else the default is invalid
                        logger.debug(kwarg_value)
                        self.execution_kwargs[kwarg_name] = get_value_from_ast_keyword(kwarg_value)

                except:
                    logger.error('Failed to get a keyword argument %s, %s' % (kwarg_name, kwarg_value))
                    raise

        #check, that the actual arc-carrying arguments are setup correctly
        self.n_input_ports = len(functionAstNode.args.args) - num_default_function_args #args with defaults are not actually arcs; they should be constant values inserted by the runtime environment
        if self.n_input_ports != len(astNode.args): #ast.args refers to positional arguments
            err = TTSyntaxError(f"SQ creation: {self.function_name} expects {self.n_input_ports} argument(s) -- {len(astNode.args)} supplied. Check the arguments with and without default values in the GRAPHify and SQify version of the function called", self.astNode.lineno)
            raise err

        self.setup_meta_kwargs(astNode, firing_rule_type=firing_ryle_type, clock_dict=clock_dict)

        logger.debug('execution kwargs: %s' % self.execution_kwargs)


    def setup_meta_kwargs(self, astNode, firing_rule_type=TTFiringRuleType.Timed, clock_dict={}):
        '''
        Analyze the meta keywords (generally starting with 'TT') and attach those to the arguments used for the synchronization (firing rule) or execution kwargs instance variable (a dictionary). This will loop through all the keyword args and look only for those we know to check for. Anything generic should already be handled.

        :param astNode: The abstract syntax tree node (generally, a Call object) from the GRAPHify-cation
        :type astNode: ``ast.AST`` (may be one of several subtypes, like _ast.Call)
        :param firing_rule_type: A desgnator for the type of the firing rule, defaulting to 'Timed' (which looks for any amount of overlap in the time interval in the token ``TTTag``)
        :type firing_rule_type: TTFiringRuleType
        :param clock_dict: A dictionary of clocks defined in the graph, default to empty (``{}``)
        :type clock_dict: dict
        '''
        kwargs = {k.arg: k.value for k in astNode.keywords} if hasattr(astNode, 'keywords') else {}

        # * All of these are runtime TT arguments
        # NOTE: should we differentiate between runtime and static TT arguments?
        for key in kwargs:
            if key[0:2] == 'TT':
                logger.debug('Found a meta keyword argument: %s = %s' % (key, kwargs[key]))
                # logger.debug('Found a meta keyword argument: %s = %s' % (key, kwargs[key].value))

            # look for known meta keywords and handle appropriately; may be used for execution or synchronization
            if key == 'TTClock':  #also check if Streamify/TimeRetrigger rule??
                logger.debug('Creating clock for firing rule kwargs')
                clock_var_name = kwargs[key].id
                try:
                    clock = clock_dict[clock_var_name]
                    self.firing_rule_kwargs['streaming_clock'] = clock
                    self.execution_kwargs['TTClock'] = clock
                except KeyError:
                    raise SyntaxError('clock %s does not appear to exist' %
                                      clock_var_name)
            elif key == 'TTPeriod':
                streaming_period = get_value_from_ast_keyword(kwargs[key])
                assert isinstance(
                    streaming_period, int
                ), 'TTPeriod keyword must be an integer and constant value'
                self.firing_rule_kwargs['streaming_period'] = streaming_period
                # self.firing_rule_kwargs['streaming_period'] = kwargs[key].value
                if self.execution_kwargs.get(
                        'TTDataIntervalWidth', None
                ) is None and firing_rule_type == TTFiringRuleType.TimedRetrigger:
                    self.execution_kwargs[
                        'TTDataIntervalWidth'] = self.firing_rule_kwargs[
                            'streaming_period']  #default for data validity interval is the period

            elif key == 'TTPhase':
                streaming_phase = get_value_from_ast_keyword(kwargs[key])
                assert isinstance(
                    streaming_phase, int
                ), 'TTPhase keyword must be an integer and constant value'
                self.firing_rule_kwargs['streaming_phase'] = streaming_phase
                # self.firing_rule_kwargs['streaming_phase'] = kwargs[key].value

            elif key == 'TTDataIntervalWidth':
                interval_width = get_value_from_ast_keyword(kwargs[key])
                assert isinstance(
                    interval_width, int
                ), 'TTDataIntervalWidth keyword must be an integer and constant value'
                self.execution_kwargs['TTDataIntervalWidth'] = interval_width

        # handle missign arguments that are known to be necessary
        if self.firing_rule_kwargs.get('streaming_clock', None) == None and firing_rule_type==TTFiringRuleType.TimedRetrigger:
            try:
                #if unspecified, we'll use the root clock
                root_clock = clock_dict[list(clock_dict.keys())[0]].trace_to_root() #pull out some clock and trace to its root; use that as the default when unspecified
                self.firing_rule_kwargs['streaming_clock'] = root_clock
            except: pass

    def set_input_arcs(self, arcs):
        '''
        Set the input arcs for this SQ, first checking to ensure they match the expected number of ports

        :param arcs: The set of arcs that feed into this SQ
        :type arcs: list(TTArc)
        '''
        # TODO: We allow void functions to have an extra arc for triggers. Should this be also modified at the function level?
        if not (len(arcs) == 1 and self.n_input_ports == 0) and len(arcs) != self.n_input_ports:
            err = TTSyntaxError(
                f"SQ creation: {self.function_name} expects {self.n_input_ports} argument(s) -- {len(arcs)} supplied.",
                self.astNode.lineno)
            raise err
        self.input_arcs = arcs

    def port_number_of_input_symbol(self, input_symbol):
        '''
        Determine the port number(s) that an input symbol would arrive on. There may be multiple in case an argument is used multiple times as inputs to the same function (e.g., a Multipy node attempting to square a value)

        :param input_symbol: The name of an input symbol (variable name) from the compilation process. Inlined expressions may generate their own symbols (format $N, for integer N)
        :type input_symbol: string

        :return: A list of port numbers that the input symbol will be used at
        :rtype: list(int)
        '''
        port_nums = [] #there may be multiple; imagine b=a*a
        for i, arc in enumerate(self.input_arcs):
            if arc.symbol == input_symbol:
                port_nums.append(i)

        # check if it's an input control port arc
        if self.input_control_arc and self.input_control_arc.symbol == input_symbol:
            port_nums.append(len(self.input_arcs))

        return port_nums

    def json(self):
        # print(f"SQ context at JSON time is {self.context} with clockspec {self.context.clockspec}")
        j = {}
        j['sq_id'] = self.id()
        j['context'] = self.context.json()
        j['map'] = {}
        j['sync'] = self.json_sync()
        j['execute'] = self.json_execute()
        j['constraints'] = self.constraints
        # print('sq json %s' % j)
        return j

    def json_sync(self):
        j = {}
        j['sq_name'] = self.sq_name
        j['firing_rule'] = self.json_firing_rule()
        j['input_ports'] = self.json_input_ports()
        j['streaming'] = self.is_streaming
        return j

    def json_firing_rule(self):
        j = {}
        if self.firing_rule.rule_type == TTFiringRuleType.Strict:
            j['type'] = 'strict'
        elif self.firing_rule.rule_type == TTFiringRuleType.Timed:
            j['type'] = 'timed'
        elif self.firing_rule.rule_type == TTFiringRuleType.TimedRetrigger:
            j['type'] = 'timed_retrigger'
        elif self.firing_rule.rule_type == TTFiringRuleType.SequentialRetrigger:
            j['type'] = 'sequential_retrigger'
        else:
            j['type'] = 'unknown'
        return j

    def json_input_ports(self):
        j = []
        for arc in self.input_arcs:
            j.append( { 'entry' : True ,
                        'port_name' : arc.id() } )
        return j

    def json_execute(self):
        #This is only going to work for Python 3 for now
        j = {}
        j['sq_name'] = self.sq_name,
        j['program'] = {
                        'type' : self.json_program_type() ,
                        'instructions' : self.function_source ,
                        'function_name' : self.function_name,
                        # 'execution_keywords': self.execution_kwargs, #This line is especially problematic as the execution_keywords can include parameters that have no obvious JSON serialization format. We could put restrictions and maintain this, but ultimately, we do not use the JSON intermediate representation and should avoid being subject to its limitations.
                        'resources' : {
                             'stack_size' : 0,
                             'local_memory_size' : 0,
                             'internal_ports' : []
                        }}
        j['output_ports'] = self.json_output_ports()
        return j

    def json_output_ports(self):
        j = []
        for arc in self.output_arcs:
            j.append( { 'port_name' : arc.id(),
                        'output_tag_rule' : ''})
        return j

    def json_program_type(self):
        if self.interpreter == TTInterpreter.IoTA:
            return 'iota'
        elif self.interpreter == TTInterpreter.Python3:
            return 'python3'
        else:
            return 'unknown'

def get_value_from_ast_keyword(keyword):
    if isinstance(keyword, ast.Num): return keyword.n
    elif isinstance(keyword, ast.Constant): return keyword.value
    elif hasattr(keyword, 'value'): return keyword.value
    else: raise ValueError("Unable to retrieve value from ast keyword: %s" % (keyword))



# SQification is NOT SQ creation.  SQification is a static transformation of a static
# function into a new function that takes tokens as inputs and produces tokens as
# output.
#
# SQified functions are CALLED in the larger code in the same way that a non-SQified
# function is called.  Each such call instance is separate.  It is these call-instances
# that need to capture the relevant lexical context in which they are encapsulated to
# record deadline and clock information along with mapping constraints such as
# limitations on the set of ensembles over which the SQ call-instance may be applied.

# Timekeeping is maintained automatically by the SQify wrapper.

def SQify(function):
    '''
    Decorator for transforming vanilla Python functions into ``SQ`` templates
    that take in and return ``TTTokens``

    :param function: the function to be ``@SQify``-ed
    :type function: function
    '''
    @wraps(function)
    def wrapper(*tokens, **kwargs):
        '''
        Hardcoded docstring in the wrapper
        '''
        #wrapper.__doc__ = '''This is a substitute docstring'''

        if len(kwargs) != 0 and "const" in kwargs and (len(tokens)) ==1:
            # Special case
            time = tokens[0].time
            # time = TTTime.infinite(TTClock.root())  # Constants are not time-limited in the interpreter
            value = kwargs["const"]
            return [TTToken(value, time)]
        else:

            # Since TTPython allows bare constants in the code, we have to anticipate that some
            # args as inputs to SQified functions may not be tokens.  Allow for that.
            token_times = map(lambda x: x.time if isinstance(x, type(TTToken(None, None))) else TTTime.infinite(tokens[0].time.clock), tokens)
            time_overlap = TTTime.common_ancestor_overlap_time_multi(*token_times)
            if time_overlap:
                if kwargs.get('TTExecuteOnFullToken', False):
                    # just used for a check to make sure the clock isn't mutated within the function.
                    before_clock = deepcopy(time_overlap.clock)
                    return_token = function(*tokens, **kwargs)

                    # TODO: check the return value is tuple, regardless convert into a list of return values
                    if isinstance(return_token, tuple):
                        return_token = list(return_token)
                    else:
                        return_token_list = [return_token]

                    for return_token in return_token_list:
                        assert return_token.time.clock == before_clock, (
                            'The clock may not be changed in an SQ that has '
                            'access to full tokens; this is to avoid other '
                            'side effects in the system.'
                        )

                    return return_token_list #The user will do as they please to this token. The output tag will be changed after this returns
                else:

                    token_values = map(
                        lambda x: x.value
                        if isinstance(x, type(TTToken(None, None))) else x,
                        tokens)
                    # TODO: fix hack
                    # * if in actuallity it's a parameterless function, should
                    # * drop parameter
                    if (len(signature(function).parameters) == 0):
                        token_values = []
                    return_value = function(*token_values, **kwargs)

                    if isinstance(return_value, tuple):
                        return_val_list = list(return_value)
                    else:
                        return_val_list = [return_value]

                    return [
                        TTToken(
                            v,
                            TTTime(time_overlap.clock, time_overlap.start_tick,
                                   time_overlap.stop_tick))
                        for v in return_val_list
                    ]

            else:
                raise Exception('Time', f"{function.__name__}({tokens}) -- token times do not overlap")
    return wrapper


# STREAMification is a function wrapper that is similar to, but NOT the same as SQification.
#
# An SQified function runs to completion each time it is invoked.  It accepts input tokens
# and produces an output token.
#
# A CPSified function is one that is intended as a STREAMING SOURCE.  Like an SQ, it is
# INSTANTIATED, and there may be multiple independent instantiations of a given CPSified
# function in a graph just as there can be multiple independent instantiations of an SQified
# function in a graph.
#
# But when an instance of a CPSified function is triggered by the arrival of one or more
# input tokens, it begins a process of issuing MULTIPLE output tokens at a specified rate
# according to an instance-specific clock.  This is intended for modeling PERIODIC
# sources like cameras. The period, phase, clock domain, and interval width are intended
# to be provided as keyword arguments 'TTClock', 'TTPeriod'', 'TTPhase', and 'TTDataValidityInterval'.
#
# With recent changes, the wrapper that surrounds STREAMify is hardly different from SQify; rather,
# the retriggering mechanisms happen in the runtime processes that encapsulte synchronization and
# execution of SQs.
def STREAMify(function):
    '''
    Decorator for turning a vanilla python function into one that will produce
    a stream of values. The main difference between this decorator and ``SQify``
    is that it forces the firing rule to be ``TTFiringRuleType.TimedRetrigger``,
    which will cause the SQ to run periodically according to meta-parameters
    provided when calling within the ``@GRAPHify`` decorated function. The same
    function will be rerun for each iteration of the stream. A good use case
    is sampling a sensor.

    To specify the clock domain, periodicity, phase, and data validity interval,
    use keyword arguments TTClock, TTPeriod, TTPhase, and TTDataValidityInterval
    with constant valued (or clock variable-named) input to those keyword
    arguments when calling this in the ``@GRAPHify`` -ed function.

    :param function: The function to be ``STREAMify`` -ed
    :type function: function
    '''
    def wrapper(*tokens, **kwargs):

        token_times = map(lambda x: x.time if isinstance(x, type(TTToken(None, None))) else TTTime.infinite(tokens[0].time.clock), tokens)
        #     # Compute the overlap among all the input tokens
        time_overlap = TTTime.common_ancestor_overlap_time_multi(*token_times)
        if time_overlap:
            if kwargs.get('TTExecuteOnFullToken', False):
                before_clock = deepcopy(time_overlap.clock)
                return_token = function(*tokens)
                assert return_token.time.clock == before_clock, 'The clock may not be changed in an SQ that has access to full tokens; this is to avoid other side effects in the system.'
                
                return return_token # The user will do as they please to this token; but what if they change the clock? This may have large side effects
            else:
                token_values = map(
                    lambda x: x.value
                    if isinstance(x, type(TTToken(None, None))) else x, tokens)
                return_value = function(*token_values)

                if isinstance(return_value, tuple):
                    return_val_list = list(return_value)
                else:
                    return_val_list = [return_value]

                return [
                    TTToken(
                        v,
                        TTTime(time_overlap.clock, time_overlap.start_tick,
                                time_overlap.stop_tick))
                    for v in return_val_list
                ]

    return wrapper


# GRAPHification is only to be applied to the top level (i.e., main) function.
# GRAPHification creates the root clock, tokenizes the arguments, invokes
# the wrapped function (which must be written using only SQified functions)
# and then de-tokenizes the returned value.

# In that sense, GRAPHification is the opposite of SQification.

# In "normal" use, the MAINified function should not have inputs nor outputs.
# These, instead, should come from / go to TTCPSource and TTCPSink nodes.

def GRAPHify(function):
    def wrapper(*args, **kwargs):
        with TTClock.root() as CLOCK:
            t0 = TTTime.infinite(CLOCK)
            tokens = map(lambda x: TTToken(x, t0), args)
            result_token = function(*tokens)
            return result_token.value

    return wrapper
