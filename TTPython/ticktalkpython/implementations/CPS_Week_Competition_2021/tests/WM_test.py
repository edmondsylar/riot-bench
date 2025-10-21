import sys, os, time

sys.path.insert(0, os.path.abspath('..'))

import multiprocessing, queue
import WaitingMatching
import Tag, Token
import DebugLogger, logging

DebugLogger.set_base_logger_level(logging.DEBUG)

class GenericFunctionProcess():
    #minimal wrapper; if you need state, then the function needs to be a method to the class such that self is implicitly passed, but not a part of the real function definitoin
    def __init__(self, function):
        self.input_queue = multiprocessing.Queue()
        self.function = function

        self.proc = multiprocessing.Process(target=self.listener)
        self.proc.start()

    def listener(self):
        while True:
            try:
                input_args = self.input_queue.get(block=True, timeout=1)
                args = input_args[0]
                kwargs = input_args[1]
                self.function(*args, **kwargs)
            except queue.Empty:
                continue
            except: 
                raise

class PythagFunctionProcess():
    def __init__(self):
        self.input_queue = multiprocessing.Queue()
        self.some_state = None
        self.proc = multiprocessing.Process(target=self.listener)
        self.proc.start()
        self.function = self.example_function_pythag

    def listener(self):
        while True:
            try:
                input_args = self.input_queue.get(block=True, timeout=1)
                args = input_args[0]
                kwargs = input_args[1]
                self.example_function_pythag(*args, **kwargs)
            except queue.Empty:
                continue
            except: 
                raise

    def example_function_pythag(self, a,b, time_overlap=None):
        #args will be passed as a list from the queue receiver part
        import math
        c = math.sqrt(a**2 + b**2)
        self.some_state = c #state is maintained and accessible
        #send c as a token, spawn another process, input to a queue, or otherwise. Returning is not correct!


def send_tokens_pythag(wm_proc, pythag_proc, a=3, b=4):
    print('Sending tokens for pythag example')
    now=time.time()
    tag_a = Tag.Tag('example_function_pythag', 'a', now+0, now+2) #function must match name; second argument is a postitional arg index or a argument name
    token_a = Token.Token(tag_a, 3)
    tag_b = Tag.Tag('example_function_pythag', 'b', now+1, now+3) 
    token_b = Token.Token(tag_b, 4)

    wm_proc.receiveToken(token_a)
    wm_proc.receiveToken(token_b)


def example_function_max(a, b, time_overlap=None):
    #generic function to test deadlines; input values may be None if deadline comes to pass
    mmax = -sys.maxsize
    if a != None:
        mmax = max(a, mmax)
    if b != None:
        mmax = max(b, mmax)

    print(f'a={a}, b={b}, and the max was {mmax}')
    return mmax

def send_tokens_deadline_test(wm_proc, max_func_proc, a=3):
    now = time.time()

    print('Send a series of tokens for one port, then some deadline')
    for i in range(5):
        print('Token %d' % i)
        tag_a = Tag.Tag('example_function_max', 'a', now+i*10, now+10*(i+1))
        token_a = Token.Token(tag_a, i)

        wm_proc.receiveToken(token_a)
    #Tag('function name', 'variable name', start_time, stop_time)
    tag_b = Tag.Tag('example_function_max', 'b', now+10, now+20)
    token_b = Token.Token(tag_b, 21)
    wm_proc.receiveToken(token_b)
    #when this runs, 0,10 should be evicted because it's too old


    print('send deadline token from 5')
    tag_deadline = Tag.Tag('example_function_max', 'DEADLINE', now+5, now+15)
    token_deadline = Token.Token(tag_deadline, None)
    wm_proc.receiveToken(token_deadline)
    # this should not run, because the previous tokens were evicted, and the last successful iteration is furter in the future

    print('send deadline token from 15')
    tag_deadline = Tag.Tag('example_function_max', 'DEADLINE', now+15, now+25)
    token_deadline = Token.Token(tag_deadline, None)
    wm_proc.receiveToken(token_deadline)
    # this should not run, because 10,20 already ran, and the last successful interval should indicate that 

    print('send old token (out of order), which should be removed the next time anything fires')
    tag_b = Tag.Tag('example_function_max', 'b', now+0, now+10)
    token_b = Token.Token(tag_b, 20)
    wm_proc.receiveToken(token_b)
    # This should not run, because the token that was meant for it already came to pass (was evicted earlier), and this should be evicted sometime in the future too

    print('Send deadline token from 25')
    tag_deadline = Tag.Tag('example_function_max', 'DEADLINE', now+25, now+35)
    token_deadline = Token.Token(tag_deadline, None)
    wm_proc.receiveToken(token_deadline)
    # This should cause the token for 'a' from 20,30 to be released


def pythag_test():
    pythag_fp = PythagFunctionProcess() #create function to synchronize inputs for/apply deadlines. Contains an input-queue listener function that runs the primary function on the list of arguments that arrives, some of which may be None if a deadline passed
    isf = WaitingMatching.InputSynchronizedFunction(pythag_fp.example_function_pythag, pythag_fp.input_queue) #pass function to execute (to view signature/#inputs) and input queue to the synchronizer process. It starts itself.

    send_tokens_pythag(isf, pythag_fp, 3, 4) #format tokens and send input WM section. Tokens must know the name of the fucn
    time.sleep(3) #let things settle

    isf.proc.kill()
    pythag_fp.proc.kill()

def deadline_test():
    max_fp = GenericFunctionProcess(example_function_max)
    isf = WaitingMatching.InputSynchronizedFunction(max_fp.function, max_fp.input_queue, min_overlap=1, use_deadline=True)

    send_tokens_deadline_test(isf, max_fp)

    time.sleep(60) #let all deadlines come to pass
    # isf_proc.kill()
    isf.proc.kill()
    max_fp.proc.kill()
    #finish all testing before this; KeyBoardInterrupt to exit
    isf.proc.join()

def main():
    pythag_test()
    deadline_test()

    print('All tests passed!')
    



if __name__ == "__main__":
    main()