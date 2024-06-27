import sys
import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))



class dataSource:
    """It represents some end points data source"""
    def __init__(self, d: dict = None, opcode: str = None):
        self.sources = []
        self.children = [] 
        self.metaData = {}
        if d is not None:
            self.sources.append(d)
            self.children.append(None)
        if opcode is not None:
            self.sources.append(opcode)
            self.children.append(None)

    def to_dict(self):
        children = [child.to_dict() if child is not None else None for child in self.children]
        return {"sources": self.sources, "children": children, "metaData": self.metaData}

    def addChild(self, child):
        self.children.append(child)

    def isEmpty(self):
        return len(self.sources) == 0

    def addFunc(self, d: dict, child = None):
        isEqual = False
        for item in self.sources:
            if item == d:
                isEqual = True
                break
        if not isEqual:
            self.sources.append(d)
            self.children.append(child)

    def addOpcode(self, opcode: str, child = None):
        if opcode not in self.sources:
            self.sources.append(opcode)
            self.children.append(child)
    
    def merge(self, other):
        for ii in range(len(other.sources)):
            source = other.sources[ii]
            child = other.children[ii]
            if isinstance(source, dict):
                self.addFunc(source, child)
            else:
                self.addOpcode(source, child)

    def endPoints(self) -> list:
        endPoints = []
        for ii in range(len(self.sources)):
            source = self.sources[ii]
            if self.children[ii] == None:
                endPoints.append(source)
            else:
                endPoints += self.children[ii].endPoints()
        return endPoints

    def __str__(self) -> str:
        string = "["
        endPoints = self.endPoints()
        for ii in range(len(endPoints)):
            if ii != 0:
                string += ", "
            string += str(endPoints[ii])
        string += "]"
        return string


def getEndPoints(dataS: dict):
    endPoints = []
    for ii in range(len(dataS["sources"])):
        source = dataS["sources"][ii]
        if dataS["children"][ii] == None:
            endPoints.append(source)
        else:
            endPoints += getEndPoints(dataS["children"][ii])
    return endPoints