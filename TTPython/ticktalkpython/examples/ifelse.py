## Example streamify
from Deadline import TTFinishByOtherwise
from Instructions import READ_TTCLOCK
from SQ import STREAMify, GRAPHify
from Instructions import *

def bar(a, b):
    return a*b

def callback(x):
  if x % 2 == 1:
    return 1
  return 0

@SQify
def timed_add1(x):
  import time
  time.sleep(0.1)
  return x + 1

@SQify
def const_val():
  return 0

@GRAPHify
def ifelse(trigger):
  a = 1
  # b = 2
  # c = 3
  # with TTClock('ROOT', None, 1, 0) as root_clock:
  with TTClock('ROOT') as root_clock:
      #start node foo; need to attach timing information?
      # y = a == b < c
      # z = a if True else 10
      # return z
      t = READ_TTCLOCK(trigger, TTClock=root_clock) + 500
      y = timed_add1(a)
      q = TTFinishByOtherwise(y, TTTimeDeadline=t, TTPlanB=const_val(), TTWillContinue=True) #if deadline fails, it produces a separate value (similar to ternary operation: a = y if clock.now < t else None)
      # x = a + b + 10 if a == b else b + c + 50
      return q
