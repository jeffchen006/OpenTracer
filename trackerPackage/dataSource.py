import sys
import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))
import copy


# we have to keep an record of which bytes correspond to dataSource
class dataSource:
    """It represents some end points data source"""
    def __init__(self, d: dict = None, opcode = None):
        self.sources = []
        self.children = [] 
        self.metaData = {}
        if d is not None:
            self.sources.append(d)
            self.children.append(None)
        if opcode is not None:
            self.sources.append(opcode)
            self.children.append(None)

    def find(self, name: str):
        for source in self.sources:
            if isinstance(source, dict):
                if "name" in source.keys() and source["name"] == name:
                    return True
            elif isinstance(source, str):
                if source == name:
                    return True
            elif isinstance(source, tuple):
                for jj in range(len(source)):
                    if source[jj] == name:
                        return True
        return
    
    def remove(self, name: str):
        for ii in range(len(self.sources)):
            if not isinstance(self.sources[ii], str):
                continue
            elif self.sources[ii] == name:
                self.sources.pop(ii)
                self.children.pop(ii)
                return
        

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
            if isinstance(endPoints[ii], tuple):
                if endPoints[ii][0] == "msg.data":
                    string += "msg.data+" + str(endPoints[ii][1]) + "-" + str(endPoints[ii][2])
                elif endPoints[ii][1] == "SLOAD":
                    key = endPoints[ii][2]                    
                    if endPoints[ii][2][0:2] == "0x":
                        string += "SLOAD+" + str(endPoints[ii][2][-8:])
                    else:
                        string += "SLOAD+" + str(endPoints[ii][2])
                elif endPoints[ii][1] == "Mapping":
                    string += "SLOAD+(Mapping" + str(endPoints[ii][2][-4:]) + "[" + str(endPoints[ii][3]) + "]" + ('+' if endPoints[ii][4] >= 0 else '') + str(endPoints[ii][4]) + ")"
                elif endPoints[ii][0] == "PC" or endPoints[ii][0] == "TIMESTAMP" or endPoints[ii][0] == "CALLER" or endPoints[ii][0] == "ORIGIN" or \
                    endPoints[ii][0] == "RETURNDATASIZE" or endPoints[ii][0] == "ADDRESS" or endPoints[ii][0] == "GAS" or endPoints[ii][0] == "CALLDATASIZE" or \
                    endPoints[ii][0] == "SELFBALANCE" or endPoints[ii][0] == "CALLVALUE" or endPoints[ii][0] == "NUMBER" or endPoints[ii][0] == "BALANCE":
                    string += endPoints[ii][0]
                elif endPoints[ii][0] == "SHA3-64":
                    string += endPoints[ii][0] + "-" + endPoints[ii][1][-4:]
                elif endPoints[ii][0] == "SHA3":
                    string += endPoints[ii][0] 
                elif endPoints[ii][0] == "address(this).code":
                    string += endPoints[ii][0] + "[{}:{}]".format(endPoints[ii][1], endPoints[ii][2])
                else:
                    print(endPoints[ii])
                    sys.exit("dataSource: Error: unknown tuple type")
            elif isinstance(endPoints[ii], dict):
                string += str(endPoints[ii]["name"]) + "(" + str(endPoints[ii]["inputs"]) + ")"

            else:
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