import ast
import astunparse
import argparse
import astor
from typing import Any, List

from CompilerRules import TTEnvVisitor
import DebugLogger
import pprint
import functools

logger = DebugLogger.get_logger('Preprocess')


class FuncGlobalVisitor(ast.NodeVisitor):
    def __init__(self, debug=False):
        self.func_globals = {}
        self.declared_globals = set()
        self.dfg = None
        self.debug = debug

    def visit_FunctionDef(self, node):
        # logger.debug(f"*** function: {node.name}")

        if 'GRAPHify' in [decorator.id for decorator in node.decorator_list]:
            logger.debug(f"{node.name} is a GRAPHify func")

            dfg_visitor = DFGBuilderVisitor()
            for stmt in node.body:
                dfg_visitor.visit(stmt)
            print(dfg_visitor.dfg)
            self.dfg = dfg_visitor.dfg

        else:
            visitor = GlobalRWVisitor()
            visitor.visit(node)
            self.func_globals[node.name] = {
                'rd': visitor.rd_globals,
                'wr': visitor.wr_globals
            }
            self.declared_globals |= visitor.declared_globals


class GlobalRWVisitor(ast.NodeVisitor):
    def __init__(self, debug=False):
        self.func_globals = {}
        self.debug = debug
        self.rd_globals = set()
        self.wr_globals = set()
        self.declared_globals = set()

    def get_free_vars(self, node):
        v = TTEnvVisitor(node)
        return v.get_env()

    def filter_set(self, gl_set):
        return {gl for gl in gl_set if gl in self.declared_globals}

    def visit_Global(self, node: ast.Global) -> Any:
        self.declared_globals.add(*node.names)

    def visit_Return(self, node: ast.Return) -> Any:
        free_vars = self.filter_set(self.get_free_vars(node.value))
        self.rd_globals |= free_vars

    def visit_Assign(self, node: ast.Assign) -> Any:
        free_vars = self.filter_set(self.get_free_vars(node.value))
        self.rd_globals |= free_vars
        self.wr_globals |= functools.reduce(
            lambda acc, target: acc | self.filter_set(
                self.get_free_vars(target)), node.targets, set())

    def visit_AugAssign(self, node: ast.AugAssign) -> Any:
        rw_var = self.get_free_vars(node.target)
        rd_vars = self.get_free_vars(node.value)
        self.rd_globals |= rw_var | rd_vars
        self.wr_globals |= rw_var


class DFG():
    def __repr__(self):
        return f"<DFG sqs:{repr(self.sqs)}  edges:{repr(self.edges)}>"

    def __init__(self):
        self.sqs = []
        self.edges = []


class Arc():
    def __repr__(self):
        return repr(self.arc_name)

    def __init__(self, name):
        self.arc_name = name


class SQ():
    def __repr__(self):
        return (f"<SQ {repr(self.name)} "
                f"in_arcs:{repr(self.in_arcs)}, "
                f"out_arcs:{repr(self.out_arcs)}>")

    def __init__(self, name):
        self.name = name
        self.in_arcs = []
        self.out_arcs = []


class DFGBuilderVisitor(ast.NodeVisitor):
    def __init__(self):
        self.dfg = DFG()
        self.env = {}
        self.symbol_counter = 0

    def gensym(self):
        new_symbol = f"${self.symbol_counter}"
        self.symbol_counter += 1
        return new_symbol

    def get_arc(self, name):
        if name not in self.env:
            self.env[name] = Arc(name)
        return self.env[name]

    def set_arc(self, arc, name):
        arc.arc_name = name
        self.env[name] = arc

    def visit_Assign(self, node):
        out_arc_list = self.visit(node.value)

        if 1 < len(node.targets):
            raise Exception("only allowing 1 target per assignment for now")
        if 1 < len(out_arc_list):
            raise Exception(
                "only allowing 1 expression per assignment for now")

        var_name = node.targets[0].id
        self.set_arc(out_arc_list[0], var_name)
        return []

    def visit_Return(self, node):
        return self.visit(node.value)

    # def visit_UnaryOp(self, node):
    #     pass

    # def visit_BinOp(self, node):
    #     pass

    # def visit_BoolOp(self, node: ast.BoolOp) -> List[TTArc]:
    #     pass

    # def visit_Compare(self, node: ast.Compare) -> List[TTArc]:
    #     pass

    # Create an SQ for this call and a TTArc for its output.
    # Return the TTArc in a list
    def visit_Call(self, node):
        new_node = SQ(node.func.id)
        new_node.in_arcs = [
            Arc(name) for arg in node.args
            for name in TTEnvVisitor(arg).get_env()
        ]
        new_node.out_arcs = [Arc(self.gensym())]
        self.dfg.sqs.append(new_node)
        return new_node.out_arcs

    # def visit_IfExp(self, node) -> List[TTArc]:
    #     pass

    def visit_Name(self, node):
        return [self.get_arc(node.id)]

    def visit_Constant(self, node: ast.Constant):
        return []

    def visit_Module(self, node: ast.Module) -> Any:
        return super().generic_visit(node)

    # 3.7 compatibility
    def visit_Num(self, node: ast.Constant):
        new_node = ast.Constant(node.n)
        return self.visit_Constant(new_node)

    def visit_NameConstant(self, node: ast.NameConstant):
        return self.visit_Constant(node)

    def generic_visit(self, node):
        # print(astor.dump_tree(node))
        # err.source = self.source_line(node.lineno)
        # err.pathname = self.pathname
        # raise err
        logger.debug(f"at {node}")
        return super().generic_visit(node)


