from SQ import GRAPHify

single = 0
multi_read = 1
multi_write = 2
multi_across = 3


def single_use():
    global single
    single += 1
    return single


def multi_r_1():
    global multi_read
    return multi_read + 3


def multi_r_2():
    global multi_read
    return multi_read + 4


def multi_w_1(trigger):
    global multi_write
    global multi_across
    multi_write += 3
    multi_write = multi_write + multi_across
    return multi_write


def multi_w_2_no_wr(trigger):
    global multi_write
    return multi_write


@GRAPHify
def main(trigger):
    x = multi_w_1(trigger)
    y = multi_w_2_no_wr(x)
