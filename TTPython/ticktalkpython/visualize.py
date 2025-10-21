#!/usr/bin/python

import re, sys
from matplotlib import pyplot as plt
import argparse


def extract_output_info_from_line(line):
    value = None
    source_sq = None
    source_ensemble = None
    t = None
    if line[1:8] == 'TTToken':
        start_T_index = line.find('T:')
        value_str = line[9:start_T_index - 1]
        value = float(value_str)

        open_paren_indices = [i.start() for i in re.finditer('\(', line)]
        close_paren_indices = [i.start() for i in re.finditer('\)', line)]
        timestamps_str = line[open_paren_indices[-1] +
                              1:close_paren_indices[-1]]
        start_time = int(timestamps_str.split(',')[0])
        stop_time = int(timestamps_str.split(',')[1])
        t = (start_time + stop_time) / 2

        start_SQ_index = line.find('from SQ "')
        end_SQ_index = line.find('" on ENS: "')
        source_sq = line[start_SQ_index + len('from SQ "'):end_SQ_index]

        start_ensemble_index = end_SQ_index
        end_ensemble_index = line.find('".')  #not very unique..
        source_ensemble = line[start_ensemble_index +
                               len('" on ENS: "'):end_ensemble_index]

    return value, source_sq, source_ensemble, t


def process_outputs(name, output_file, output_SQ_names, list_info):
    phy = 'phy'
    sim = 'simulation'
    header_types = [
        f'start execution of {exec_type} ' for exec_type in (phy, sim)
    ]
    values = [[] for i in range(len(output_SQ_names))]
    times = [[] for i in range(len(output_SQ_names))]
    source_ensembles = [None for i in range(len(values))]
    all_names = set()
    all_sq = set()
    with open(output_file, 'r') as f:
        lines = f.readlines()
        header_lines = []
        if list_info:
            print()
            print("Names:")
        for i, line in enumerate(lines):
            for header_type in header_types:
                if header_type in line:
                    try:
                        cur_name = line[line.index('(') + 1:line.index(')')]
                        if list_info and cur_name not in all_names:
                            all_names.add(cur_name)
                            print(cur_name)
                        if name in (cur_name, ""):
                            header_lines.append(i)
                    except:
                        pass
        try:
            most_recent_set = lines[header_lines[-1]:]
        except:
            print(f"No execution with name {name} found")
            return
        if list_info:
            print()
            print("SQ:")
        for line in most_recent_set:
            val, sq, ens, timestamp = extract_output_info_from_line(line)
            if val != None:
                if list_info and sq not in all_sq:
                    all_sq.add(sq)
                    print(sq)
                try:
                    sq_index = output_SQ_names.index(sq)

                    values[sq_index].append(val)
                    times[sq_index].append(timestamp)
                    source_ensembles[
                        sq_index] = ens  #assume this cannot be more than one
                except:
                    pass

    for i, sq_name in enumerate(output_SQ_names):
        if not source_ensembles[i] is None:
            plt.plot(times[i], values[i], 'b.')
            plt.title("'" + sq_name + "' output from Ensemble '" +
                      source_ensembles[i] + "'")
            plt.ylabel('Token Value')  #we're just going to assume numeric
            plt.xlabel('Time')
            plt.show()
        else:
            print(f"'{sq_name}' does not have a corresponding source_ensemble")


def main():
    parser = argparse.ArgumentParser(
        description='visualize the output of an executed TTPython program')

    parser.add_argument('file',
                        metavar='F',
                        type=str,
                        help='the output file to visualize')
    parser.add_argument('sq_names',
                        metavar='N',
                        type=str,
                        nargs='+',
                        help='sq names to extract')
    parser.add_argument(
        '--name',
        default='',
        help='the name of the execution to show (default: last one that ran)')
    parser.add_argument('--list',
                        action='store_true',
                        default=False,
                        help='lists available sq names in given output file')

    args = parser.parse_args()
    file = args.file
    sq_names = args.sq_names
    name = args.name
    lst = args.list

    sys.path.append('tt/')

    filename = file.split('/')[-1]

    print(f"Viewing {filename}")
    process_outputs(name, file, sq_names, lst)


if __name__ == "__main__":
    main()
