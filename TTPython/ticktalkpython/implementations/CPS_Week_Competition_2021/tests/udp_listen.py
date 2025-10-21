import sys
import os
import pickle

sys.path.insert(0, os.path.abspath('..'))



import Tag
import Token
from Network import TTNetwork, TTMessageType

def done(msg):  
    if(msg.message_type == TTMessageType.InputToken):
        token = pickle.loads(msg.payload)
        print(token.value)

network = TTNetwork(port=3030, msg_receiver=done)
