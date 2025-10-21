import sys, os, math, time

# sys.path.insert(0, os.path.abspath('..'))

#everyone's favorite data processing libraries
import pandas as pd
import numpy as np
from matplotlib import pyplot as plt

#e.g. line 1619745841.191991,WM.receiveToken.pythagorean,<TTCompTag:: id:0x7fbfd02e1cd0 func: pythagorean p-name: a p-num: None time:(100, 200)>>
column_names = ["timestamp", "code_context", "data_context"]
MIN_TIME_BETWEEN_TESTS = 30

get_id = lambda string: int(string.split('token_id')[-1].split(':')[-1]) #very specific format... comes from only putting the str(token) into the data_context part of a log item

def read_instrumentation_samples(f=None):
    print('Read new chunk of file')
    data = pd.DataFrame(columns=column_names)
    data_interim = pd.DataFrame(columns=column_names)
    #open file, if it wasn't. May only be partially done with this
    if f==None:
        was_open = False
        f = open('CAV_instrument.log' , 'r')
    else:
        was_open = True

    previous_empty = False
    last_timestamp = math.inf
    try:
        i=0
        for line in f:
            split_line = line.split(',', maxsplit=2)
            if line.strip() == '':
                if previous_empty: 
                    data = data.append(data_interim)
                    break
                previous_empty = True
                continue
            if '===================' in line or not line or float(split_line[0]) - last_timestamp > MIN_TIME_BETWEEN_TESTS: 
                print('trial ended')
                data = data.append(data_interim)
                break
            if not line:
                print('hit end of file')
                f.close()
                raise EOFError()
            # data = data.append(line.split(','))
            df_l = pd.DataFrame([split_line], columns=column_names)
            data_interim = data_interim.append(df_l)
            previous_empty = False
            last_timestamp = float(split_line[0])
            i+=1
            if i%100 == 0:
                print('%dth line read' % i)


            if i%10000 == 0:
                #append to the larger dataset periodically to reduce 
                data = data.append(data_interim)
                data_interim = pd.DataFrame(columns=column_names)
                # print('%dth line read' % i)



    except KeyboardInterrupt:
        print('Interrupted on...')
        print(line)
        print(next(f))
        print('.')
        raise
    
    data = data.sort_values(column_names[0])

    if not was_open:
        f.close()
        print('closed file')

    return data

def process_samples(df):
    print('Process samples')
    first_timestamp = df.iloc[0,0]
    #get a list of the process names
    process_names = set()
    for i, row in df.iterrows():
        if 'START' in row[1]:
            process_names.add(row[1].split('.')[-1])
    
    # print(process_names)

    process_names = list(process_names)
    process_wm_latencies = [[] for i in range(len(process_names))]
    deadline_hits = [0 for i in range(len(process_names))]
    total_calls = [0 for i in range(len(process_names))]
    process_num_args = [None for i in range(len(process_names))]
    unprocessed_tokens = 0


    #make indexing faster by storing a dictionary of the indices, rather than searching each time
    process_ind_dict = {}
    for i, n in enumerate(process_names): process_ind_dict[n] = i


    #measure overhead of waiting matching
    waiting = {}
    for i, row in df.iterrows():
        if 'PM.give_token_to_process' in row[1]:          
            token_id = get_id(row[2])
            timestamp = float(row[0])
            waiting[token_id] = timestamp

        if 'WM.processToken_CALL' in row[1]:
            function_name = row[1].split('.')[-1]
            total_calls[process_ind_dict[function_name]] += 1 


            timestamp = float(row[0])
            token_ids = row[2].split('ids:')[-1].strip().strip('[]').split(',')
            token_ids = [int(i) if i!=None and 'None' not in i else -1 for i in token_ids] 
            process_num_args[process_ind_dict[function_name]] = len(token_ids)

            latency = math.inf
            valid = True
            for ti in token_ids:
                if ti==-1:
                    #deadline went off; skip this one entirely. Overhead hard to measure
                    valid = False
                    deadline_hits[process_ind_dict[function_name]] += 1 
                    break
                if ti>=0:      
                    try:
                        latency = min(latency, timestamp-waiting[ti])
                        del waiting[ti]
                    except KeyError:
                        valid = False
                        break

            if valid:
                func_ind = process_ind_dict[function_name]
                process_wm_latencies[func_ind].append(latency)
        #TODO: remove anything exceptionally old for 'waiting'

        if i % 10000 == 0:
            pass
            #remove old tokens from 'waiting'... garbage collection would have removed those explicitly
        
    unprocessed_tokens = len(waiting)

    return first_timestamp, process_names, process_num_args, process_wm_latencies, deadline_hits, total_calls, unprocessed_tokens



def analyze(process_names, process_num_args, process_wm_latencies, deadline_hits, total_calls):
    # TODO: add standard deviation to overhead

    columns = ['function name', 'average overhead', 'min overhead', 'max overhead', '5 percentile overhead','25 percentile overhead', '75 percentile overhead', '95 percentile overhead','median overhead', 'Est total overhead', 'deadline hit rate', 'total iterations']
    df = pd.DataFrame(columns=columns)

    for i, pn in enumerate(process_names):
        latencies = process_wm_latencies[i]
        if len(latencies) == 0 or total_calls[i] == 0:
            continue

        latencies_arr = np.asarray(latencies)
        mean_overhead = np.average(latencies_arr)
        min_overhead = np.min(latencies_arr)
        max_overhead = np.max(latencies_arr)
        percentile5 = np.percentile(latencies_arr, 5)
        percentile25 = np.percentile(latencies_arr, 25)
        percentile75 = np.percentile(latencies_arr, 75)
        percentile95 = np.percentile(latencies_arr, 95)
        median = np.median(latencies_arr)

        est_total_overhead = mean_overhead * process_num_args[i]
        deadline_hit_rate = deadline_hits[i] / total_calls[i]
        total_iterations = total_calls[i]

        ddf = pd.DataFrame(data=[[pn, mean_overhead, min_overhead, max_overhead, percentile5, percentile25, percentile75, percentile95, median, est_total_overhead, deadline_hit_rate, total_iterations]], columns=columns)
        df = df.append(ddf)

    print(df)
    return df

def main(filename):
    with open(filename, 'r') as f:
        final_data = []
        while True:
            data = pd.DataFrame(columns=column_names)
            try:
                data = read_instrumentation_samples(f=f)
            except EOFError as e:
                raise
            except: break
            if len(data) == 0: break
            print('Lines read for trial: %d' %len(data))
            try:
                first_timestamp, process_names, process_num_args, process_wm_latencies, deadline_hits, total_calls, unprocessed_tokens = process_samples(data)
                df = analyze(process_names, process_num_args, process_wm_latencies, deadline_hits, total_calls)
                final_data.append(df)
            except: 
                print(data)
                raise

            ffilename = filename.split('.')[0] + '_'+str(first_timestamp)+'.csv'
            print('Total unprocessed tokens: %d' % unprocessed_tokens)
            df.to_csv(ffilename)
            print('======\n\n\n\nNext iteration\n\n\n\n======\n')
         



if __name__ == "__main__":
    args = sys.argv
    if len(args) > 1:
        filename = args[1]
    else: filename = 'CAV_instrument_test.log'
    main(filename)

