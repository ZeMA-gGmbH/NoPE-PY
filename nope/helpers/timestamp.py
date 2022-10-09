from time import time


def getTimestamp():
    """ Retruns a Timestamp in [ms]"""
    return int(time()*1000)
