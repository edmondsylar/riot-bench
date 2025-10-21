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

These rules are automatically called as the ast (abstract syntax tree) library 'visits'
syntactic structures within the TTPython file to compile.

The ``TTSQ`` constructor is also an especially essential component of the compilation process!
'''

import ast
from typing import Any, List
import ast_scope
import astor   # be sure to pip install this...
from os import path, listdir
import sys
import pprint
from SQ import TTSQ, TTSQContext,  TTSQPattern
from copy import copy
from Stack import TTStack
from Clock import TTClockSpec, TTClock
from Arc import *
from Error import *
from Graph import TTGraph
import Query

import copy

from functools import reduce
from FiringRule import TTFiringRuleType

import DebugLogger
logger = DebugLogger.get_logger('CompilerRules')

# Rules for handling imported files
#
# Extract the SQified functions and ignore the rest


class TTImportVisitor(ast.NodeVisitor):
    ''''''
    def __init__(self, graph, debug=False):
        self.graph = graph
        self.debug = debug

    def visit_ImportFrom(self, node):
        # print(f"Importing SQified functions from {node.module}.py")
        import_sqified_functions_from_module(node.module, self.graph)

    def visit_FunctionDef(self, node):
        for decorator in node.decorator_list:
            # print(astor.dump_tree(decorator))
            if isinstance(decorator, type(
                    ast.Name())) and (decorator.id == 'SQify'
                                      or decorator.id == 'STREAMify'
                                      or decorator.id == "Resampler"):
                # print(f"SQified function: {node.name}")
                self.graph.sqFunctionDictionary[node.name] = node


def get_deps(node):
    _, statements = next(ast.iter_fields(node))

    full_graph = {
        assign.targets[0].id: [
            d.id for d in ast.walk(assign) if isinstance(d, ast.Name)
        ]
        for assign in statements
    }
    # full_graph also contains `range` and `i`. Keep only top levels var
    restricted = {}
    for var in full_graph:
        restricted[var] = [d for d in full_graph[var] if d in full_graph and d != var]
    return restricted

# Enter with the name of a module from an "import" statement.
# Find the file by searching sys.path.
# If found, read the file and generate an AST.
# Visit the AST for SQified functions.
def import_sqified_functions_from_module(module, graph):
    slashified_module = module.replace(".","/")
    for path_prefix in sys.path:
        pathname = f"{path_prefix}/{slashified_module}.py"
        if path.exists(pathname):
            with open(pathname, "r", encoding='utf-8') as source:
                imported_module = ast.parse(source.read())
                TTImportVisitor(graph).visit(imported_module)
            return


# gets all free variables in an expression
class TTEnvVisitor(ast.NodeVisitor):
    def __init__(self, node):
        self.node = node
        self.has_constants = False
        self.env = self.visit(node)

    def get_env(self):
        return self.env

    def visit_BinOp(self, node: ast.BinOp) -> set:
        lhs = self.visit(node.left)
        rhs = self.visit(node.right)
        return lhs | rhs

    def visit_UnaryOp(self, node: ast.UnaryOp) -> set:
        return self.visit(node.operand)

    def visit_Name(self, node: ast.Name) -> set:
        return {node.id}

    def visit_Call(self, node: ast.Call) -> set:
        return reduce((lambda acc, arg: acc | self.visit(arg)), node.args, set())

    def visit_IfExp(self, node: ast.IfExp) -> set:
        return self.visit(node.test) | self.visit(node.body) | self.visit(node.orelse)

    def visit_Compare(self, node: ast.Compare) -> set:
        return reduce((lambda acc, c: acc | self.visit(c)), node.comparators,
                      self.visit(node.left))

    def visit_BoolOp(self, node: ast.BoolOp) -> set:
        return reduce(
            (lambda acc, clause: acc | self.visit(clause), node.values, set()))

    def visit_Constant(self, node: ast.Constant) -> set:
        self.has_constants = True
        return set()

    # backward compatibility with 3.7
    def visit_Num(self, node: ast.Constant) -> List[TTArc]:
        return self.visit_Constant(node)

    def visit_NameConstant(self, node: ast.NameConstant) -> List[TTArc]:
        return self.visit_Constant(node)

    def generic_visit(self, node: ast.AST) -> set:
        logger.debug(f"TTEnvVisitor visited {node}")
        return set()

# Rules for handling the main TTPython file

class TTGraphCompilationVisitor(ast.NodeVisitor):
    '''
    A child class of ast.NodeVisitor, which walks through the ast and calls specific handlers for each syntactic construct

    :param graph: An instantiated but empty graph, ready to be filled in as the AST is walked
    :type graph: TTGraph
    '''
    def __init__(self, graph: TTGraph, debug=False, source=[], pathname=None):
        self.graph = graph
        self.context_stack = TTStack()
        self.debug = debug
        self.scope_info = None
        self.source = source
        self.pathname = pathname
        self.symbol_counter = 0
        self.sq_counter = 0
        self.func_counter = 0
        self.converting_literal_to_CONST = False
        self.flattened_constraints = [];

    def gensym(self):
        new_symbol = f"${self.symbol_counter}"
        self.symbol_counter += 1
        return new_symbol

    def get_uniq_sq_name(self, sqName):
        name = sqName + "-" + str(self.sq_counter)
        self.sq_counter += 1
        return name

    def get_uniq_func_name(self, funcName):
        name = funcName + "_" + str(self.func_counter)
        self.func_counter += 1
        return name

    def source_line(self, lineno):
        return self.source[lineno - 1]

    # this function modifies the graph symbol table
    # modifies the provided arcs in the list with a generated symbol if none provided
    def fix_arc_list_symbols(self, arc_list):
        for arc in arc_list:
            if arc.symbol == None:
                arc.symbol = self.gensym()
                self.graph.symbolTable[arc.symbol] = arc

    def n_compare_generator(self, input_arcs, bool_type):
        if type(bool_type) is ast.And:
            func_name  = 'ANDN'
            join_op = ' and '
        elif type(bool_type) is ast.Or:
            func_name = 'ORN'
            join_op = ' or '
        else:
            raise TTCompilerError(f"bruh I can't with this n-type {bool_type}")

        self.fix_arc_list_symbols(input_arcs)

        bool_param_list = ["b" + str(i) for i in range(0, len(input_arcs))]
        # create an meta boolean node, inputs are defined by input_arcs
        bool_py_func_name = self.get_uniq_func_name("ANDN")
        bool_py_func_str = "@SQify\ndef " + bool_py_func_name + "(" + \
            ', '.join(bool_param_list) + "):\n\t return " + join_op.join(bool_param_list)

        bool_call_node = ast.Call(ast.Name(id=bool_py_func_name), input_arcs)
        # returns a module with a single function def. We only want the func def
        bool_py_func = ast.parse(bool_py_func_str).body[0]

        sq_name = self.get_uniq_sq_name(func_name)
        top_context = self.context_stack.tos()

        sq = TTSQ(
            bool_call_node,
            bool_py_func,
            top_context,
            sq_name,
            input_arcs,
            top_context.constraints,
            clock_dict=self.graph.clockDictionary
        )

        self.graph.sqList.append(sq)

        #create an output arc for this sq, but assign the symbol and output destinations later
        output_arcs = [TTArc(sq, None)]
        sq.output_arcs = output_arcs
        return output_arcs

    def generate_merge_sq(self, merge_input_arcs):
        self.fix_arc_list_symbols(merge_input_arcs)
        merge_sq_name = self.get_uniq_func_name("MERGE")
        merge_py_func_str = ("@SQify\ndef " + merge_sq_name +
                             "(then_exp, else_exp):\n\tif else_exp is None:\n"
                             "\t\treturn then_exp\n\treturn else_exp")
        merge_py_func = ast.parse(merge_py_func_str).body[0]

        merge_call_node = ast.Call(ast.Name(id=merge_sq_name),
                                   merge_input_arcs)
        top_context = self.context_stack.tos()
        merge_sq = TTSQ(merge_call_node,
                        merge_py_func,
                        top_context,
                        merge_sq_name,
                        merge_input_arcs,
                        top_context.constraints,
                        firing_rule_type=TTFiringRuleType.Immediate,
                        clock_dict=self.graph.clockDictionary)

        # insert the merge node, return that Arc
        self.graph.sqList.append(merge_sq)
        merge_output_arcs = [TTArc(merge_sq, None)]
        merge_sq.output_arcs = merge_output_arcs

        return merge_output_arcs

    def visit_ImportFrom(self, node):
        # if self.debug:
        #     print(f"*** Importing SQified functions from {node.module}.py")
        import_sqified_functions_from_module(node.module, self.graph)
        return node

    def visit_FunctionDef(self, node):
        # if self.debug:
        logger.debug(f"*** function: {node.name}")
        for decorator in node.decorator_list:
            logger.debug(f"*** decorator: {decorator.id}")
            if decorator.id == 'SQify':
                # if self.debug:
                #     print("*** is SQified")
                self.graph.sqFunctionDictionary[node.name] = node
            if decorator.id == 'STREAMify':
                self.graph.sqFunctionDictionary[node.name] = node

            elif decorator.id == 'GRAPHify':
                # if self.debug:
                #     print("*** is GRAPHified")
                #     print("*** and the current SQified function dictionary is")
                #     pp = pprint.PrettyPrinter(indent=4)
                #     pp.pprint(self.graph.sqFunctionDictionary)
                self.scope_info = ast_scope.annotate(node)
                self.graph.GRAPHified_function = node
                self.graph.graph_name = node.name
                # Create distinguished arcs in the symbol table for the graph's inputs
                # print(astor.dump_tree(node))
                for arg in node.args.args:
                    name = arg.arg
                    arc = TTArc(None, name)  # SQ: None
                    self.graph.symbolTable[name] = arc
                    if self.graph.triggerArc == None:
                        self.graph.triggerArc = arc  # We will use this input to trigger implicitly-defined constants.  But we REALLY need to expand the timestamp...
                # Recursively descend into the body
                self.context_stack.push(TTSQContext("root"))
                for child in node.body:
                    logger.log(5, child)
                    self.visit(child)
                self.context_stack.pop()

            elif decorator.id == 'SELECTify':
                self.graph.sqFunctionDictionary[node.name] = node
                raise TTSyntaxError('selectify not implemented yet')

    def visit_With(self, node):
        # Handle the ast within a 'with' specifier, which are used in TTPython to specify things like clocks or mapping constraints
        # Clone the current context as a starting point
        new_context = TTSQContext(base_context=self.context_stack.tos())
        # Iterate over the context modifications
        for item in node.items:
            # **TEMPORARY**  -- instead, do a pass on the AST first to
            # build the clock tree.  Then insert the TTClock object here instead of the name.
            if not isinstance(item.context_expr, type(ast.Call())):
                err = TTSyntaxError('Illegal context specifier', item.lineno)
                err.source = self.source_line(item.lineno)
                err.pathname = self.pathname
                raise err
            # print(astor.dump_tree(item))
            # withitem(
            #   context_expr=Call(func=Attribute(value=Name(id='TTClock'), attr='root'), args=[], keywords=[]),
            #   optional_vars=Name(id='CLOCK'))
            # Could be TTClock(...)
            #   function_id = item.context_expr.func.id
            # or it could be TTClock.root()
            #   function_id = item.context_expr.func.value.id

            root_clock = False
            # Hackish way to do this:
            try:
                function_id = item.context_expr.func.id
            except:
                function_id = item.context_expr.func.value.id
                root_clock = True

            new_context.name = function_id
            if function_id == "TTClock":
                clock_var_name = item.optional_vars.id  # e.g., 'CLOCK'
                if root_clock:
                    clock_print_name = 'ROOT' #assume the print name as 'ROOT' so it doesn't have to be specified
                else:
                    clock_print_name = item.context_expr.args[0].s  # e.g., 'local_root'
                new_context.name = f'with TTClock({clock_print_name})'

                if clock_var_name in self.graph.clockDictionary.keys():
                    err = TTSyntaxError(f"Clock name {clock_var_name} is being re-defined here", item.lineno)
                    err.source = self.source_line(item.lineno)
                    err.pathname = self.pathname
                    raise err

                n_args = 1 if root_clock else len(item.context_expr.args)
                if n_args == 1:
                    #if there are no other arugments, this must be the root cock
                    new_clock = TTClock.root()
                    new_clock.name = clock_print_name
                elif n_args == 4:
                    # there should be 4 args for non-root clocks: name, parent, period, epoch
                    parent_clock = item.context_expr.args[1].id
                    try:
                        self.graph.clockDictionary[parent_clock]
                    except KeyError:
                        raise TTSyntaxError(f"Attemped to create a clock {clock_print_name} for a parent '{parent_clock}' that has not been specified", node.lineno)
                    period = item.context_expr.args[2].n            # **Check** should only be a Num node
                    epoch = item.context_expr.args[3].n             # **Check** should only be a Num node

                    parent_clock = self.graph.clockDictionary[item.context_expr.args[1].id] #search for the parent clock based on variable name
                    new_clock = TTClock(clock_print_name, parent_clock, period, epoch)
                else:
                    err = TTSyntaxError(f"Incorrect arglist for clock spec",
                                        item.lineno)
                    err.source = self.source_line(item.lineno)
                    err.pathname = self.pathname
                    raise err

                self.graph.clockDictionary[clock_var_name] = new_clock
                new_context.clock = new_clock
            elif function_id == "TTConstraint":
                # TTQuery to apply mapping contraints to any SQs that appear within this block
                new_context.name = 'with TTConstraint'
                kwargs = item.context_expr.keywords
                # we assume the 'components' kwarg will point to a list
                component_list_search = [
                    k.value.elts for k in kwargs if k.arg == 'components'
                ]
                component_list = component_list_search[0] if 0 < len(
                    component_list_search) else []

                # if expr required for 3.7 ast parsing
                ens_name_list = (lambda l: l if len(l) == 1 else [])([
                    Query.TTQCEnsembleName(k.value.s if isinstance(
                        k.value, ast.Str) else k.value.value) for k in kwargs
                    if k.arg == 'name'
                ])

                # assumes args are string constants
                # if expr required for 3.7 ast parsing
                name_query_list = [
                    Query.TTQCComponentName(
                        c.s if isinstance(c, ast.Str) else c.value)
                    for c in component_list
                ]

                new_context.constraints = name_query_list + ens_name_list
                self.flattened_constraints.extend(new_context.constraints)
            else:
                err = TTSyntaxError(f"Illegal context specifier", node.lineno)
                err.source = self.source_line(node.lineno)
                err.pathname = self.pathname
                raise err
        #if self.debug:
        #    print (f"*** New context {new_context}")       # Name of the context function
        self.context_stack.push(new_context)

        # Recursively descend into the body
        for child in node.body:  # ast.iter_child_nodes(node.body):
            logger.debug('Child of functionDef visit: %s' % child)
            self.visit(child)
        self.context_stack.pop()
        #if self.debug:
        #    print(f"*** Popped to context {self.context_stack.tos()}")

    def visit_Assign(self, node):
        # Logic:
        #
        # Process the right hand side of the assigmnet (an expression).
        # The value returned will be a TTArc with an assigned source SQ.
        # Add an entry to the symbol table that links the left hand symbol to this TTArc.
        #
        #print(astor.dump_tree(node))
        assignment_list = node.targets
        # In TTPython, we only allow assignment to a single identifier in a given assignment statement.
        if len(assignment_list) > 1:
            err = TTSyntaxError('Only one identifier is allowed on the left hand side of an assignment', node.lineno)
            err.source = self.source_line(node.lineno)
            err.pathname = self.pathname
            raise err
        raw_symbol = assignment_list[0].id

        # Symbols may be re-used, and the usage in a scope may shadow a different usage in an outer scope.
        # Disallow re-definititions within a scope, and re-name shadowing symbols to dis-ambiguate them from
        # shadowed definitions in outer scopes

        # **Temporary**
        unique_symbol = raw_symbol
        if unique_symbol in self.graph.symbolTable.keys():
            err = TTSyntaxError('Multiple assignments to the same symbol', node.lineno)
            err.source = self.source_line(node.lineno)
            err.pathname = self.pathname
            raise err
        arc_list = self.visit(node.value)  # Expecting an Expr
        if 1 < len(arc_list):
            err = TTSyntaxError('lhs expression returns more than 1 value!', node.lineno)
            err.source = self.source_line(node.lineno)
            err.pathname = self.pathname
            raise err
        arc_list[0].symbol = unique_symbol
        self.graph.symbolTable[unique_symbol] = arc_list[0]

    def visit_Return(self, node):
        # Logic:
        #
        # Process the right hand side of the assignment (an expression).
        # The value returned will be a TTArc with an assigned source SQ.
        #print(astor.dump_tree(node))

        arc_list = self.visit(node.value)  # Expecting an Expr
        for arc in arc_list:
            if arc.symbol == None:
                arc.symbol = self.gensym()
                self.graph.symbolTable[arc.symbol] = arc

    def visit_UnaryOp(self, node):
        # print(astor.dump_tree(node))
        if isinstance(node.op, type(ast.USub())):
            func_string = 'NEG'
        else:
            err = TTSyntaxError('Unrecognized unary operation', node.lineno)
            err.source = self.source_line(node.lineno)
            err.pathname = self.pathname
            raise err
        func = ast.Name(id=func_string)
        arc_arg_list = self.visit(node.operand)
        if len(arc_arg_list) != 1:
            raise TTSyntaxError('Unary operation received more than 1 expr', node.lineno)
        arc_arg = arc_arg_list[0]
        if arc_arg.symbol == None:
            arc_arg.symbol = self.gensym()
            self.graph.symbolTable[arc_arg.symbol] = arc_arg
        args = [ast.Name(id=arc_arg.symbol)]
        call_node = ast.Call(func, args)
        # Process the new Call node -- it should return an Arc -- we return that Arc in turn
        return self.visit_Call(call_node)

    def visit_BinOp(self, node):
        # In:  BinOp(left=BinOp(left=Name(id='a'), op=Add, right=Name(id='b')),
        #           op=Mult,
        #           right=BinOp(left=Name(id='a'), op=Sub, right=Name(id='b'))))
        # print(astor.dump_tree(node))
        if isinstance(node.op, type(ast.Add())):
            func_string = 'ADD'
        elif isinstance(node.op, type(ast.Sub())):
            func_string = 'SUB'
        elif isinstance(node.op, type(ast.Mult())):
            func_string = 'MULT'
        elif isinstance(node.op, type(ast.Div())):
            func_string = 'DIV'
        else:
            err = TTSyntaxError('Unrecognized binary operation', node.lineno)
            err.source = self.source_line(node.lineno)
            err.pathname = self.pathname
            raise err
        func = ast.Name(id=func_string)

        # Visit the left and right nodes -- each should return a TTArc.
        # Each TTArc may be a result of the node being a Name (easy),
        # but if the node a Call or another BinOp, then the TTArc
        # has no programmer-specified symbol with which the arc
        # is associated.  So we make one up.
        arc_left_list = self.visit(node.left)
        arc_right_list = self.visit(node.right)

        if len(arc_left_list) != 1:
            raise TTSyntaxError(
                'Binary operation received more than 1 expr on lhs',
                node.lineno)
        if len(arc_right_list) != 1:
            raise TTSyntaxError(
                'Binary operation received more than 1 expr on rhs',
                node.lineno)

        arc_left = arc_left_list[0]
        arc_right = arc_right_list[0]
        if arc_left.symbol == None:
            arc_left.symbol = self.gensym()
            self.graph.symbolTable[arc_left.symbol] = arc_left
        if arc_right.symbol == None:
            arc_right.symbol = self.gensym()
            self.graph.symbolTable[arc_right.symbol] = arc_right
        args = [ast.Name(id=arc_left.symbol), ast.Name(id=arc_right.symbol)]
        call_node = ast.Call(func, args)
        # Process the new Call node -- it should return an Arc -- we return that Arc in turn
        return self.visit_Call(call_node)

    def visit_BoolOp(self, node: ast.BoolOp) -> List[TTArc]:
        bool_input_arcs = [
            input_arc
            for arc_list in [self.visit(clause) for clause in node.values]
            for input_arc in arc_list
        ]

        return self.n_compare_generator(bool_input_arcs, node.op)

    def visit_Compare(self, node: ast.Compare) -> List[TTArc]:
        arc_left_comp_list = self.visit(node.left)
        arc_comp_list = [
            input_arc
            for arc_list in [self.visit(comp) for comp in node.comparators]
            for input_arc in arc_list
        ]
        arcs = arc_left_comp_list + arc_comp_list

        self.fix_arc_list_symbols(arcs)

        arc_and_list = []
        for i in range(0, len(arcs) - 1):
            left_arc = arcs[i]
            right_arc = arcs[i + 1]

            if isinstance(node.ops[i], type(ast.Eq())):
                func_string = 'EQ'
            elif isinstance(node.ops[i], type(ast.NotEq())):
                func_string = 'NEQ'
            elif isinstance(node.ops[i], type(ast.Lt())):
                func_string = 'LT'
            elif isinstance(node.ops[i], type(ast.LtE())):
                func_string = 'LTE'
            elif isinstance(node.ops[i], type(ast.Gt())):
                func_string = 'GT'
            elif isinstance(node.ops[i], type(ast.GtE())):
                func_string = 'GTE'
            else:
                raise TTSyntaxError(
                    f'Compare operator {node.ops[i]} not implemented',
                    node.lineno)

            func = ast.Name(id=func_string)
            args = [
                ast.Name(id=left_arc.symbol),
                ast.Name(id=right_arc.symbol)
            ]
            call_node = ast.Call(func, args)
            # Process the new Call node -- it should return an Arc -- we return that Arc in turn
            arc_and_list.extend(self.visit_Call(call_node))

        return self.n_compare_generator(arc_and_list, ast.And())


    # Create an SQ for this call and a TTArc for its output.
    # Return the TTArc in a list
    def visit_Call(self, node):
        # print(astor.dump_tree(node))
        # Ignore top-level calls in the source file (e.g. print(main(...)))
        # "top-level" is recognizable because the context has not yet been defined.
        if self.context_stack.tos() == None:
            return
        # Each call gives rise to a new SQ.  Allocate it (and with it, the TTArc
        # at its output).
        #
        # Each call consumes one or more inputs -- find the corresponding TTArcs, and
        # annotate them with the SQ and port of this SQ
        # if self.debug:
        #     print(f"*** SQ {node.func.id}")
        #     print(self.context_stack.tos())
        #     print(astor.dump_tree(node))

        # Create the SQ for this Call
        sqName = node.func.id
        # Recursively visit the args and collect the TTArcs that are returned
        input_arcs = []

        logger.log(5, astor.dump_tree(node))

        # add triggers for void functions
        if len(node.args) == 0:
            logger.debug(f"node has no arguments!")
            input_arcs = [self.graph.triggerArc]

        for arg in node.args:
            arc_list = self.visit(arg)
            if isinstance(arc_list, List) and isinstance(arc_list[0], TTArc):
                arc = arc_list[0]
                input_arcs.append(arc)
                if arc.symbol == None:
                    arc.symbol = self.gensym()
                    self.graph.symbolTable[arc.symbol] = arc
                if sqName == 'CONST': # is this really necessary? Should just be 1 arg: a trigger
                    break

        if sqName == 'TTFinishByOtherwise':
            if len(node.args) != 1:
                raise TTSyntaxError(
                    f"TTFinishByOtherwise {sqName} has too many parameters",
                    node.lineno, self.source_line(node.lineno), self.pathname)

            planB_check = [
                kwarg.value for kwarg in
                [kw for kw in node.keywords if kw.arg == "TTPlanB"]
            ]
            will_ret_check = [
                kwarg.value for kwarg in
                [kw for kw in node.keywords if kw.arg == "TTWillContinue"]
            ]
            time_deadline_check = [
                kwarg.value for kwarg in
                [kw for kw in node.keywords if kw.arg == "TTTimeDeadline"]
            ]

            if len(planB_check) != 1:
                raise TTSyntaxError(
                    f"TTFinishByOtherwise requires the TTPlanB keyword",
                    node.lineno, self.source_line(node.lineno), self.pathname)

            if len(will_ret_check) != 1:
                raise TTSyntaxError(
                    f"TTFinishByOtherwsie requires the TTWillContinue keyword",
                    node.lineno, self.source_line(node.lineno), self.pathname)

            if len(time_deadline_check) != 1:
                raise TTSyntaxError(
                    f"TTFinishByOtherwise requires the TTTimeDeadline keyword",
                    node.lineno, self.source_line(node.lineno), self.pathname)

            planB = planB_check[0]
            will_ret = will_ret_check[0]
            time_deadline = time_deadline_check[0]

            # need to relax ast.Constant for backwards compatibility of ast generation
            if type(will_ret.value) is not bool:
                raise TTSyntaxError(
                    f"TTFinishByOtherwise: TTWillContinue requires a boolean value",
                    node.lineno, self.source_line(node.lineno), self.pathname)

            time_control_arc = self.visit(time_deadline)[0]
            print(time_control_arc)

            if len(input_arcs) != 1:
                raise TTSyntaxError(
                    "TTFinishByOtherwise only can operate on one output", node.lineno)

            func_name = 'DEADLINE'
            deadline_sq_name = self.get_uniq_func_name(func_name)

            # TODO: visit TTPlanB, add it to potential output_arcs
            py_func_text = (
                "@SQify\n"
                "def " + deadline_sq_name + "(x):\n"
                "\tfrom Empty import TTEmpty\n"
                "\tif (x is None):\n"
                "\t\treturn TTEmpty(), None\n"
                "\treturn x, TTEmpty()"
            )

            sqified_function = ast.parse(py_func_text).body[0]
            deadline_node = ast.Call(ast.Name(id=deadline_sq_name), input_arcs)
            top_context = self.context_stack.tos()

            deadline_sq = TTSQ(deadline_node,
                      sqified_function,
                      top_context,
                      deadline_sq_name,
                      input_arcs,
                      top_context.constraints,
                      input_control_arc=time_control_arc,
                      clock_dict=self.graph.clockDictionary,
                      firing_rule_type=TTFiringRuleType.Deadline)
            self.graph.sqList.append(deadline_sq)

            # TODO: exposes SQ linking of arcs, should this be moved to SQ or refactor SQ?
            # conveniently appends to the back, so will be the last
            time_control_arc.add_destination(deadline_sq)
            if time_control_arc.sourceSQ != None and time_control_arc.sourceSQ.is_streaming:
                self.is_streaming = True # streaming designation propagates

            # TODO: figure out if callBack is a constant, func call, lambda, etc.
            # TODO: need to include shadow table to also link planB to the output of the
            # TODO:     deadline sq
            orig_symbol_table = self.graph.symbolTable
            orig_trigger = self.graph.triggerArc

            deadline_trigger = TTArc(deadline_sq, None)
            data_arc = TTArc(deadline_sq, None)
            deadline_output_arcs = [data_arc, deadline_trigger]
            deadline_sq.output_arcs = deadline_output_arcs

            self.graph.triggerArc = deadline_trigger

            try:
                planB_arcs = self.visit_Call(planB)
            except TTCompilerError as e:
                logger.error("must be a function planB with TTFinishByOtherwise for now")
                raise e

            self.graph.symbolTable = orig_symbol_table
            orig_symbol_table[deadline_sq_name + "_trigger"] = deadline_trigger
            self.graph.triggerArc = orig_trigger

            if will_ret.value: # create a merge SQ like an if/else branch
                if len(planB_arcs) != 1:
                    raise TTSyntaxError(
                    f"PlanB at SQ {sqName} has more than 1 return value",
                    node.lineno, self.source_line(node.lineno), self.pathname)

                merge_input_arcs = [data_arc] + planB_arcs
                output_arcs = self.generate_merge_sq(merge_input_arcs)
            else:
                output_arcs = [data_arc]

            return output_arcs

        try:
            sqified_function = self.graph.sqFunctionDictionary[sqName]
        except TTCompilerError:
            logger.error(self.graph.sqFunctionDictionary)
            raise TTCompilerError("UndefinedSQ", f"SQified function {sqName} was not found")
        if sqified_function:
            sqName = self.get_uniq_sq_name(sqName) #ensure the SQ has a unique name by appending a counter
            top_context = self.context_stack.tos()

            sq = TTSQ(node, sqified_function, top_context, sqName, input_arcs, top_context.constraints, clock_dict=self.graph.clockDictionary)
            self.graph.sqList.append(sq)
            #create an output arc for this sq, but assign the symbol and output destinations later
            output_arcs = [TTArc(sq, None)]
            sq.output_arcs = output_arcs

            # if sqName == 'CONST':
            #     print(f"CONST call about to return {output_arc}")
            return output_arcs
        else:
            err = TTSyntaxError(f"SQified function {node.name} is not defined", node.lineno)
            err.source = self.source_line(node.lineno)
            err.pathname = self.pathname
            raise err

    def visit_IfExp(self, node) -> List[TTArc]:
        # Expression(
        # body=IfExp(
        #     test=Name(id='b', ctx=Load()),
        #     body=Name(id='a', ctx=Load()),
        #     orelse=Name(id='c', ctx=Load())))
        if_sq_name = self.get_uniq_func_name("IF")

        arc_check_exp_list = self.visit(node.test)

        then_visitor = TTEnvVisitor(node.body)
        else_visitor = TTEnvVisitor(node.orelse)

        then_env = list(then_visitor.get_env())
        if then_visitor.has_constants:
            then_trigger_name = if_sq_name + "_then_trigger"
            then_env.append(then_trigger_name)
        else_env = list(else_visitor.get_env())
        if else_visitor.has_constants:
            else_trigger_name = if_sq_name + "_else_trigger"
            else_env.append(else_trigger_name)

        free_vars = list(then_visitor.get_env() | else_visitor.get_env())

        param_list = ["_check"] + free_vars

        then_param_list = ', '.join(map(
            str, list(then_env))) + ', TTEmpty()' * len(else_env)
        else_param_list = 'TTEmpty(), ' * len(then_env) + ', '.join(
            map(str, else_env))

        then_branch_text = ("\tif (_check):\n\t\treturn " + then_param_list +
                            "\n")
        else_branch_text = "\telse:\n\t\treturn " + else_param_list

        if_py_func_hdr = "\tfrom Empty import TTEmpty\n"
        # add outputs to triggers
        if then_visitor.has_constants:
            if_py_func_hdr += "\t" + then_trigger_name + " = None\n"
        if else_visitor.has_constants:
            if_py_func_hdr += "\t" + else_trigger_name + " = None\n"

        if_py_func_str = ("@SQify\ndef " + if_sq_name + "(" +
                          ', '.join(map(str, param_list)) + "):\n" +
                          if_py_func_hdr + then_branch_text + else_branch_text)
        if_py_func = ast.parse(if_py_func_str).body[0]

        # lookup the SQs for each free_var
        if_input_arcs = arc_check_exp_list + [
            arc for arc_list in
            [self.visit_Name(ast.Name(id=p)) for p in free_vars]
            for arc in arc_list
        ]

        self.fix_arc_list_symbols(if_input_arcs)

        if_call_node = ast.Call(ast.Name(id=if_sq_name), if_input_arcs)
        top_context = self.context_stack.tos()

        if_sq = TTSQ(if_call_node,
                     if_py_func,
                     top_context,
                     if_sq_name,
                     if_input_arcs,
                     top_context.constraints,
                     clock_dict=self.graph.clockDictionary)
        self.graph.sqList.append(if_sq)

        # TODO: fix this hackage 1/2
        orig_symbol_table = self.graph.symbolTable
        then_shadow_symbol_table = dict([(key, TTArc(if_sq, key))
                                         for key in then_env])
        else_shadow_symbol_table = dict([(key, TTArc(if_sq, key))
                                         for key in else_env])

        # save the original trigger and prep new triggers
        orig_trigger = self.graph.triggerArc
        then_shadow_trigger = orig_trigger
        if then_visitor.has_constants:
            then_shadow_trigger = TTArc(if_sq, if_sq_name + "_then_trigger")
        else_shadow_trigger = orig_trigger
        if else_visitor.has_constants:
            else_shadow_trigger = TTArc(if_sq, if_sq_name + "_else_trigger")

        if_output_arcs = [
            then_shadow_symbol_table[key] for key in then_env
        ] + [else_shadow_symbol_table[key] for key in else_env]
        if_sq.output_arcs = if_output_arcs

        # visit both branches, and replace the symbol table/trigger respectively
        self.graph.symbolTable = then_shadow_symbol_table
        self.graph.triggerArc = then_shadow_trigger
        then_exp_arcs = self.visit(node.body)

        self.graph.symbolTable = else_shadow_symbol_table
        self.graph.triggerArc = else_shadow_trigger
        else_exp_arcs = self.visit(node.orelse)

        # create the join node to merge the if and else branches
        merge_input_arcs = then_exp_arcs + else_exp_arcs
        self.fix_arc_list_symbols(merge_input_arcs)

        merge_output_arcs = self.generate_merge_sq(merge_input_arcs)

        # TODO: fix this hackage 2/2
        # need to put back then/else shadow tables into the real table
        for name, arc in then_shadow_symbol_table.items():
            orig_symbol_table[if_sq_name + "_then_" + name] = arc

        for name, arc in else_shadow_symbol_table.items():
            orig_symbol_table[if_sq_name + "_else_" + name] = arc

        self.graph.symbolTable = orig_symbol_table
        self.graph.triggerArc = orig_trigger

        return merge_output_arcs

    def visit_Name(self, node) -> List[TTArc]:
        # Look up the name using scope resolution rules
        # For the disambiguated version of the name, find the corresponding arc and return it

        # **In Progress**
        #  What if this is not something specified in the 'with' context?

        try:
            if node.id in self.graph.symbolTable:
                return [self.graph.symbolTable[node.id]]
            elif node.id in self.graph.clockDictionary:
                return [self.graph.clockDictionary[node.id]]
            else:
                raise KeyError(node.id)

        except KeyError:
            raise

    def visit_Constant(self, node: ast.Constant) -> List[TTArc]:
        # print(astor.dump_tree(node))
        # If we find a Const as an arg to a BinOp or a function call, we want to
        # insert a CONST() SQ.  In so doing, one of the CONST() parameters will
        # itself be a Const.  We need to break this infinite recursion here:
        if self.converting_literal_to_CONST:
            return
        # A way to handle literal constants in the program -- convert them to CONST() calls
        self.converting_literal_to_CONST = True
        func = ast.Name(id='CONST')
        trigger_arg = ast.Name(id=self.graph.triggerArc.symbol)  # Grab the graph's first input as the trigger
        const_kwarg = ast.keyword(arg='const', value=node)      # make this node the keyword value of the CONST() call
        args = [trigger_arg]
        keywords = [const_kwarg]
        call_node = ast.Call(func, args, keywords)
        result_arc_list = self.visit_Call(call_node)
        self.converting_literal_to_CONST = False
        return result_arc_list

    def visit_Module(self, node: ast.Module) -> Any:
        return super().generic_visit(node)

    # 3.7 compatibility
    def visit_Num(self, node: ast.Constant) -> List[TTArc]:
        new_node = ast.Constant(node.n)
        return self.visit_Constant(new_node)

    def visit_NameConstant(self, node: ast.NameConstant) -> List[TTArc]:
        return self.visit_Constant(node)

    def generic_visit(self, node):
        # print(astor.dump_tree(node))
        err = TTSyntaxError(f'This structure ({type(node)}) is not currently supported in TTPython', node.lineno)
        err.source = self.source_line(node.lineno)
        err.pathname = self.pathname
        raise err
