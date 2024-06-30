import sys
import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))
import json
from trackerPackage.tracker import tracker
from crawlPackage.crawlEtherscan import CrawlEtherscan
from parserPackage.decoder import decoder

def dict2TraceTree(dict):
    return TraceTree().from_dict(dict)


class TraceTree:
    def __init__(self, info: dict = {}) -> None:
        self.info = info
        self.internalCalls = []
        self.address2addressesMap = {}


    def __str__(self) -> str:
        # print both info and internalCalls
        return self.visualize()

    def visualize(self, indent=0):
        returnStr = ""
        returnStr += (' ' * indent + str(self.info) + "\n")
        for child in self.internalCalls:
            returnStr += child.visualize(indent + 2)
        return returnStr
    
    def visualizeASE(self, indent=0):

        returnStr = ""
        if "meta" in self.info:
            reverted = ""
            if "status" in self.info and self.info["status"] == "reverted":
                reverted = "{Transaction Reverted!}"
            returnStr += "[Meta Info] " + reverted + " TxHash: " + self.info["txHash"] + "   tx.origin: " + self.info["origin"] + "\n"
            pass
        else:
            typeStr = self.info["type"] if "type" in self.info else ""
            if typeStr == "firstCall":
                typeStr = "call"
            typeStr = typeStr.upper()
            returnStr += '  ' * indent + "[" + typeStr + "] "
            if "gas" in self.info and "msg.value" in self.info:
                gas = self.info["gas"]
                if isinstance(gas, str):
                    gas = int(gas, 16)

                value = self.info["msg.value"]
                if isinstance(value, str):
                    value = int(value, 16)
                formattedValue = format(value, ".2e")
                returnStr += "{ gas:" + str(gas) + ", value:" + formattedValue +" } "

            elif "gas" in self.info:    
                gas = self.info["gas"]
                if isinstance(gas, str):
                    gas = int(gas, 16)
                returnStr += "{ gas:" + str(gas) + " } "

            elif "msg.value" in self.info:
                value = self.info["msg.value"]
                if isinstance(value, str):
                    value = int(value, 16)
                formattedValue = format(value, ".2e")

                returnStr += "{ value:" + formattedValue + " } "
            
            returnStr += str(self.info["addr"]) 
            if "name" in self.info:
                returnStr += "." + self.info["name"]
            elif "Selector" in self.info:
                returnStr += "." + self.info["Selector"]
            else:
                returnStr += ""

            calldata = ""
            if "Raw calldata" in self.info:
                calldata = self.info["Raw calldata"]
            elif "calldata" in self.info:
                calldata = self.info["calldata"]

            # # remove the leading 0s
            # calldata = calldata.lstrip("0")
            # remove selector from calldata
            calldata = calldata[8:]
            # remove the leading 0s
            calldata = calldata.lstrip("0")
            # if calldata is too long, we should truncate it and use ... to omit the details
            if len(calldata) > 8:
                calldata = calldata[:4] + "..." + calldata[-4:]

            returnvalue = ""
            if "Raw returnvalue" in self.info:
                returnvalue = self.info["Raw returnvalue"]
                # remove the leading 0s from returnvalue
                returnvalue = returnvalue.lstrip("0")
                if len(returnvalue) > 8:
                    returnvalue = returnvalue[:4] + "..." + returnvalue[-4:]
            if returnvalue == "":
                returnvalue = "None"

            returnStr += "({}) -> {}".format(calldata, returnvalue) + "\n"


            # next add sload and sstore
            if "sload/sstore" in self.info:
                for ret in self.info["sload/sstore"]:
                    opcode = ret[0]
                    if ret[0] == "sload":
                        slot = ret[1]
                        value = ret[2]
                    elif ret[0] == "sstore":
                        slot = ret[1]
                        value = ret[2]
                    else:
                        sys.exit("TraceTree: Error: unknown opcode besides sload and sstore")
                    
                    returnStr += '  ' * (indent + 1) + "[{}] {}: {}\n".format(opcode, slot, value)

                
            
            
        for child in self.internalCalls:
            returnStr += child.visualizeASE(indent + 2)
        return returnStr
        

    def simpleVisualize(self, addresses = [], indent=0):
        returnStr = ""
        if "meta" in self.info:
            pass
        else:
            if self.info["addr"] in addresses:
                returnStr += '  ' * indent + "\033[31m" + str(self.info["addr"]) + "\033[0m"
            else:
                if  "type" in self.info and self.info["type"] == "delegatecall":
                    returnStr += '  ' * indent +  "\033[34m" + str(self.info["addr"]) + "\033[0m"
                else:
                    returnStr += '  ' * indent +  str(self.info["addr"]) 
            if "name" in self.info:
                returnStr += "." + self.info["name"] + "\n"
            elif "Selector" in self.info:
                returnStr += "." + self.info["Selector"] + "\n"
            else:
                returnStr += "\n"
        for child in self.internalCalls:
            returnStr += child.simpleVisualize(addresses, indent + 2)
        return returnStr
    

    def simpleAnalyze(self, contracts):
        contract2contractMap = {}
        for contract in contracts:
            contract2contractMap[contract] = self._simpleAnalyze(contract, contracts)
        return contract2contractMap


    def _simpleAnalyze(self, targetAddress, childAddresses):
        if "addr" in self.info and self.info["addr"] == targetAddress and \
            "type" in self.info and self.info["type"] != "staticcall":
            invokedChildAddresses = []
            for childAddress in childAddresses:
                for child in self.internalCalls:
                    if child.isInvokeAddresses([childAddress]):
                        invokedChildAddresses.append(childAddress)
            invokedChildAddresses = list(set(invokedChildAddresses))
            return invokedChildAddresses
        else:
            invokedChildAddresses = []
            for child in self.internalCalls:
                invokedChildAddresses += child._simpleAnalyze(targetAddress, childAddresses)
                        
            return list(set(invokedChildAddresses))
        
    
    def simpleAnalyzeStorage(self, addresses): 
        storageAccessArray = []
        if 'addr' in self.info and self.info['addr'] in addresses and 'sstore' in self.info:
            for store in self.info["sstore"]:
                storageAccessArray.append(self.info["addr"] + "." + store[0])
        for child in self.internalCalls:
            storageAccessArray += child.simpleAnalyzeStorage(addresses)
        return storageAccessArray

    # eg. 'info': {'type': 'call', 'structLogsStart': 889505, 
    #               'gas': 919945, 'addr': '0x6b175474e89094c44da98b954eedeac495271d0f', 
    #               'msg.value': '0x0', 'msg.sender': '0x9c211bfa6dc329c5e757a223fb72f5481d676dc1', 
    #               'retOffset': '0x8d8', 'retLength': '0x0', 'structLogsEnd': 889829},
    #     'internalCalls': []}
    def from_dict(self, dict):
        self.info = dict['info']
        self.internalCalls = [TraceTree().from_dict(child) for child in dict['internalCalls']]
        return self
    
    def to_dict(self):
        children = [child.to_dict() for child in self.internalCalls]
        return {"info": self.info, "internalCalls": children}
    
    def to_json(self):
        # convert a TraceTree to json
        # this json is used for visualization  
        json_str = json.dumps(self.to_dict())
        return json_str

    def getAddresses(self):
        addresses = []
        if 'addr' in self.info:
            addresses.append(self.info['addr'])
        for child in self.internalCalls:
            addresses += child.getAddresses()
        return addresses
    
    def isInvokeAddresses(self, addresses):
        if self.info['addr'] in addresses:
            return True
        for child in self.internalCalls:
            if child.isInvokeAddresses(addresses):
                return True
        return False

    def filterByAddresses(self, addresses):
        # filter out all internalCalls that are not isInvokedAddresses
        self.internalCalls = [child for child in self.internalCalls if child.isInvokeAddresses(addresses)]
        for child in self.internalCalls:
            child.filterByAddresses(addresses)
        
    def updateInfo(self, dict, depth = 0, allowOverwrite = False):
        if 'name' in dict and dict['name'] == 'fallback' \
            and 'Selector' in dict and dict['Selector'] == '':
            return
        if depth == 0:
            if not allowOverwrite:
                for key in dict.keys():
                    if key in self.info and self.info[key] != dict[key]:
                        sys.exit("TraceTree: Warning: key {} is overwritten".format(key))
            if "meta" in self.info:
                # print("now is the time")
                print(dict)
            self.info.update(dict)
        elif depth == 1:
            self.internalCalls[-1].updateInfo(dict)
        else:
            self.internalCalls[-1].updateInfo(dict, depth - 1)

    def updateInfoList(self, key, value, depth = 0):
        if depth == 0:
            # if "meta" in self.info:
            #     print("now is the time")
            #     print(dict)
            if key not in self.info:
                self.info[key] = [value]
            else:
                self.info[key].append(value)
        elif depth == 1:
            self.internalCalls[-1].updateInfoList(key, value)
        else:
            self.internalCalls[-1].updateInfoList(key, value, depth - 1)

    def addInternalCall(self, newTraceTree, depth = 0):
        if depth == 0:
            # if depth is 0,
            # we should update self.info rather than add an internal call
            sys.exit("TraceTree: Depth cannot be 0")
        elif depth == 1:
            if newTraceTree.info['type'] == 'delegatecall' and \
                'msg.value' not in newTraceTree.info and 'msg.value' in self.info:
                newTraceTree.info['msg.value'] = self.info['msg.value']
            self.internalCalls.append(newTraceTree)
        else:
            self.internalCalls[-1].addInternalCall(newTraceTree, depth - 1)

    def splitTraceTree(self, contractAddress, proxyAddress = None): 
        """Given a contract, split the original trace tree into multiple trace tree"""
        splittedTraceTrees = []
        # print(self.info)
        if "meta" not in self.info and self.info['addr'].lower() == contractAddress.lower():
            if proxyAddress is None or 'type' not in self.info or self.info['type'] != 'delegatecall':
                splittedTraceTrees += [self]
            else:
                if self.info['proxy'].lower() == proxyAddress.lower():
                    splittedTraceTrees += [self]
        for child in self.internalCalls:
            splittedTraceTrees += child.splitTraceTree(contractAddress, proxyAddress)
        return splittedTraceTrees

    def cleanStaticCall(self):
        # clean all staticcalls since they don't change storage
        # clean all enteries with 'type' == 'staticcall' in internalCalls
        self.internalCalls = [child for child in self.internalCalls if child.info['type'] != 'staticcall']

    def hideUnnecessaryInfo(self):
        # hide all info except for funcSelector
        for child in self.internalCalls:
            #  remove keys 
            if "structLogsStart" in child.info:
                child.info.pop('structLogsStart')
            if "structLogsEnd" in child.info:
                child.info.pop('structLogsEnd')
            if 'retOffset' in child.info:
                child.info.pop('retOffset')
            if 'retLength' in child.info:
                child.info.pop('retLength')
            if 'gasEnd' in child.info:
                child.info.pop('gasEnd')
            child.hideUnnecessaryInfo()


    def decodeABIStorage(self, structLogs):
        if 'meta' in self.info:
            for child in self.internalCalls:
                child.decodeABIStorage(structLogs)
            return
        

        # part 1: decode ABI
        funcSelector = self.info['funcSelector'] if 'funcSelector' in self.info else ""
        if funcSelector == "" and 'Raw calldata' in self.info:
            funcSelector = "0x" + self.info['Raw calldata'][:8].lower()
        
        crawlEtherScan = CrawlEtherscan()
        funcSigMap = crawlEtherScan.Contract2funcSigMap2(self.info["addr"])


        if funcSelector in funcSigMap:
            self.info["name"] = funcSigMap[funcSelector][0]
            Ctypes = funcSigMap[funcSelector][1]

            calldata = ""
            if "Raw calldata" in self.info:
                calldata = self.info["Raw calldata"]
            elif "calldata" in self.info:
                calldata = self.info["calldata"]

            Cdecoded = decoder().decodeSimpleABI(Ctypes, calldata[8:])
            self.info["decoded calldata"] = Cdecoded

            Rtypes = funcSigMap[funcSelector][2]
            Rdecoded = decoder().decodeSimpleABI(Rtypes, self.info["Raw returnvalue"])
            self.info["decoded returnvalue"] = Rdecoded

        else:
            self.info["name"] = "fallback"
            
        

        # part 2: decode storage
        structLogsStart = None
        structLogsEnd = None
        if "type" in self.info and self.info["type"] == "firstCall":
            structLogsStart = 0
            structLogsEnd = len(structLogs)
        else:
            structLogsStart = self.info['structLogsStart']
            if structLogsStart == -1:
                structLogsStart = 0
            structLogsEnd = self.info['structLogsEnd']

        # part 2.1: collect structLogs ranges for its internal calls
        children_structLogs_ranges = []
        for child in self.internalCalls:
            children_structLogs_ranges.append((child.info['structLogsStart'], child.info['structLogsEnd']))

        depth = structLogs[structLogsStart + 1]['depth']
        aTracker = tracker(self.info["addr"])
        for ii in range(structLogsStart, structLogsEnd - 1):
            # if ii in any of the children's structLogs range, we should skip it
            skip = False
            for child_structLogs_range in children_structLogs_ranges:
                if ii >= child_structLogs_range[0] and ii <= child_structLogs_range[1]:
                    skip = True
                    break
            if skip:
                continue

            if depth == structLogs[ii]['depth'] and depth == structLogs[ii + 1]['depth']:
                aTracker.stackTrack(structLogs[ii], nextStructLog = structLogs[ii + 1], info = self.info)
        self.info["sload/sstore_decoded"] = []

        if "sload/sstore" in self.info:
            for opcode, key, value, pc, ii in self.info["sload/sstore"]:
                if key in aTracker.preimage:
                    self.info["sload/sstore_decoded"].append((opcode, [aTracker.preimage[key][1], aTracker.preimage[key][2]], value, pc, ii))
                else:
                    self.info["sload/sstore_decoded"].append((opcode, key, value, pc, ii))

        image = aTracker.preimage
        # print(image)
        
        # with this preimage, we can decode the storage and ABI
        for child in self.internalCalls:
            child.decodeABIStorage(structLogs)


    
    def visualizeASE_decoded(self, indent=0):
        returnStr = ""
        if "meta" in self.info:
            reverted = ""
            if "status" in self.info and self.info["status"] == "reverted":
                reverted = "{Transaction Reverted!}"
            returnStr += "[Meta Info] " + reverted + " TxHash: " + self.info["txHash"] + "   tx.origin: " + self.info["origin"] + "\n"
            pass
        else:
            typeStr = self.info["type"] if "type" in self.info else ""
            if typeStr == "firstCall":
                typeStr = "call"
            typeStr = typeStr.upper()
            returnStr += '  ' * indent + "[" + typeStr + "] "
            if "gas" in self.info and "msg.value" in self.info:
                gas = self.info["gas"]
                if isinstance(gas, str):
                    gas = int(gas, 16)

                value = self.info["msg.value"]
                if isinstance(value, str):
                    value = int(value, 16)
                formattedValue = format(value, ".2e")
                returnStr += "{ gas:" + str(gas) + ", value:" + formattedValue +" } "

            elif "gas" in self.info:    
                gas = self.info["gas"]
                if isinstance(gas, str):
                    gas = int(gas, 16)
                returnStr += "{ gas:" + str(gas) + " } "

            elif "msg.value" in self.info:
                value = self.info["msg.value"]
                if isinstance(value, str):
                    value = int(value, 16)
                formattedValue = format(value, ".2e")

                returnStr += "{ value:" + formattedValue + " } "
            
            returnStr += str(self.info["addr"]) 
            if "name" in self.info:
                returnStr += "." + self.info["name"]
            elif "Selector" in self.info:
                returnStr += "." + self.info["Selector"]
            else:
                returnStr += ""


            if "decoded calldata" in self.info:
                returnStr += "(" + str(self.info["decoded calldata"]) + ") -> " + str(self.info["decoded returnvalue"]) + "\n"
            else:
                calldata = ""
                if "Raw calldata" in self.info:
                    calldata = self.info["Raw calldata"]
                elif "calldata" in self.info:
                    calldata = self.info["calldata"]

                # # remove the leading 0s
                # calldata = calldata.lstrip("0")
                # remove selector from calldata
                calldata = calldata[8:]
                # remove the leading 0s
                calldata = calldata.lstrip("0")
                # if calldata is too long, we should truncate it and use ... to omit the details
                if len(calldata) > 8:
                    calldata = calldata[:4] + "..." + calldata[-4:]

                returnvalue = ""
                if "Raw returnvalue" in self.info:
                    returnvalue = self.info["Raw returnvalue"]
                    # remove the leading 0s from returnvalue
                    returnvalue = returnvalue.lstrip("0")
                    if len(returnvalue) > 8:
                        returnvalue = returnvalue[:4] + "..." + returnvalue[-4:]
                if returnvalue == "":
                    returnvalue = "None"
                returnStr += "({}) -> {}".format(calldata, returnvalue) + "\n"


            # next add sload and sstore
            if "sload/sstore_decoded" in self.info:
                for ret in self.info["sload/sstore_decoded"]:
                    opcode = ret[0]
                    if ret[0] == "sload":
                        slot = ret[1]
                        value = ret[2]
                    elif ret[0] == "sstore":
                        slot = ret[1]
                        value = ret[2]
                    else:
                        sys.exit("TraceTree: Error: unknown opcode besides sload and sstore")
                    
                    if isinstance(slot, list):
                        mapping = slot[0]
                        # truncate the leading 0s
                        mapping = mapping.lstrip("0")
                        mapping = "0x" + mapping
                        key = slot[1]
                        returnStr += '  ' * (indent + 1) + "[{}] {}[ {} ]: {}\n".format(opcode, mapping, key, value)
                    else:
                        returnStr += '  ' * (indent + 1) + "[{}] {}: {}\n".format(opcode, slot, value)

            elif "sload/sstore" in self.info:
                for ret in self.info["sload/sstore"]:
                    opcode = ret[0]
                    if ret[0] == "sload":
                        slot = ret[1]
                        value = ret[2]
                    elif ret[0] == "sstore":
                        slot = ret[1]
                        value = ret[2]
                    else:
                        sys.exit("TraceTree: Error: unknown opcode besides sload and sstore")

                    returnStr += '  ' * (indent + 1) + "[{}] {}: {}\n".format(opcode, slot, value)

        for child in self.internalCalls:
            returnStr += child.visualizeASE_decoded(indent + 2)
        return returnStr
    




if __name__ == "__main__":
    # test funcCall
    traceTree1 = TraceTree({"funcSelector": "0x0"})
    traceTree2 = TraceTree({"funcSelector": "0x1"})
    traceTree3 = TraceTree({"funcSelector": "0x2"})
    traceTree4 = TraceTree({"funcSelector": "0x3"})
    traceTree5 = TraceTree({"funcSelector": "0x4"})


    traceTree1.addInternalCall(traceTree2, 1)
    traceTree1.addInternalCall(traceTree4, 2)
    traceTree1.addInternalCall(traceTree5, 2)
    traceTree1.addInternalCall(traceTree3, 1)
    traceTree1.addInternalCall(traceTree5, 2)
    traceTree1.updateInfo({"mean": "0x5"}, 1)
    traceTree1.updateInfo({"mea342n": "0x6"}, 0)

    

    print(traceTree1)
    

    
