# a general parser for vmtrace
import struct
import sys
import os
import time
import json
from crawlPackage.crawlEtherscan import CrawlEtherscan
from crawlPackage.crawlQuicknode import CrawlQuickNode
from staticAnalyzer.analyzer import Analyzer
from parserPackage.decoder import decoder
from parserPackage.functions import *
from parserPackage.traceTree import TraceTree, dict2TraceTree
from trackerPackage.tracker import *
from trackerPackage.dataSource import dataSource
from parserPackage.locator import *
from utilsPackage.compressor import writeCompressedJson, readCompressedJson, writeJson, readJson
from utilsPackage.tomlHandler import changeSettings, changeLoggingUpperBound

from fetchPackage.fetchTrace import *
from web3 import Web3
import copy
import cProfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

import toml
settings = toml.load("settings.toml")





class VmtraceParserGlobal:
    def __init__(self):
        self.analyzer = Analyzer()
        self.crawlEtherscan = CrawlEtherscan()
        self.crawlQuickNode = CrawlQuickNode()
        self.indent = 0
        self.logging = 0
        ##### They four should be one struct
        self.msgSenderStack = None
        self.contractAddressStack = None
        self.isDelegateCallStack = None
        #####
        self.contractAddress = None
        self.decoder = decoder()
        self.noprint = True
        self.printAll = True and (not self.noprint)
        self.printMessageStack = self.printAll or False
        #####
        self.structLogs = None
        self.txHash = None
        self.CreateContract = False

    def printStack(self):
        if self.printMessageStack:
            print("========msgSenderStack", self.msgSenderStack)
            print("==contractAddressStack", self.contractAddressStack)
            print("===isDelegateCallStack", self.isDelegateCallStack)


    def getMsgSender(self, isDelegate: bool = False):
        if len(self.msgSenderStack) != len(self.isDelegateCallStack):
            sys.exit("Error: len(msgSenderStack) != len(isDelegateCallStack)")
        if len(self.msgSenderStack) != len(self.contractAddressStack):
            sys.exit("Error: len(msgSenderStack) != len(contractAddressStack)")

        if isDelegate:
            return self.msgSenderStack[-1]
        elif not self.isDelegateCallStack[-1]:
            return self.contractAddressStack[-1]
        else:
            for jj in range(len(self.isDelegateCallStack) - 1, -1, -1):
                if not self.isDelegateCallStack[jj]:
                    return self.contractAddressStack[jj]
        


    def parseLogsJson(self, contractAddress: str, txHash: str, jsonFile):
        """Given a json file, parse the trace and return logs"""
        trace = getTrace(jsonFile)
        return self.parseLogs(contractAddress.lower(), txHash, trace)

    def printIndentContent(self, *values: object):
        """Given an indent and a content, print the content with the indent"""
        for _ in range(self.indent - 1):
            print("\t", end = '')
        print(*values)

    def printIndentContentLogging(self, *values: object):
        """Given an indent and a content, print the content with the indent"""
        value_str = str(values)
        # if "calldata" in value_str or "sload" in value_str or "sstore" in value_str:
        #     return
        if not self.noprint:
            if self.printAll:
                for _ in range(self.indent - 1):
                    print("\t", end = '')
                print(*values)

            if not self.printAll and self.logging > 0:
                if self.contractAddress not in self.contractAddressStack:
                    sys.exit("Error! contractAddress not in contractAddressStack")

                for _ in range(self.indent - 1):
                    print("\t", end = '')
                print(*values)

    def setupGlobalState(self, txHash: str):
        receipt = self.crawlEtherscan.Tx2Receipt(txHash)
        fromAddress = receipt["from"].lower()
        if "input" not in receipt or "value" not in receipt or \
            receipt["input"] is None or receipt["value"] is None:
            receipt2 = self.crawlEtherscan.Tx2Receipt2(txHash)
            receipt.update(receipt2)


        # status = details["status"]
        input = receipt["input"]
        toAddress = receipt["to"]
        value = receipt["value"]
        status = receipt["status"]

        # global states of a transaction
        origin = fromAddress
        msgSenderStack = [fromAddress]
        contractAddressStack = None
        isDelegateCallStack = None
        if toAddress != None:
            contractAddressStack = [toAddress.lower()]
            isDelegateCallStack = [False]
        elif "contractAddress" in receipt:
            contractAddress = receipt["contractAddress"]
            contractAddressStack = [contractAddress.lower()]
            isDelegateCallStack = [False]
            self.CreateContract = True

        else:
            sys.exit("Error: toAddress is None and contractAddress is not in receipt")


        self.msgSenderStack = msgSenderStack
        self.contractAddressStack = contractAddressStack
        self.isDelegateCallStack = isDelegateCallStack

        return input, origin, value, status
    

    def decrementLogging(self):
        if self.logging > 0:
            self.logging -= 1

    def incrementLogging(self, addr: str):
        if self.logging > 0:
            self.logging += 1
        elif int(addr, 16) == int(self.contractAddress.lower(), 16):
            if self.logging != 0:
                sys.exit("Error: logging != 0")
            self.logging += 1

    def getFuncName(self, funcSigMapMap, currentContract, funcSelector):
        if len(funcSigMapMap[currentContract].keys()) == 0:
            return None
        if funcSelector != "" and funcSelector in funcSigMapMap[currentContract]:
            return funcSigMapMap[currentContract][funcSelector][0]
        else:
            return "fallback"



    def getFuncSpecs(self, funcSigMapMap, currentContract, funcSelector, calldata, memoryList = None, offset = None, length = None):
        # R represents return value
        # C represents call value
        name = None
        Ctypes = None
        Cdecoded = None

        if len(funcSigMapMap[currentContract].keys()) == 0:
            return "fallback", "None", "None", "None", "None"

        if funcSelector != "" and funcSelector in funcSigMapMap[currentContract]:
            name = funcSigMapMap[currentContract][funcSelector][0]
            Ctypes = funcSigMapMap[currentContract][funcSelector][1]
            Cdecoded = self.decoder.decodeSimpleABI(Ctypes, calldata[8:]) # remove the first 4 bytes, which is the function selector
        else:
            name = "fallback"
            Ctypes = "None"
            Cdecoded = calldata[8:]

        if memoryList == None and offset == None and length == None:
            return name, Ctypes, Cdecoded, "None", "None"

        Rtypes = None
        Rdecoded = None
        if funcSelector != "" and funcSelector in funcSigMapMap[currentContract]:
            Rtypes = funcSigMapMap[currentContract][funcSelector][2]
            Rdecoded = self.decoder.decodeReturn(Rtypes, memoryList, offset, length)
        else:
            Rtypes = "None"
            Rdecoded = self.decoder.extractMemory(memoryList, offset, length)

        return name, Ctypes, Cdecoded, Rtypes, Rdecoded


    def parseLogsGlobal(self, contractAddress: str, txHash: str, trace):
        LoggingUpperBound = settings["runtime"]["LoggingUpperBound"]
        """Given a trace, return a list of logs restricted to <contractAddress>"""
        """These logs should be ready to feed into an invariant checker"""

        self.txHash = txHash
        ce = self.crawlEtherscan

        input, origin, value, status = self.setupGlobalState(txHash)
        # funcSigMapMap = {}
        if len(self.contractAddressStack) > 0:
            contractAddress = self.contractAddressStack[-1]
            self.contractAddress = contractAddress
            # funcSigMap = self.analyzer.contract2funcSigMap(contractAddress)
            # funcSigMapMap = {contractAddress: funcSigMap}

        self.calldataStack = [{"calldata":"", "preimage":{}, "fixed": False}] # calldata of the function, a stack
        # eg. {
        #     "calldata": "0x12345678",
        #     "calldatasize": "0x12345678",
        # }

        funcSelector = "" # function selector of the function, a temp
        self.funcSelectorStack = [""] # function selector, a stack

        metaData = {"meta": True, "txHash": txHash, "origin": origin}
        metaTraceTree = TraceTree(metaData) # function calls represent what we really care
        if self.CreateContract:
            infoDict = {
                "type": "create", "structLogsStart": -1, "addr": contractAddress,
                "calldata": input
            }
            newTraceTree = TraceTree(infoDict)
            metaTraceTree.addInternalCall(newTraceTree, 1)
        else:
            infoDict = {
                "type": "firstCall", "structLogsStart": -1, "addr": contractAddress,
                "calldata": input, "msg.value": value
            }
            newTraceTree = TraceTree(infoDict)
            metaTraceTree.addInternalCall(newTraceTree, 1)

        if not isinstance(status, int):
            status = int(status, 16)
        
        if status == 0:
            metaTraceTree.info["status"] = "reverted"
            return metaTraceTree
        
        # Basically, it records a list of function calls to the <contractAddress>
        
        # eg. functionLog = {
        #   "type": "call", or "constructor", or "fallback"
        #   "from": "0x12345678",
        #   "tx.origin": "0x12345678",
        #   "msg.sender": "0x12345678",
        #   "functionSelector": "0x12345678",
        #   children: [
        #      sload 
        #      calldataread
        #      sload
        #      sstore
        #      functionLog
        #      functionLog
        #      sload
        #   ]
        # 
        # }

        self.logging = 0  # 0: not logging, >=1: logging

        if self.contractAddressStack[-1] == contractAddress:
            # means we are calling a function inside the target contract
            self.incrementLogging( self.contractAddressStack[-1] )


        self.structLogs = structLogs = trace['structLogs']
        ii = -1

        d = decoder()
        while ii < len(structLogs) - 1:
            ii += 1
            pc = structLogs[ii]["pc"]
            self.indent = structLogs[ii]["depth"]
            # if ii+1 < len(structLogs):
                # gas1 = structLogs[ii]["gas"]
                # gas2 = structLogs[ii+1]["gas"]
                # if gas2 > gas1:
                #     print("=========gas increases")

            # check if msg.value == 0 if the function is non-payable
            if ii + 7 < len(structLogs) and \
                structLogs[ii]["op"] == "PUSH1" and \
                structLogs[ii + 1]["op"] == "PUSH1" and \
                structLogs[ii + 2]["op"] == "MSTORE" and \
                structLogs[ii + 3]["op"] == "CALLVALUE" and \
                structLogs[ii + 4]["op"] == "DUP1" and \
                structLogs[ii + 5]["op"] == "ISZERO":

                ii = ii + 7
                continue


            # truncate the calldata size to get function selector
            if ii + 3 < len(structLogs) and \
                structLogs[ii]["op"] == "PUSH1" and \
                structLogs[ii + 1]["op"] == "CALLDATALOAD" and \
                structLogs[ii + 2]["op"] == "PUSH1" and \
                structLogs[ii + 3]["op"] == "SHR" and \
                len(structLogs[ii + 3]["stack"]) >= 1 and \
                structLogs[ii + 3]["stack"][-1] == "0xe0":

                currentContract = self.contractAddressStack[-1]

                ii = ii + 3
                # if self.logging > 0:
                #     # print("self.logging", self.logging)
                #     funcSigMap = funcSigMapMap[self.contractAddressStack[-1]]
                #     # print("contract key, ", self.contractAddressStack[-1])
                #     # print("funcSigMapMap keys", funcSigMapMap.keys())
                #     if len(funcSigMap.keys()) > 0 and self.logging < LoggingUpperBound:
                #         # print("funcSigMap")
                #         # print("contract key, ", self.contractAddressStack[-1])
                #         # print(funcSigMap)
                #         self.printIndentContentLogging("Function name:", funcSigMap[funcSelector][0], " ||  Function Signature:", funcSigMap[funcSelector][1], funcSigMap[funcSelector][2])
                #     else:
                #         self.printIndentContentLogging("Function name: Unknown,   Function Signature: Unknown ")

                continue

                
            # function selector comparison succeeds for Solidity
            if ii + 4 < len(structLogs) and \
                structLogs[ii]["op"] == "DUP1" and \
                structLogs[ii + 1]["op"] == "PUSH4" and \
                structLogs[ii + 2]["op"] == "EQ" and \
                "PUSH" in structLogs[ii + 3]["op"] and \
                structLogs[ii + 4]["op"] == "JUMPI" and ( \
                (
                structLogs[ii + 4]["stack"][-2] == "0x1" and \
                structLogs[ii + 5]["op"] == "JUMPDEST"
                ) or \
                (
                    structLogs[ii + 4]["stack"][-2] == "0x0" and \
                    structLogs[ii + 5]["op"] == "PUSH2" and \
                    structLogs[ii + 6]["op"] == "JUMP" and \
                    structLogs[ii + 7]["op"] == "JUMPDEST"
                ) ): 
                # comparison succeeds
                funcSelector = structLogs[ii + 2]["stack"][-1]
                funcSelector = addLeadningZeroFuncSelector(funcSelector)
                self.printIndentContentLogging("Enter into function ", funcSelector)
                




            # function selector comparison succeeds for Vyper
            if ii + 4 < len(structLogs) and \
                structLogs[ii]["op"] == "PUSH4" and \
                structLogs[ii + 1]["op"] == "PUSH1" and \
                structLogs[ii + 2]["op"] == "MLOAD" and \
                structLogs[ii + 3]["op"] == "EQ" and \
                structLogs[ii + 4]["op"] == "ISZERO" and \
                structLogs[ii + 4]["stack"][-1] == "0x1" and \
                structLogs[ii + 5]["op"] == "PUSH2" and \
                structLogs[ii + 6]["op"] == "JUMPI": # comparison succeeds

                funcSelector = structLogs[ii + 3]["stack"][-1]
                funcSelector = addLeadningZeroFuncSelector(funcSelector)
                self.printIndentContentLogging("Enter into function ", funcSelector)

                # if self.logging > 0:
                #     # print("self.logging", self.logging)
                #     funcSigMap = funcSigMapMap[self.contractAddressStack[-1]]
                #     # print("contract key, ", self.contractAddressStack[-1])
                #     # print("funcSigMapMap keys", funcSigMapMap.keys())
                #     self.printIndentContentLogging("Function name:", funcSigMap[funcSelector][0], " ||  Function Signature:", funcSigMap[funcSelector][1], funcSigMap[funcSelector][2])



            # A log should start from CALL/STATICCALL/DELEGATECALL/CREATE/CREATE2/
            # end with RETURN/STOP/REVERT/SELFDESTRUCT
            if ii + 1 < len(structLogs) and \
                (structLogs[ii]["op"] == "CREATE" or structLogs[ii]["op"] == "CREATE2"):
                opcode = structLogs[ii]["op"]
                value = structLogs[ii]["stack"][-1]
                offset = structLogs[ii]["stack"][-2]
                size = structLogs[ii]["stack"][-3]
                if structLogs[ii]["op"] == "CREATE2":
                    salt = structLogs[ii]["stack"][-4]

                depth = structLogs[ii]["depth"]
                addr = None
                for jj in range(ii + 1, len(structLogs)):
                    if structLogs[jj]["depth"] == depth:
                        addr = structLogs[jj]["stack"][-1]
                        break
                addr = "0x" + addr[2:].zfill(40)

                self.incrementLogging(addr)
                msgSender = self.getMsgSender()
                self.msgSenderStack.append(msgSender)
                self.funcSelectorStack.append(funcSelector)
                funcSelector = "constructor"


                infoDict = {"type": opcode.lower(), "structLogsStart": ii,  "addr": addr, "msg.sender": msgSender}
                newTraceTree =  TraceTree(infoDict)
                
                if addr == contractAddress and self.logging == 1:
                    # means we are calling a function inside the target contract
                    metaTraceTree.addInternalCall(newTraceTree, self.logging)
                elif self.logging > 1:
                    metaTraceTree.addInternalCall(newTraceTree, self.logging)


                # print(self.funcSelectorStack)

                self.calldataStack.append({"calldata":"", "preimage":{}, "fixed": False})  # preimage is a map from key to keccak(key)
                self.contractAddressStack.append(addr)
                self.isDelegateCallStack.append(False)
                

                self.printIndentContentLogging(opcode, "value = ", value,  "address = ", addr)
                self.printIndentContentLogging("msg.sender = ", msgSender, "({} does change msg.sender)".format(opcode))


                self.printIndentContentLogging("Currently Entering into a contract", addr)


                
                if self.logging > 0:
                    if contractAddress not in self.contractAddressStack:
                        sys.exit("Error: contractAddress not in self.contractAddressStack")
                    # if addr not in funcSigMapMap: # and not self.analyzer.isVyper(addr):
                    #     funcSigMapMap[addr] = self.analyzer.contract2funcSigMap(addr)
            
            # Call a function inside another contract
            elif structLogs[ii]["op"] == "CALL" and "error" not in structLogs[ii]:
                # gas = Web3.toInt(hexstr = structLogs[ii]["stack"][-1])
                hex_str = structLogs[ii]["stack"][-1]
                gas = int(hex_str, 16)

                addr = structLogs[ii]["stack"][-2]
                if len(addr) > 42:
                    addr = '0x' + addr[-40:]
                addr = "0x" + addr[2:]
                value = structLogs[ii]["stack"][-3]
                argsOffset = structLogs[ii]["stack"][-4]
                argsLength = structLogs[ii]["stack"][-5]
                retOffset = structLogs[ii]["stack"][-6]
                retLength = structLogs[ii]["stack"][-7]
                
                calldata = d.extractMemory(structLogs[ii]["memory"], argsOffset, argsLength)


                if addr == "0x1" or addr == "0x2" or addr == "0x3" or addr == "0x4":
                    # 0x1 represents: ECREC
                    # 0x2 represents: SHA256
                    # 0x3 represents: RIP160
                    # 0x4 represents: IDENTITY
                    continue
                
                addr = "0x" + addr[2:].zfill(40)

                if structLogs[ii]["depth"] == structLogs[ii + 1]["depth"]:
                    # looks like a fallback function
                    # In rare rare cases, "CALL" opcode does not increase the depth 
                    # which means we should not change stacks
                    self.printIndentContentLogging("call(gas = {}, addr = {}, value = {}, argsOffset = {}, argsLength = {})".format(gas, addr, value, argsOffset, argsLength))
                    self.printIndentContentLogging("call does not increase depth")
                    msgSender = self.getMsgSender()
                    infoDict = {"type": "call", "structLogsStart": ii, \
                                "structLogsEnd": ii, \
                                "gas": gas, "addr": addr, \
                                "msg.value": value, "msg.sender": msgSender, \
                                "retOffset": retOffset, "retLength": retLength, \
                                "name": "fallback", \
                                "inputs": [], \
                                "Raw calldata": calldata
                            }
                            
                    newTraceTree =  TraceTree(infoDict)
                    if self.logging > 0:
                        metaTraceTree.addInternalCall(newTraceTree, self.logging + 1)
                    continue

                self.incrementLogging(addr)
                msgSender = self.getMsgSender()
                self.msgSenderStack.append(msgSender)
                self.funcSelectorStack.append(funcSelector)
                funcSelector = ""

                # print(self.funcSelectorStack)

                infoDict = {"type": "call", "structLogsStart": ii, "gas": gas, "addr": addr, \
                            "msg.value": value, "msg.sender": msgSender, \
                            "retOffset": retOffset, "retLength": retLength, \
                            "Raw calldata": calldata}
                newTraceTree =  TraceTree(infoDict)
                
                if addr == contractAddress and self.logging == 1:
                    # means we are calling a function inside the target contract
                    metaTraceTree.addInternalCall(newTraceTree, self.logging)
                elif self.logging > 1:
                    metaTraceTree.addInternalCall(newTraceTree, self.logging)

                self.calldataStack.append({"calldata": calldata, "preimage":{}, "fixed": True})
                
                self.contractAddressStack.append(addr)
                self.isDelegateCallStack.append(False)

                self.printIndentContentLogging("call(gas = {}, addr = {}, value = {}, argsOffset = {}, argsLength = {})".format(gas, addr, value, argsOffset, argsLength))
                self.printIndentContentLogging("msg.sender = ", msgSender, "(Call does change msg.sender)")
                self.printIndentContentLogging("Currently Entering into a contract", addr)

                # print("self.msgSenderStack = ", self.msgSenderStack)

                if self.logging > 0:
                    if contractAddress not in self.contractAddressStack:
                        sys.exit("Error: contractAddress not in self.contractAddressStack")
                    # if addr not in funcSigMapMap: # and not self.analyzer.isVyper(addr):
                    #     funcSigMapMap[addr] = self.analyzer.contract2funcSigMap(addr)
   
            # Call a function inside another contract
            elif structLogs[ii]["op"] == "CALLCODE" and "error" not in structLogs[ii]:
                # gas = Web3.toInt(hexstr = structLogs[ii]["stack"][-1])
                hex_str = structLogs[ii]["stack"][-1]
                gas = int(hex_str, 16)

                addr = structLogs[ii]["stack"][-2]
                if len(addr) > 42:
                    addr = '0x' + addr[-40:]
                value = structLogs[ii]["stack"][-3]
                argsOffset = structLogs[ii]["stack"][-4]
                argsLength = structLogs[ii]["stack"][-5]
                retOffset = structLogs[ii]["stack"][-6]
                retLength = structLogs[ii]["stack"][-7]

                calldata = d.extractMemory(structLogs[ii]["memory"], argsOffset, argsLength)


                if addr == "0x1" or addr == "0x2" or addr == "0x3" or addr == "0x4":
                    # 0x1 represents: ECREC
                    # 0x2 represents: SHA256
                    # 0x3 represents: RIP160
                    # 0x4 represents: IDENTITY
                    continue

                addr = "0x" + addr[2:].zfill(40)
                self.incrementLogging(addr)

                msgSender = self.getMsgSender()
                self.msgSenderStack.append(msgSender)
                self.funcSelectorStack.append(funcSelector)
                funcSelector = ""
                
                infoDict = {"type": "callcode", "structLogsStart": ii, "gas": gas, "addr": addr, \
                            "msg.value": value, "msg.sender": msgSender, \
                            "retOffset": retOffset, "retLength": retLength, \
                            "Raw calldata": calldata}
                newTraceTree =  TraceTree(infoDict)
                
                if addr == contractAddress and self.logging == 1:
                    # means we are calling a function inside the target contract
                    metaTraceTree.addInternalCall(newTraceTree, self.logging)
                elif self.logging > 1:
                    metaTraceTree.addInternalCall(newTraceTree, self.logging)

                
                calldata = d.extractMemory(structLogs[ii]["memory"], argsOffset, argsLength)
                self.calldataStack.append({"calldata":calldata, "preimage":{}, "fixed": True})
                self.contractAddressStack.append(addr)
                self.isDelegateCallStack.append(True)
                self.printIndentContentLogging("callcode(gas = {}, addr = {}, value = {}, argsOffset = {}, argsLength = {})".format(gas, addr, value, argsOffset, argsLength))
                self.printIndentContentLogging("msg.sender = ", msgSender, "(Callcode does change msg.sender)")
                self.printIndentContentLogging("Currently Entering into a contract", addr)
                # print("self.msgSenderStack = ", self.msgSenderStack)

                if self.logging > 0:
                    if contractAddress not in self.contractAddressStack:
                        sys.exit("Error: contractAddress not in self.contractAddressStack")
                    # if addr not in funcSigMapMap: # and not self.analyzer.isVyper(addr):
                    #     funcSigMapMap[addr] = self.analyzer.contract2funcSigMap(addr)


            # calls a method in another contract with state changes disallowed
            elif structLogs[ii]["op"] == "STATICCALL" and "error" not in structLogs[ii]:
                # gas = Web3.toInt(hexstr = structLogs[ii]["stack"][-1])
                hex_str = structLogs[ii]["stack"][-1]
                gas = int(hex_str,16)

                addr = structLogs[ii]["stack"][-2]
                if len(addr) > 42:
                    addr = '0x' + addr[-40:]
                argsOffset = structLogs[ii]["stack"][-3]
                argsLength = structLogs[ii]["stack"][-4]
                retOffset = structLogs[ii]["stack"][-5]
                retLength = structLogs[ii]["stack"][-6]

                
                calldata = d.extractMemory(structLogs[ii]["memory"], argsOffset, argsLength)


                if addr == "0x1" or addr == "0x2" or addr == "0x3" or addr == "0x4":
                    # 0x1 represents: ECREC
                    # 0x2 represents: SHA256
                    # 0x3 represents: RIP160
                    # 0x4 represents: IDENTITY
                    # infoDict = {"type": "staticcall", "structLogsStart": ii, "gas": gas, "addr": addr, "msg.sender": msgSender, \
                    #         "retOffset": retOffset, "retLength": retLength, "structLogsEnd": ii}
                    # newTraceTree =  TraceTree(infoDict)
                    # if addr == contractAddress and self.logging == 1:
                    #     # means we are calling a function inside the target contract
                    #     metaTraceTree.addInternalCall(newTraceTree, self.logging)
                    # elif self.logging > 1:
                    #     metaTraceTree.addInternalCall(newTraceTree, self.logging)
                    continue

                # another situation
                # I cannot think of any reason why we need to staticcall when the return length is 0
                # the only reason I can think of is to clear the stack, but it makes no sense............
                if retLength == "0x0":
                    # print("suspicious staticcall with retLength = 0")
                    if structLogs[ii]["depth"] == structLogs[ii + 1]["depth"]:
                        continue

                # Consider precompile EIP-712 ecrecover 
                addr = "0x" + addr[2:].zfill(40)
                deployTx = ce.Contract2DeployTx(addr)
                if deployTx is None:
                    # sys.exit("Precompile ecrecover detected")
                    continue

                self.incrementLogging(addr)

                msgSender = self.getMsgSender()
                self.msgSenderStack.append(msgSender)
                self.funcSelectorStack.append(funcSelector)
                funcSelector = ""

                # if addr == "0x44fbebd2f576670a6c33f6fc0b00aa8c5753b322":
                #     print("now is the time")

                # print(self.funcSelectorStack)

                infoDict = {"type": "staticcall", "structLogsStart": ii, "gas": gas, "addr": addr, "msg.sender": msgSender, \
                            "retOffset": retOffset, "retLength": retLength, "Raw calldata": calldata}
                newTraceTree =  TraceTree(infoDict)
                
                if addr == contractAddress and self.logging == 1:
                    # means we are calling a function inside the target contract
                    metaTraceTree.addInternalCall(newTraceTree, self.logging)
                elif self.logging > 1:
                    metaTraceTree.addInternalCall(newTraceTree, self.logging)

                self.calldataStack.append({"calldata":calldata, "preimage":{}, "fixed": True})                
                self.contractAddressStack.append(addr)
                self.isDelegateCallStack.append(False)
                self.printIndentContentLogging("staticcall(gas = {}, addr = {}, argsOffset = {}, argsLength = {})".format(gas, addr, argsOffset, argsLength))
                self.printIndentContentLogging("msg.sender = ", msgSender, "(Staticcall does change msg.sender)") 
                self.printIndentContentLogging("Currently Entering into a contract", addr)

                # print("self.msgSenderStack = ", self.msgSenderStack)

                # if self.logging > 0:
                #     if contractAddress not in self.contractAddressStack:
                #         sys.exit("Error: contractAddress not in self.contractAddressStack")
                #     if addr not in funcSigMapMap: # and not self.analyzer.isVyper(addr):
                #         funcSigMapMap[addr] = self.analyzer.contract2funcSigMap(addr)


            #  calls a method in another contract, using the storage of the current contract
            elif structLogs[ii]["op"] == "DELEGATECALL" and "error" not in structLogs[ii]:
                # gas = Web3.toInt(hexstr = structLogs[ii]["stack"][-1])
                hex_str = structLogs[ii]["stack"][-1]
                gas = int(hex_str, 16)
                addr = structLogs[ii]["stack"][-2]
                if len(addr) > 42:
                    addr = '0x' + addr[-40:]
                argsOffset = structLogs[ii]["stack"][-3]
                argsLength = structLogs[ii]["stack"][-4]
                retOffset = structLogs[ii]["stack"][-5]
                retLength = structLogs[ii]["stack"][-6]
                calldata = d.extractMemory(structLogs[ii]["memory"], argsOffset, argsLength)

                if addr == "0x1" or addr == "0x2" or addr == "0x3" or addr == "0x4":
                    # 0x1 represents: ECREC
                    # 0x2 represents: SHA256
                    # 0x3 represents: RIP160
                    # 0x4 represents: IDENTITY
                    continue

                if structLogs[ii]["depth"] == structLogs[ii + 1]["depth"]:
                    # looks like call fails
                    continue
                
                addr = "0x" + addr[2:].zfill(40)

                self.incrementLogging(addr)

                msgSender = self.getMsgSender(isDelegate=True)
                self.msgSenderStack.append(msgSender)
                self.funcSelectorStack.append(funcSelector)
                funcSelector = ""
                # print(self.funcSelectorStack)

                infoDict = {"type": "delegatecall", "structLogsStart": ii,  "gas": gas, "addr": addr, "msg.sender": msgSender, \
                            "retOffset": retOffset, "retLength": retLength, "proxy": self.contractAddressStack[-1], "Raw calldata": calldata}
                    
                newTraceTree =  TraceTree(infoDict)
                
                if addr == contractAddress and self.logging == 1:
                    # means we are calling a function inside the target contract
                    metaTraceTree.addInternalCall(newTraceTree, self.logging)
                elif self.logging > 1:
                    metaTraceTree.addInternalCall(newTraceTree, self.logging)

                self.calldataStack.append({"calldata":calldata, "preimage":{}, "fixed": True})
                self.contractAddressStack.append(addr)
                self.isDelegateCallStack.append(True)
                self.printIndentContentLogging("delegatecall(gas = {}, addr = {}, argsOffset = {}, argsLength = {})".format(gas, addr, argsOffset, argsLength))
                self.printIndentContentLogging("msg.sender = ", msgSender, "(delegate call does not change msg.sender)")
                self.printIndentContentLogging("Currently Entering into a contract", addr)

                # if self.logging > 0:
                #     if contractAddress not in self.contractAddressStack:
                #         sys.exit("Error: contractAddress not in self.contractAddressStack")
                #     if addr not in funcSigMapMap: # and not self.analyzer.isVyper(addr):
                #         funcSigMapMap[addr] = self.analyzer.contract2funcSigMap(addr)

            # check if matches the pattern of RETURN
            if structLogs[ii]["op"] == "RETURN":
                # self.printIndentContent("Function Returns with something(RETURN)")
                self.printIndentContentLogging("Currently Leaving from a contract(RETURN)", self.contractAddressStack[-1])
                calldata = self.calldataStack[-1]["calldata"]

                self.printIndentContentLogging("callData = ", calldata)

                if self.logging > 0:
                    metaTraceTree.updateInfo({"structLogsEnd": ii}, self.logging)
                    gasEnd = structLogs[ii]["gas"]
                    metaTraceTree.updateInfo({"gasEnd": gasEnd}, self.logging)

                if self.logging > 0 and self.logging < LoggingUpperBound and funcSelector != "constructor" :
                    offset = structLogs[ii]["stack"][-1]
                    length = structLogs[ii]["stack"][-2]
                    self.printIndentContentLogging("Function Returns memory[{}:{}+{}]".format(offset, offset, length))
                    # self.printIndentContentLogging("memory = ",  structLogs[ii]["memory"])
                    currentContract = self.contractAddressStack[-1]

                    # name = self.getFuncName(funcSigMapMap, currentContract, funcSelector)
                    # self.printIndentContentLogging("Function Name = ", name)

                    insert_calldata = calldata
                    insert_return  = d.extractMemory(structLogs[ii]["memory"], offset, length)
                    if self.calldataStack[-1]["fixed"]:
                        funcSelector = "0x" + calldata[0:8]
                    metaTraceTree.updateInfo({"Selector": funcSelector, \
                                                "Raw returnvalue": insert_return, \
                                                "Raw calldata": insert_calldata}, self.logging)
                        

                    # if len(metaTraceTree.internalCalls) > 0:
                    #     name, Ctypes, Cdecoded, Rtypes, Rdecoded = self.getFuncSpecs(funcSigMapMap, currentContract, funcSelector, calldata, structLogs[ii]["memory"], offset, length)
                    #     metaTraceTree.updateInfo({"name": name, \
                    #                             "Selector": funcSelector, \
                    #                             "Decoded returnvalue types": Rtypes, \
                    #                             "Decoded returnvalue": Rdecoded, \
                    #                             "Decoded calldata types": Ctypes, \
                    #                             "Decoded calldata": Cdecoded}, self.logging)
                        

                funcSelector = self.funcSelectorStack.pop()
                self.contractAddressStack.pop()
                self.msgSenderStack.pop()
                self.isDelegateCallStack.pop()
                self.calldataStack.pop()
                
                self.decrementLogging()

            elif structLogs[ii]["op"] == "STOP":
                # self.printIndentContent("Function Returns with nothing(STOP)")
                self.printIndentContentLogging("Currently Leaving from a contract(STOP)", self.contractAddressStack[-1])
                calldata = self.calldataStack[-1]["calldata"]
                self.printIndentContentLogging("callData = ", calldata)

                if self.logging > 0:
                    try:
                        metaTraceTree.updateInfo({"structLogsEnd": ii}, self.logging)
                        # if "gas" in structLogs[ii]:
                        gasEnd = structLogs[ii]["gas"]
                        metaTraceTree.updateInfo({"gasEnd": gasEnd}, self.logging)
                    except IndexError:
                        # potentially it's a call to fallback function
                        pass

                if self.logging > 0 and self.logging < LoggingUpperBound:
                    currentContract = self.contractAddressStack[-1]
                    # name, Ctypes, Cdecoded, Rtypes, Rdecoded = self.getFuncSpecs(funcSigMapMap, currentContract, funcSelector, calldata)
                    # self.printIndentContentLogging("Decoded calldata types = ", Ctypes)
                    # self.printIndentContentLogging("Decoded calldata = ", Cdecoded)
                    if self.calldataStack[-1]["fixed"]:
                        funcSelector = "0x" + calldata[0:8]
                    insert_calldata = calldata
                    metaTraceTree.updateInfo({"Selector": funcSelector, \
                                                "Raw returnvalue": "", \
                                                "Raw calldata": insert_calldata}, self.logging)
                        

               
                funcSelector = self.funcSelectorStack.pop()
                self.contractAddressStack.pop()
                self.msgSenderStack.pop()
                self.isDelegateCallStack.pop()
                self.calldataStack.pop()
                self.decrementLogging()

            elif structLogs[ii]["op"] == "REVERT":
                # self.printIndentContent("Function Returns with nothing(REVERT)")
                self.printIndentContentLogging("Currently Leaving from a contract(REVERT)", self.contractAddressStack[-1])
                calldata = self.calldataStack[-1]["calldata"]
                self.printIndentContentLogging("callData = ", calldata)

                if self.logging > 0:
                    metaTraceTree.updateInfo({"structLogsEnd": ii}, self.logging)
                    # if "gas" in structLogs[ii]:
                    gasEnd = structLogs[ii]["gas"]
                    metaTraceTree.updateInfo({"gasEnd": gasEnd}, self.logging)

                
                if self.logging > 0 and self.logging < LoggingUpperBound:
                    currentContract = self.contractAddressStack[-1]
                    if self.calldataStack[-1]["fixed"]:
                        funcSelector = "0x" + calldata[0:8]
                    insert_calldata = calldata
                    metaTraceTree.updateInfo({"Selector": funcSelector, \
                                                "Raw returnvalue": "", \
                                                "Raw calldata": insert_calldata}, self.logging)
                        


                funcSelector = self.funcSelectorStack.pop()
                self.contractAddressStack.pop()
                self.msgSenderStack.pop()
                self.isDelegateCallStack.pop()
                self.calldataStack.pop()
                self.decrementLogging()

            elif structLogs[ii]["op"] == "SELFDESTRUCT":
                # self.printIndentContent("Function Returns with nothing(SELFDESTRUCT)")
                self.printIndentContentLogging("Currently Leaving from a contract(SELFDESTRUCT)", self.contractAddressStack[-1])
                calldata = self.calldataStack[-1]["calldata"]
                self.printIndentContentLogging("callData = ", calldata)

                if self.logging > 0:
                    metaTraceTree.updateInfo({"structLogsEnd": ii}, self.logging)
                    # if "gas" in structLogs[ii]:
                    gasEnd = structLogs[ii]["gas"]
                    metaTraceTree.updateInfo({"gasEnd": gasEnd}, self.logging)

                if self.logging > 0 and self.logging < LoggingUpperBound:    
                    currentContract = self.contractAddressStack[-1]
                    insert_calldata = calldata
                    # insert_return  = d.extractMemory(structLogs[ii]["memory"], offset, length)
                    if self.calldataStack[-1]["fixed"]:
                        funcSelector = "0x" + calldata[0:8]
                    metaTraceTree.updateInfo({"Selector": funcSelector, \
                                                "Raw returnvalue": "", \
                                                "Raw calldata": insert_calldata}, self.logging)

                funcSelector = self.funcSelectorStack.pop()
                self.contractAddressStack.pop()
                self.msgSenderStack.pop()
                self.isDelegateCallStack.pop()
                self.calldataStack.pop()
                self.decrementLogging()


            # Test INVALID opcode
            elif structLogs[ii]["op"] == "INVALID":
                self.printIndentContentLogging("Currently Leaving from a contract(INVALID)", self.contractAddressStack[-1])
                calldata = self.calldataStack[-1]["calldata"]
                self.printIndentContentLogging("callData = ", calldata)

                if self.logging > 0:
                    metaTraceTree.updateInfo({"structLogsEnd": ii}, self.logging)
                    # if "gas" in structLogs[ii]:
                    gasEnd = structLogs[ii]["gas"]
                    metaTraceTree.updateInfo({"gasEnd": gasEnd}, self.logging)
                
                if self.logging > 0 and self.logging < LoggingUpperBound:
                    currentContract = self.contractAddressStack[-1]
                    insert_calldata = calldata
                    if self.calldataStack[-1]["fixed"]:
                        funcSelector = "0x" + calldata[0:8]
                    metaTraceTree.updateInfo({"Selector": funcSelector, \
                                                "Raw returnvalue": "", \
                                                "Raw calldata": insert_calldata}, self.logging)
                funcSelector = self.funcSelectorStack.pop()
                self.contractAddressStack.pop()
                self.msgSenderStack.pop()
                self.isDelegateCallStack.pop()
                self.calldataStack.pop()
                self.decrementLogging()




            elif len(structLogs) > ii + 1 and  structLogs[ii + 1]["depth"] < structLogs[ii]["depth"] \
                and structLogs[ii]["op"] != "STOP" and structLogs[ii]["op"] != "RETURN" \
                and structLogs[ii]["op"] != "REVERT" and structLogs[ii]["op"] != "INVALID" \
                and structLogs[ii]["op"] != "SELFDESTRUCT":
                # print("gas=", structLogs[ii]["gas"])
                # print(structLogs[ii])
                # print(structLogs[ii + 1])
                # self.printIndentContent("Function Returns with nothing(GASLESS)")

                self.printIndentContentLogging("Currently Leaving from a contract(GASLESS)", self.contractAddressStack[-1])
                calldata = self.calldataStack[-1]["calldata"]
                self.printIndentContentLogging("callData = ", calldata)

                if self.logging > 0:
                    metaTraceTree.updateInfo({"structLogsEnd": ii}, self.logging)
                    # if "gas" in structLogs[ii]:
                    gasEnd = structLogs[ii]["gas"]
                    metaTraceTree.updateInfo({"gasEnd": gasEnd}, self.logging)
                    metaTraceTree.updateInfo({"gasless": True}, self.logging)


                if self.logging > 0 and self.logging < LoggingUpperBound:    
                    currentContract = self.contractAddressStack[-1]
                    insert_calldata = calldata
                    d = decoder()
                    if "memory" not in structLogs[ii]:
                        metaTraceTree.updateInfo({"Selector": funcSelector, \
                                                "Raw calldata": insert_calldata}, self.logging)

                    else:
                        insert_return  = d.extractMemory(structLogs[ii]["memory"], offset, length)
                        metaTraceTree.updateInfo({"Selector": funcSelector, \
                                                    "Raw returnvalue": insert_return, \
                                                    "Raw calldata": insert_calldata}, self.logging)
                        

                funcSelector = self.funcSelectorStack.pop()
                self.contractAddressStack.pop()
                self.msgSenderStack.pop()
                self.isDelegateCallStack.pop()
                self.calldataStack.pop()
                
                self.decrementLogging()
            
            
            elif "error" in structLogs[ii]:
                # sys.exit("Parser: \'error\' in structLogs, but not handled by gasless send")
                metaTraceTree.info["isRevert"] = True
                funcSelector = self.funcSelectorStack.pop()
                self.contractAddressStack.pop()
                self.msgSenderStack.pop()
                self.isDelegateCallStack.pop()
                self.calldataStack.pop()
                
                self.decrementLogging()

                if ii + 1 == len(structLogs):
                    return metaTraceTree

                

            # print sload
            if structLogs[ii]["op"] == "SLOAD":
                key = structLogs[ii]["stack"][-1]
                # print("structLogs[ii]", structLogs[ii])
                # print("structLogs[ii + 1]", structLogs[ii + 1])
                value = structLogs[ii + 1]["stack"][-1]
                self.printIndentContentLogging("sload[{}] -> {}".format(key, value))
                if self.logging > 0:
                    metaTraceTree.updateInfoList("sload/sstore", ("sload", key, value, pc, ii), self.logging)
                elif structLogs[ii]["depth"] == 0:
                    metaTraceTree.updateInfoList("sload/sstore", ("sload", key, value, pc, ii), 0)


                # interpret the key
                # find answer from two places: 
                # 1. Preimage: self.calldataStack[-1]["preimage"]
                # eg. {hashValue: ("Vyper", mapPositionHex, key[64:])}
                # 2  StorageMapping: storageMappingMap[currentContract]
                # eg. "96": [
                #     "balanceOf",
                #     [
                #         "address",
                #         "uint256"
                #     ]
                # ]
                # 3. Transaction Variables:
                # eg. msg.sender, msg.value, tx.origin, gas, ...   No one will use gas as key to a map, right? ;)
                # should take a look at https://github.com/banteg/storage-layout to better understand the storage layout

                # goal: In the end, it should be in the form of 
                # Start from sth in storage Mapping, then calculate a function f(paras, msg.sender, msg.value, tx.origin) and get the index. 
                # Then, we can get the answer from the preimage. 

                # This is not trivial...

                # eg. sload[0xf7bb5e32e7dcc1b54124ab032e8d3728ddffa8e6f9fe66385a3ffce8c5cdc823] -> 0x0
                # several possibilities:
                # 1. key is in StorageMapping. Easiest case. 
                # 2. key is from nested mapping: a nested SHA3 call. Trace back preimage
                # 3. key is from nested dynamic array: trace how it is calculated.
                # 4. Most complicated case: key is calculated using paras. Symbolic execution is needed.
                

            # print sstore
            elif structLogs[ii]["op"] == "SSTORE":
                key = structLogs[ii]["stack"][-1]
                value = structLogs[ii]["stack"][-2]
                self.printIndentContentLogging("sstore[{}] = {}".format(key, value))
                if self.logging > 0:
                    metaTraceTree.updateInfoList("sload/sstore", ("sstore", key, value, pc, ii), self.logging)
                elif structLogs[ii]["depth"] == 0:
                    metaTraceTree.updateInfoList("sload/sstore", ("sstore", key, value, pc, ii), 0)

            # print calldatasize
            elif structLogs[ii]["op"] == "CALLDATASIZE":
                size = structLogs[ii + 1]["stack"][-1]
                self.printIndentContentLogging("msg.data.size -> {} bytes".format(size))
                if "calldatasize" not in self.calldataStack[-1]:
                    self.calldataStack[-1]["calldatasize"] = size
                elif self.calldataStack[-1]["calldatasize"] != size and self.calldataStack[-1]["calldatasize"] != -1:
                    print("self.calldataStack:")
                    for calldata in self.calldataStack:
                        print("calldatasize:", calldata["calldatasize"])
                    print("self.msgSenderStack:")
                    for msgSender in self.msgSenderStack:
                        print("msgSender:", msgSender)
                    print("self.isDelegateCallStack:", self.isDelegateCallStack)
                    print("self.contractAddressStack:")
                    for contractAddress in self.contractAddressStack:
                        print("contractAddress:", contractAddress)
                    print("self.funcSelectorStack:", self.funcSelectorStack)
                    print("len:", len(self.calldataStack))
                    print("len:", len(self.msgSenderStack))
                    print("len:", len(self.isDelegateCallStack))
                    print("len:", len(self.contractAddressStack))
                    print("len:", len(self.funcSelectorStack))
                    sys.exit("Error: calldatasize is changed, size = {} but self.calldataStack[-1][\"calldatasize\"] = {}".format(size, self.calldataStack[-1]["calldatasize"]))



            # print calldatacopy
            elif structLogs[ii]["op"] == "CALLDATACOPY":
                destOffset = structLogs[ii]["stack"][-1]
                offset = structLogs[ii]["stack"][-2]
                length = structLogs[ii]["stack"][-3]
                self.printIndentContentLogging("CALLDATACOPY: memory[{0}:{0}+{2}] = msg.data[{1}:{1}+{2}]".format(destOffset, offset, length))
                
            # print calldataload
            elif structLogs[ii]["op"] == "CALLDATALOAD":
                index = structLogs[ii]["stack"][-1]
                value = structLogs[ii + 1]["stack"][-1]
                
                # print("calldata[{}] -> {}".format(index, value))
                # self.printIndentContentLogging("calldata[{}] -> {}".format(index, value))
                

                if "calldata" in self.calldataStack[-1] and not self.calldataStack[-1]["fixed"]:
                    oldCalldata = self.calldataStack[-1]["calldata"]
                    calldataSizeInt = -1
                    if "calldatasize" in self.calldataStack[-1]:
                        calldataSize = self.calldataStack[-1]["calldatasize"]
                        calldataSizeInt = int(calldataSize, 16)
                    newCalldata = self.decoder.getCalldataHex(oldCalldata, calldataSizeInt, index, value)
                    self.calldataStack[-1]["calldata"] = newCalldata
                
                
                # print("Old method: ", self.calldataStack[-1]["calldata"])
                # print("calldataSize", calldataSize)
                # print("New method: ", newCalldata)

                self.printIndentContentLogging("calldata[{}] -> {}".format(index, value))

            # print origin
            elif structLogs[ii]["op"] == "ORIGIN":
                origin = structLogs[ii + 1]["stack"][-1]
                self.printIndentContentLogging("origin -> {}".format(origin))
            
            # print caller
            elif structLogs[ii]["op"] == "CALLER":
                caller = structLogs[ii + 1]["stack"][-1]
                # remove 0x prefix, add zero paddings and then add 0x prefix back
                
                caller = "0x" + caller[2:].zfill(40)

                msgSender = self.msgSenderStack[-1]
                msgSender = "0x" + msgSender[2:].zfill(40)

                self.printIndentContentLogging("caller -> {}".format(caller))


            # print callvalue
            elif structLogs[ii]["op"] == "CALLVALUE":
                callvalue = structLogs[ii + 1]["stack"][-1]
                if self.logging > 0:
                    metaTraceTree.updateInfo({"msg.value": callvalue}, self.logging)
                elif structLogs[ii]["depth"] == 0:
                    metaTraceTree.updateInfo({"msg.value": callvalue}, 0)
                self.printIndentContentLogging("callvalue -> {}".format(callvalue))


            # print selfbalance
            elif structLogs[ii]["op"] == "SELFBALANCE":
                selfbalance = structLogs[ii + 1]["stack"][-1]
                if self.logging > 0:
                    metaTraceTree.updateInfoList("selfbalance", (selfbalance, ii), self.logging)
                elif structLogs[ii]["depth"] == 0:
                    metaTraceTree.updateInfoList("selfbalance", (selfbalance, ii), 0)
                self.printIndentContentLogging("selfbalance -> {}".format(selfbalance))
            
            # print balance
            elif structLogs[ii]["op"] == "BALANCE":
                addr = structLogs[ii]["stack"][-1]
                addr = "0x" + addr[2:].zfill(40)
                balance = structLogs[ii + 1]["stack"][-1]
                if self.logging > 0:
                    metaTraceTree.updateInfoList("balance", (addr, balance, ii), self.logging)
                elif structLogs[ii]["depth"] == 0:
                    metaTraceTree.updateInfoList("balance", (addr, balance, ii), 0)
                    
                self.printIndentContentLogging("balance[{}] -> {}".format(addr, balance))
            
            # print timestamp
            elif structLogs[ii]["op"] == "TIMESTAMP":
                timestamp = structLogs[ii + 1]["stack"][-1]
                self.printIndentContentLogging("timestamp -> {}".format(timestamp))


        # print("msgSenderStack: ", self.msgSenderStack)
        # print("contractAddressStack: ", self.contractAddressStack)
        # print("isDelegateCallStack: ", self.isDelegateCallStack)


        if len(self.msgSenderStack) != 0 or len(self.contractAddressStack) != 0 \
            or len(self.isDelegateCallStack) != 0:

            if len(self.msgSenderStack) == 1 and len(self.contractAddressStack) == 1 and \
                self.msgSenderStack[0] == self.contractAddressStack[0]:
                # some EoA send ether to itself
                pass
            else:
                if input == "0x":
                    # calling fallback function, which is not a problem
                    pass
                elif len(structLogs) == 0:
                    # this is a withdraw operation, which is not a problem
                    pass
                elif structLogs[ii]["op"] == "REVERT" or structLogs[ii]["op"] == "INVALID":
                    pass
                else:
                    print("msgSenderStack: ", self.msgSenderStack)
                    print("contractAddressStack: ", self.contractAddressStack)
                    print("isDelegateCallStack: ", self.isDelegateCallStack)
                    sys.exit("Error! msgSenderStack, contractAddressStack, isDelegateCallStack should be empty at the end of a Tx")

        # metaTraceTree.cleanStaticCall()
        return metaTraceTree





def analyzeOneTxGlobal(txHash, path, cache_path = ""):
    trace = None
    try:
        trace = readCompressedJson(path)
    except Exception as e:
        printed = "\nreadCompressedJson Error: " + str(e)
        printed += "  txHash: " + txHash
        print(printed)
        return

    # changeLoggingUpperBound(1000)
    p = VmtraceParserGlobal()
    metaTraceTree = None
    # metaTraceTree = p.parseLogsGlobal(None, txHash, trace)
    try:
        metaTraceTree = p.parseLogsGlobal(None, txHash, trace)

    except KeyError as e:
        printed = "\nKey Error: " + str(e)   
        printed += "  txHash: " + txHash
        print(printed)
        return
    except Exception as e:
        printed = "\nOther Error: " + str(e)
        printed += "  txHash: " + txHash
        print(printed)
        return


    if cache_path != "":
        if not os.path.exists(cache_path):
            metaTraceTree = {txHash: metaTraceTree}
            writeCompressedJson(cache_path, metaTraceTree)
    return metaTraceTree
    