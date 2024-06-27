import sys
import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))
from trackerPackage.dataSource import *
from trackerPackage.stackTracker import *

class memoryTracker:
    """It represents some memory locations where some data source is stored"""
    def __init__(self):
        self.memoryMap = []

    def find(self, name: str):
        for (start, end, dataSrcInfo) in self.memoryMap:
            if dataSrcInfo.find(name):
                return True
        return False
    
    def overwriteStackEntry(self, start, end, entry: stackEntry):
        self.overwriteInterval(start, end, dataSource())
        if end - start != entry.length:
            entry.shiftInterval( -1 * (entry.length - (end - start)) )
            # sys.exit("memoryTracker Error: stack entry length does not match {} and {}".format(end - start, entry.length))
        for dataSrcInfo in entry.dataSrcMap:
            self.addInterval(start + dataSrcInfo[0], start + dataSrcInfo[1], dataSrcInfo[2])
            
    def addInterval(self, start, end, dataSrcInfo: dataSource):
        self.memoryMap.append([start, end, dataSrcInfo])

    def overwriteInterval(self, start, end, dataSrcInfo: dataSource):
        # if start < 324 + 100 and end > 324:
        #     print("now is the time")

        # interval is of shape (start, end, {data source info})
        hasIt = False
        for ii in range(len(self.memoryMap)):
            item = self.memoryMap[ii]
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
                    item[0] = start
                    item[1] = end
                    item[2] = dataSrcInfo
                    hasIt = True
                else:
                    item[0] = None
            elif start <= item[0] and end < item[1]:
                item[0] = end
            elif start > item[0] and end >= item[1]:
                item[1] = start
            elif start > item[0] and end < item[1]:
                # split the existing interval
                self.memoryMap.append([end, item[1], item[2]])
                item[1] = start
        if not hasIt:
            self.memoryMap.append([start, end, dataSrcInfo])

        # remove all items whose start is None
        self.memoryMap = [item for item in self.memoryMap if item[0] is not None]

    def getInterval(self, start, end):
        dataSrcInfo = dataSource()
        for item in self.memoryMap:
            # check if overlapping
            if item[1] <= start:
                continue
            elif item[0] >= end:
                continue
            else:
                # overlapping
                dataSrcInfo.merge(item[2])
        return dataSrcInfo
    
    def getIntervalDetails(self, start, end):
        dataSrcVec = [] # a list of data sources
        for item in self.memoryMap:
            # check if overlapping
            if item[1] <= start:
                continue
            elif item[0] >= end:
                continue
            else:
                # overlapping
                dataSrcVec.append( (item[0] - start, item[1] - start, item[2]) )
        return dataSrcVec


        
    def __str__(self) -> str:
        return str(self.memoryMap)

