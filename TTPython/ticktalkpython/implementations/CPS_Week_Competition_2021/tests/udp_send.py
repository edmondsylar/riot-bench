import sys
import os

sys.path.insert(0, os.path.abspath('..'))

import Network
import Tag
import Token
import time
file = open("./time_instrument.py")
contents = file.read()
file.close()

tokenA = Token.Token(Tag.Tag("foo", 'arg1', 0, 100), "I'm token A!")
tokenB = Token.Token(Tag.Tag("foo", 'arg1', 100, 200), "I'm token B! This is my value")
tokenC = Token.Token(Tag.Tag("foo", 'arg2', 100, 200), "I'm token C! This is my value")

network = Network.TTNetwork(port=3031)

tokenAMsg = Network.message(tokenA, Network.TTMessageType.InputToken, recipient_port=3030)
tokenBMsg = Network.message(tokenB, Network.TTMessageType.InputToken, recipient_port=3030)
tokenCMsg = Network.message(tokenC, Network.TTMessageType.InputToken, recipient_port=3030)
send_num = 0

while(True):
    tokenAMsg = Network.message(tokenA, Network.TTMessageType.InputToken, recipient_port=3030)
    print("%s: Sending token A, ID=%s, value=%s" % (send_num, id(tokenA), tokenA.value))
    network.send(tokenAMsg)
    send_num += 1
    time.sleep(1/2)

#print("Sending token B, ID=%s, value=%s" % (id(tokenB), tokenB.value))
#network.send(tokenBMsg)

#print("Sending token C, ID=%s, value=%s" % (id(tokenC), tokenC.value))
#network.send(tokenCMsg)