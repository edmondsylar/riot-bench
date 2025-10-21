# Copyright 2021 Carnegie Mellon University
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

code = """
def hailstone(n):
    if n == 1:
        return 1
    if n % 2 == 0:
        return hailstone(n // 2)
    if n % 2 == 1:
        return hailstone(3 * n + 1)

def mapper(f, lst):
    return list(map(f, lst))

def lrange(n):
    return list(range(n))

def main():
    return mapper(hailstone, lrange(20))
"""

import ast
import ast_scope
import networkx as nx
import matplotlib.pyplot as plt
tree = ast.parse(code)
scope_info = ast_scope.annotate(tree)
directed_graph = scope_info.static_dependency_graph

print(directed_graph)
plt.subplot(121)
nx.draw(directed_graph)