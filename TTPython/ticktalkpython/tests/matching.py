# Copyright 2021 Carnegie Mellon University
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.# TTPython
#
# Framework for formally defining the TickTalk core language concepts
# as extensions to Python 3.x
#
# Created by Bob Iannucci 2021
#
import sys, os

sys.path.insert(0, os.path.abspath('..'))
sys.path.insert(0, os.path.abspath('../tt/'))
sys.path.insert(0, os.path.abspath('./tt/'))

from Time import TTTime
from Clock import TTClock
from Token import TTToken
from SQ import *
from SQSync import *
from FiringRule import TTFiringRuleType

# TODO: doesn't work anymore
def match_game():
    token_storage = TTSQInputTokenStorage(2, TTFiringRuleType.Timed, 'Test-SQ-0')            # Allocate a TokenStorage instance for a 2-port SQ
    root_clock = TTClock.root()                         # Conjure up the root clock
    time1_root = TTTime(root_clock, 0, 2)               # Create a timestamp
    time2_root = TTTime(root_clock, 1, 3)               # Create a timestamp
    token1 = TTToken(1, time1_root)                     # Create two different but identically-timed tokens
    token2 = TTToken(2, time2_root)
    token_storage.addTokenOnPort(token1, 0)             # Queue up a token on port 0
    overlap_time, token_list = token_storage.matchTokenOnPort(token2, 1)    # See if it matches the queued token
    assert(overlap_time.start_tick == 1)
    assert(overlap_time.stop_tick == 2)
    assert(token_list[0] == token1)
    assert(token_list[1] == token2)

    other_clock = TTClock("other clock", root_clock, 3, 19)
    time3_other = TTTime(other_clock, 0, 1)
    token3 = TTToken(17, time3_other, streaming=True)   # IMPORTANT: mark this as having come from a streaming source
    token_storage2 = TTSQInputTokenStorage(2, TTFiringRuleType.Timed)
    token_storage2.addTokenOnPort(token1, 1)
    try:
        overlap_time, token_list = token_storage2.matchTokenOnPort(token3, 0)   # Should flag a clock mismatch error
        raise Exception("UntriggeredError", "Illegal token matching should have triggered an error but did not")
    except Exception as error:
        type, description = error.args
        assert(type == "WaitingMatchingError")

def all_tests():
    match_game()
    # Will only get here if there are no assertion failures
    print("All token matching tests PASSED")

if __name__ == "__main__":
    all_tests()
