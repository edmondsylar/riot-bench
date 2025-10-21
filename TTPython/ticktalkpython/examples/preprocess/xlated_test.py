from SQ import GRAPHify


def single_use():
    global sq_state
    if sq_state.get('single', None) == None:
        sq_state['single'] = 0

    sq_state['single'] += 1


def multi_r_1():
    global sq_state
    if sq_state.get('multi_read', None) == None:
        sq_state['multi_read'] = 1

    return sq_state['multi_read'] + 3


def multi_r_2():
    global sq_state
    if sq_state.get('multi_read', None) == None:
        sq_state['multi_read'] = 1

    return sq_state['multi_read'] + 4


def multi_w_1(trigger):
    global sq_state
    if sq_state.get('multi_write', None) == None:
        sq_state['multi_write'] = 2
    if sq_state.get('multi_across', None) == None:
        sq_state['multi_across'] = 3

    sq_state['multi_write'] += 3
    sq_state[
        'multi_write'] = sq_state['multi_write'] + sq_state['multi_across']
    return sq_state['multi_write']


def multi_w_2_no_wr(trigger, multi_write):
    return multi_write


@GRAPHify
def main(trigger):
    x = multi_w_1(trigger)
    y = multi_w_2_no_wr(x)
