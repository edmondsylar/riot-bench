# Copyright 2021 Carnegie Mellon University
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import sys
import os

sys.path.insert(0, os.path.abspath('./tt'))

import Network
from Token import TTToken
from Time import TTTime, TTClock

root_clock = TTClock.root()
time_0 = TTTime(root_clock, 2, 1024)
time_1 = TTTime(root_clock, 1, 1023)
time_2 = TTTime(root_clock, 3, 1025)

tokenA = TTToken(value="I'm token A! This is my value", time=time_0)
tokenB = TTToken(value="I'm token B! This is my value", time=time_1)
tokenC = TTToken(value="I'm token C! This is my value", time=time_2)

network = Network.TTNetwork(port=8080)

tokenAMsg = Network.message(tokenA, Network.TTMessageType.InputToken, recipient_ip="127.0.0.1", recipient_port=3030)
tokenBMsg = Network.message(tokenB, Network.TTMessageType.InputToken, recipient_ip="127.0.0.1", recipient_port=3030)
tokenCMsg = Network.message(tokenC, Network.TTMessageType.InputToken, recipient_ip="127.0.0.1", recipient_port=3030)

print("Sending token A, ID=%s, value=%s" % (id(tokenA), tokenA.value))
network.send(tokenAMsg)

print("Sending token B, ID=%s, value=%s" % (id(tokenB), tokenB.value))
network.send(tokenBMsg)

print("Sending token C, ID=%s, value=%s" % (id(tokenC), tokenC.value))
network.send(tokenCMsg)