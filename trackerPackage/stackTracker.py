import sys
import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))
from trackerPackage.dataSource import *
import copy
from itertools import groupby


class stackEntry:
    def __init__(self, length = 0, dataSrcOrdataSrcVec = None) -> None:
        self.dataSrcMap = []
        self.length = length # data length in bytes
        if dataSrcOrdataSrcVec is None:
            return
        elif isinstance(dataSrcOrdataSrcVec, dataSource):
            self.dataSrcMap = [[0, length, dataSrcOrdataSrcVec]]
        elif isinstance(dataSrcOrdataSrcVec, list):
            self.dataSrcMap = copy.deepcopy(dataSrcOrdataSrcVec)
        else:
            sys.exit("stackEntry Error: dataSrcOrdataSrcVec is neither a dataSource nor a list")
    
    def gc(self):
        sources = []
        for ii in reversed(range(len(self.dataSrcMap))):
            if self.dataSrcMap[ii][2].isEmpty():
                del self.dataSrcMap[ii]
        
        


    def mergeList(self, dataSrcVec: list):
        for item in dataSrcVec:
            self.addInterval(item[0], item[1], item[2])
        self.gc()

    def merge(self, other):
        # merge other into self
        for item in other.dataSrcMap:
            self.addInterval(item[0], item[1], item[2])
        self.gc()

    def addInterval(self, start, end, dataSrcInfo: dataSource):
        for i_start, i_end, i_dataSrcInfo in self.dataSrcMap:
            if i_start == start and i_end == end:
                i_dataSrcInfo.merge(dataSrcInfo)
                return
        self.dataSrcMap.append((start, end, dataSrcInfo))
        self.gc()


    def overwriteInterval(self, start, end, dataSrcInfo: dataSource):
        hasIt = False
        for ii in range(len(self.dataSrcMap)):
            item = self.dataSrcMap[ii]
            # no overlapping
            if item[1] <= start:
                continue
            elif item[0] >= end:
                continue
            # overlapping
            if start <= item[0] and end >= item[1]:
                # new interval is larger than the existing interval
                # remove the existing interval
                if not hasIt:
                    self.dataSrcMap[ii] = (start, end, dataSrcInfo)
                    hasIt = True
                else:
                    self.dataSrcMap[ii] = (None, item[1], item[2])
            elif start <= item[0] and end < item[1]:
                self.dataSrcMap[ii] = (end, item[1], item[2])
            elif start > item[0] and end >= item[1]:
                self.dataSrcMap[ii] = (item[0], start, item[2])
            elif start > item[0] and end < item[1]:
                # split the existing interval
                self.dataSrcMap.append([end, item[1], item[2]])
                self.dataSrcMap[ii] = (item[0], start, item[2])
        if not hasIt:
            self.dataSrcMap.append((start, end, dataSrcInfo))

        # remove all items whose start is None
        self.dataSrcMap = [item for item in self.dataSrcMap if item[0] is not None]
        self.gc()


    def getInterval(self, start = -1, end = 99999999):
        dataSrcInfo = dataSource()
        for item in self.dataSrcMap:
            # check if overlapping
            if item[1] <= start:
                continue
            elif item[0] >= end:
                continue
            else:
                # overlapping
                dataSrcInfo.merge(item[2])
        return dataSrcInfo
    
    def removeInterval(self, start, end):
        self.overwriteInterval(start, end, dataSource())
        self.gc()


    def shiftInterval(self, shift):
        # shift <0 means shift to the left
        # shift >0 means shift to the right
        index2remove = []
        for ii in range(len(self.dataSrcMap)):
            item = self.dataSrcMap[ii]
            new_start = min(max(0, item[0] + shift), 32)
            new_end = min(max(0, item[1] + shift), 32)
            if new_start == 0 and new_end == 0:
                index2remove.append(ii)
            elif new_start == 32 and new_end == 32:
                index2remove.append(ii)
            else:
                self.dataSrcMap[ii] = (new_start, new_end, item[2])

        # remove all items with index in index2remove from self.dataSrcMap
        for ii in reversed(index2remove):
            del self.dataSrcMap[ii]
        self.gc()


    def __str__(self) -> str:
        string = "["
        for ii, item in enumerate(self.dataSrcMap):
            if ii != 0:
                string += ", "
            string += "[{}, {}, {}]".format(item[0], item[1], str(item[2]) )
        string += "]"
        self.dataSrcMap = [list(x) for x in {(tuple(e)) for e in self.dataSrcMap }]
        return string
        







class stackTracker:
    def __init__(self, oldStack = []) -> None:
        self.stack = oldStack.copy()

    def find(self, dataSrcInfo: dataSource):
        # find the data source in the stack
        for i in range(len(self.stack)):
            for (start, end, item) in self.stack[i].dataSrcMap:
                if item == dataSrcInfo:
                    return i
        return -1

    def __str__(self) -> str:
        return str(self.stack)

    def swap(self, n: int):
        # swap the last element with the element at index - n - 1
        if not len(self.stack) >= n + 1:
            sys.exit("Tracker Error: swap() called with n = {} but stack length is {}".format(n, len(self.stack)))
        if n == 0:
            pass
        else:
            self.stack[-1], self.stack[-n-1] = self.stack[-n-1], self.stack[-1]

    def dup(self, n: int):
        # n = 1: duplicate the last element
        # n = 2: duplicate the second last element
        # n = 3: duplicate the third last element
        if not len(self.stack) >= 1:
            sys.exit("Tracker Error: dup() called with n = {} but stack length is {}".format(n, len(self.stack)))
        if n == 0:
            pass
        else:
            self.stack.append( copy.deepcopy(self.stack[-n]) )

    def push(self, n: stackEntry):
        # push n to the stack
        # TODO
        self.stack += [n]

    def pop(self, n: int):
        # pop the last n elements
        if not len(self.stack) >= n:
            sys.exit("Tracker Error: pop() called with n = {} but stack length is {}".format(n, len(self.stack)))
        if n == 0:
            pass
        elif n == 1:
            last = self.stack[-1]
            self.stack = self.stack[:-1]
            if self.stack:
                return last
        else:
            self.stack = self.stack[:-n]


    def merge_last_n(self, n: int, length: int):
        # Check if the stack is empty or if n is 0 or negative
        if not self.stack or n <= 0:
            return self.stack

        if not len(self.stack) >= n:
            sys.exit("Tracker Error: merge_last_n() called with n = {} but stack length is {}".format(n, len(self.stack)))
        # Create a new stack to store the result
        result_stack = []

        # Loop through the elements in the stack, skipping the last n elements
        for i in range(len(self.stack) - n):
            result_stack.append( copy.deepcopy(self.stack[i]) )

        # Merge the last n elements in the original stack
        merged_entry = stackEntry()
        merged_entry.length = length
        for i in range(len(self.stack) - n, len(self.stack)):
            merged_entry.merge(self.stack[i])
            if isinstance(self.stack[i], set):
                sys.exit("Tracker Error: merge_last_n() called with set")
            elif isinstance(self.stack[i], dict):
                sys.exit("Tracker Error: merge_last_n() called with dict")
            

        result_stack.append(merged_entry)

        self.stack = result_stack