def get_all_parents(dfg, sq):
    upstream_sqs = [s for s in dfg.sq if s in sq.in_arcs]
    parent_sqs = []
    while 0 < len(upstream_sqs):
        parent_sqs += upstream_sqs
        upstream_arcs = [arc for s in upstream_sqs for arc in s.input_arcs]
        upstream_sqs = [s for s in dfg.sq if s in upstream_arcs]


def check_inconsistent_globals(func_g_list, dfg):
    changed = True
    while changed:
        changed = False

        for sq in dfg.sqs:
            upstream_sqs = [s for s in dfg.sq if s in sq.in_arcs]

    pass


def gen_globals_info(ast):
    visitor = FuncGlobalVisitor()
    visitor.visit(ast)
    # logger.debug(visitor.func_globals)
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(visitor.func_globals)

    return visitor


def rename_target(name):
    return ast.Subscript(
        value=ast.Name(id='sq_state'),
        slice=ast.Index(value=ast.Constant(value=name, kind=None)))


def prep_init(name, if_body):
    return ast.If(test=ast.Compare(
        left=ast.Call(func=ast.Attribute(value=ast.Name(id='sq_state'),
                                         attr='get'),
                      args=[
                          ast.Constant(value=name, kind=None),
                          ast.Constant(value=None, kind=None)
                      ],
                      keywords=[]),
        ops=[ast.Eq()],
        comparators=[ast.Constant(value=None, kind=None)]),
                  body=if_body,
                  orelse=[])


def gen_global_hide_local(name):
    return ast.Assign(targets=[
        ast.Subscript(
            value=ast.Name(id='sq_state'),
            slice=ast.Index(value=ast.Constant(value=name, kind=None)))
    ],
                      value=ast.Name(id=name),
                      type_comment=None)


def gen_global_hide_local(name):
    return ast.Assign(
        targets=[ast.Name(id=name)],
        value=ast.Subscript(
            value=ast.Name(id='sq_state'),
            slice=ast.Index(value=ast.Constant(value=name, kind=None))),
        type_comment=None)


class GlobalTransformVisitor(ast.NodeVisitor):
    def __init__(self, g_list, func_globals, debug=False):
        self.g_list = g_list
        self.func_globals = func_globals
        self.g_assigned = {}

    def visit_Module(self, node: ast.Module) -> Any:
        visitor = GTModuleVisitor(self.g_list, self.func_globals)
        xformed_stmts = [visitor.visit(stmt) for stmt in node.body]
        concat_stmts = functools.reduce(lambda acc, stmt: acc + stmt,
                                        xformed_stmts, [])
        node.body = concat_stmts


class GTModuleVisitor(ast.NodeVisitor):
    def __init__(self, g_list, func_globals, debug=False):
        self.g_list = g_list
        self.func_globals = func_globals
        self.g_assigned = {}

    def visit_Assign(self, node: ast.Assign) -> List:
        for i, target in enumerate(node.targets):
            if target.id in self.g_list:
                self.g_assigned[target.id] = node
                node.targets[i] = rename_target(target.id)
        # print(astor.dump_tree(node))
        return []

    def visit_FunctionDef(self, node) -> List:
        logger.debug(f"*** function: {node.name}")

        if 'GRAPHify' in [decorator.id for decorator in node.decorator_list]:
            # don't make any changes
            logger.debug(f"{node.name} is a GRAPHify func")
        else:
            local_g_stmt = [ast.Global(names=['sq_state'])]
            g_list = self.func_globals[node.name]['rd']
            local_decl_stmts = [
                prep_init(name, self.g_assigned[name]) for name in g_list
            ]
            v_body = [
                x for x in [
                    GTFuncVisitor(self.g_list, self.g_assigned).visit(stmt)
                    for stmt in node.body
                ] if x is not None
            ]
            # print(astor.dump_tree(v_body))
            new_body = local_g_stmt + local_decl_stmts + v_body
            # print(astunparse.unparse(new_body))
            node.body = new_body
        return [node]

    def generic_visit(self, node: ast.AST) -> List:
        logger.debug(f"GTModuleVisitor visited {node}")
        return [node]


class GTFuncVisitor(ast.NodeTransformer):
    def __init__(self, g_list, g_assigned, debug=False):
        self.g_list = g_list
        self.g_assigned = g_assigned

    def visit_Global(self, node: ast.Global) -> List:
        return None

    def visit_Name(self, node: ast.Name) -> Any:
        return rename_target(node.id)

    def generic_visit(self, node: ast.AST) -> List:
        logger.debug(f"GTFuncVisitor visited {node}")
        super().generic_visit(node)
        return node


def transform_globals(ast):
    info = gen_globals_info(ast)
    # visitor = GlobalTransformVisitor(info.declared_globals, info.func_globals)
    # visitor.visit(ast)
    # print(astunparse.unparse(ast))
    print('done')


def main():
    parser = argparse.ArgumentParser(description=(
        'Highlights potentially error-prone areas in pre-transformed code '
        'for TTPython deployment.'))
    parser.add_argument('filenames',
                        metavar='F',
                        type=str,
                        nargs='+',
                        help='filenames to run preprocessing on')
    args = parser.parse_args()

    for filename in args.filenames:

        with open(filename, "r") as source:
            module = ast.parse(source.read())

        with open(filename, "r") as source:
            source_list = source.readlines()

        print(astor.dump_tree(module))
        transform_globals(module)


if __name__ == "__main__":
    main()
