import sys
import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

# a list of types the tracker could track
EVENT = 0
FUNCTION = 1
RETURNVALUE = 2
SELFCALLVALUE = 3  # call value attached to the function call
CALLVALUE = 4 # call value attached to an external function call
FALLBACK = 5 # call value attached to a fallback function call

# physical meaning
DEPOSIT = 99
INVEST = 100
WITHDRAW = 101
TRANSFER = 102

# # Special address
# MSGSENDER = 555
# TXORIGIN = 556


# class locator marks a list of locations which could be manipulated 
class locator:
    def __init__(self, targetFunc, type, *, name = None, funcPara = [], \
                 funcAddress = None, position = None, returnValuePosition = None, \
                 fromAddr = None): 
        '''funcPara means the value of function's another parameter'''
        self.type = type
        self.targetFunc = targetFunc
        self.fromAddr = fromAddr
        if type == FUNCTION:
            self.funcName = name
            self.argPosition = position
            self.funcPara = funcPara
            self.funcAddress = funcAddress
        elif type == EVENT:
            self.eventName = name
            self.eventPosition = position
        elif type == RETURNVALUE:
            self.returnValuePosition = returnValuePosition
        elif type == SELFCALLVALUE:
            pass
        elif type == CALLVALUE:
            self.funcAddress = funcAddress
            pass
        elif type == FALLBACK:
            pass
        self.kind = None


    def isTrackedDeeper(self):
        if self.type == FUNCTION:
            return True
        else:
            return False
        


if __name__ == "__main__":
    l1 = locator("func1", FUNCTION, funcPara = (1, "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"), position=2)
    l2 = locator("event1", EVENT, position=1)

