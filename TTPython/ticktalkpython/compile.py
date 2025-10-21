#!/usr/bin/python

import sys
import argparse


def main():
    parser = argparse.ArgumentParser(
        description='Compile a TTPython program to the DFG')

    parser.add_argument('file', metavar='F', type=str, help='file to compile')
    parser.add_argument(
        '-o',
        '--out',
        nargs='?',
        default='./output',
        help='output file name of the compile TTPython program')
    parser.add_argument(
        '--ast',
        action='store_true',
        default=False,
        help='flag whether to print out the compiled program\'s ast')
    parser.add_argument(
        '-g',
        '--graph',
        action='store_true',
        default=False,
        help='flag whether to show the compiled program\'s dataflow graph')

    args = parser.parse_args()

    # TODO: allow multi-file compilation
    file = args.file
    is_py = file[-3:] == '.py'
    if is_py:
        file = file[:-3]
    else:
        print("file given is not a Python program")
        return 1

    outpath = args.out
    if outpath[-1] != '/':
        outpath = outpath + '/'

    ast = args.ast

    filepath = file.split('/')
    filename = filepath[-1]
    file_import = file.replace('/', '.')

    inpath = f"./{'/'.join(filepath[:-1])}/"
    showGraph = args.graph

    sys.path.append('tt/')
    from tt.Compiler import TTCompile

    exec(f"import {file_import}")

    print(f"Compiling {filename}")
    TTCompile(filename,
              inpath=inpath,
              outpath=outpath,
              printAST=ast,
              showGraph=showGraph,
              use_graphviz=showGraph)


if __name__ == "__main__":
    main()
