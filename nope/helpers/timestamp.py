from time import time


def get_timestamp():
    """ Retruns a Timestamp in [ms]"""
    return int(time()*1000)
