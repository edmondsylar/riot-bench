# Copyright 2021 Carnegie Mellon University
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# 

import sys, os

sys.path.insert(0, os.path.abspath('..'))
sys.path.insert(0, os.path.abspath('../tt/'))
sys.path.insert(0, os.path.abspath('./tt/'))

import Clock
import Time
import Tag
import Token
from Compiler import TTCompile
from SQSync import TTSQSync
from SQExecute import TTSQExecute


def test_clock_spec():
    try: 
        root = Clock.TTClock.root()
        child = Clock.TTClock('child', root, 10, 0)
        clocks = [root, child]

        child_spec = Clock.TTClockSpec.fromClock(child)
        root_spec = Clock.TTClockSpec.fromClock(root)

        child_clock_found = child_spec.toClock(clocks)
    
    except: 
        raise AssertionError('Testing TTClockSpec failed')


def test_time_spec():

    try:
        root = Clock.TTClock.root()
        child = Clock.TTClock('child', root, 10, 0)
        clocks = [root, child]

        child_spec = Clock.TTClockSpec.fromClock(child)
        root_spec = Clock.TTClockSpec.fromClock(root)

        time = Time.TTTime(child, 0, 100)
        time_root = Time.TTTime(root, 0, 1000)

        time_spec_direct = Time.TTTimeSpec(child_spec, 0, 100, 'ensemble-1')
        time_spec_converted = Time.TTTimeSpec.fromTime(time)

        time_unspec_direct = time_spec_direct.toTime(clock_list=clocks)
        time_unspec_converted = time_spec_converted.toTime(clock_list=clocks)

        assert time == time_unspec_direct, 'conversion between time spec and time failed (direct)'
        assert time == time_unspec_converted, 'conversion between time spec and time failed (converted)'

        time_unspec_converted_root = time_unspec_converted.ancestor_time(root)

        assert time_root == time_unspec_converted_root, 'conversion from converted time spec to root domain failed'
        
    except AssertionError: raise
    except:
        raise AssertionError('Testing TTTimeSpec failed')

from tests.test import all_tests, token_processing

def test_sq_spec():

    graph = TTCompile("quadratic", printAST=False, showGraph=False)
    sq = graph.sqList[0]
    json_spec = sq.json()

    sync_spec = json_spec['sync']
    sq_sync = TTSQSync.from_json(sync_spec)

    execute_spec = json_spec['execute']
    sq_execute = TTSQExecute.from_json(execute_spec)

def test_reference_free_tokens():

    root_clock_spec = Clock.TTClockSpec('root')
    time_spec = Time.TTTimeSpec(root_clock_spec, 0, 10)

    token = Token.TTToken(0xdeadbeef, time_spec)
    print(token)


def main():

    test_clock_spec()
    test_time_spec()
    test_sq_spec()
    test_reference_free_tokens()


if __name__ == "__main__":
    main()