from rich import print
from rich.pretty import pprint
from enum import IntEnum

class LOG_LEVELS(IntEnum):
    BASIC = 0
    SIMPLE = 1
    COMPLEX = 2

logLevel = LOG_LEVELS.BASIC
def setLogLevel(level: LOG_LEVELS):
    global logLevel
    logLevel = level

def log(msg, level = LOG_LEVELS.BASIC, prettyPrint = False, end= "\n", **options):
    if logLevel >= level:
        if prettyPrint:
            pprint(msg, **options)
        else:
            print(msg, end=end)