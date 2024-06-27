import sys
import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))
from trackerPackage.dataSource import *

class storageTracker():
    """It represents some storage locations where some data source is stored"""
    # sstore only writes a single word, 32 bytes
    # sload only reads a single word, 32 bytes
    def __init__(self):
        self.storageMap = []

    def store(self, start, dataSrcInfo):
        # store the data source info at the start location
        self.storageMap.append([start, start + 32, dataSrcInfo])
    
    def read(self, start):
        # read the data source info at the start location
        dataSrcInfo = dataSource()
        for item in self.storageMap:
            if item[1] <= start:
                continue
            elif item[0] >= start + 32:
                continue
            else:
                dataSrcInfo.merge(item[2])
        return dataSrcInfo

    def readDetails(self, start):
        dataSrcVec = []
        for item in self.storageMap:
            if item[1] <= start:
                continue
            elif item[0] >= start + 32:
                continue
            else:
                dataSrcVec.append( (item[0] - start, item[1] - start, item[2]) )
        return dataSrcVec
    
            

