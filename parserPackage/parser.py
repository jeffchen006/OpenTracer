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

from web3 import Web3
import copy
import cProfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

import toml
settings = toml.load("settings.toml")






def checkmapPositionInStorageMapping(mapPosition, storageMapping, preimage):
    """Given a mapPosition and a storageMapping, check if the mapPosition is in the storageMapping"""
    # storageMapping: {0: ('Ownable._owner', 'address'), 32: ('Pausable.pauser', 'address'), 52: ('Pausable.paused', 'bool'), 64: ('Blacklistable.blacklister', 'address'), 96: ('Blacklistable.blacklisted', ('address', 'bool')), 128: ('FiatTokenV1.name', 'string'), 160: ('FiatTokenV1.symbol', 'string'), 192: ('FiatTokenV1.decimals', 'uint8'), 224: ('FiatTokenV1.currency', 'string'), 256: ('FiatTokenV1.masterMinter', 'address'), 276: ('FiatTokenV1.initialized', 'bool'), 288: ('FiatTokenV1.balances', ('address', 'uint256')), 320: ('FiatTokenV1.allowed', ('address', ('address', 'uint256'))), 352: ('FiatTokenV1.totalSupply_', 'uint256'), 384: ('FiatTokenV1.minters', ('address', 'bool')), 416: ('FiatTokenV1.minterAllowed', ('address', 'uint256')), 448: ('Rescuable._rescuer', 'address'), 480: ('EIP712Domain.DOMAIN_SEPARATOR', 'bytes32'), 512: ('GasAbstraction.TRANSFER_WITH_AUTHORIZATION_TYPEHASH', 'bytes32'), 544: ('GasAbstraction.APPROVE_WITH_AUTHORIZATION_TYPEHASH', 'bytes32'), 576: ('GasAbstraction.INCREASE_ALLOWANCE_WITH_AUTHORIZATION_TYPEHASH', 'bytes32'), 608: ('GasAbstraction.DECREASE_ALLOWANCE_WITH_AUTHORIZATION_TYPEHASH', 'bytes32'), 640: ('GasAbstraction.CANCEL_AUTHORIZATION_TYPEHASH', 'bytes32'), 672: ('GasAbstraction._authorizationStates', ('address', ('bytes32', 'GasAbstraction.AuthorizationState'))), 704: ('Permit.PERMIT_TYPEHASH', 'bytes32'), 736: ('Permit._permitNonces', ('address', 'uint256')), 768: ('FiatTokenV2._initializedV2', 'bool')}
    # preimage:  
    # {'0x882d7ed9f2a3bb94081200846cb72e20b34d0a96f26eafd7e2ec91639183323c': 
    #       ('Solc', 
    #       '0000000000000000000000000000000000000000000000000000000000000003', 
    #       '000000000000000000000000bebc44782c7db0a1a60cb6fe97d0b483032ff1c7'), 
    # '0x8caee21460e4b97ad21ef6f50ba78c06f8ace770150686bffca228a84ab684a8': 
    #       ('Solc', 
    #       '0000000000000000000000000000000000000000000000000000000000000003', 
    #       '0000000000000000000000009c211bfa6dc329c5e757a223fb72f5481d676dc1'), 
    # '0xbeff42312369bb0ffea406565ab897ad38d0d32a39e2ed7b1fcdcb8dca706a8': 
    #       ('Solc', 
    #       '000000000000000000000000000000000000000000000000000000000000000a', 
    #       '0000000000000000000000009c211bfa6dc329c5e757a223fb72f5481d676dc1'), 
    # '0xf8e05935db44fb75f76ff7f18f35b7e3d12441171b26eeafb55f7a73378f7641': 
    #       ('Solc', 
    #       '0beff42312369bb0ffea406565ab897ad38d0d32a39e2ed7b1fcdcb8dca706a8', 
    #       '000000000000000000000000bebc44782c7db0a1a60cb6fe97d0b483032ff1c7')
    # }

    pass



def unifySelectors(accesList):
    
    for map in accesList:
        if 'Selector' in map:
            map["Selector"] = map["Selector"].upper()
        



class VmtraceParser:
    def __init__(self):
        self.analyzer = Analyzer()
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
        self.CreateContract = None



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

        details = self.crawlQuickNode.Tx2Details(txHash)
        fromAddress = details["from"].lower()
        status = details["status"]

        toAddress = details["to"]
        interactContract = details["contractAddress"]
        
        # global states of a transaction
        origin = fromAddress
        msgSenderStack = [fromAddress]
        contractAddressStack = None
        isDelegateCallStack = None

        if toAddress != None:
            contractAddressStack = [toAddress.lower()]
            isDelegateCallStack = [False]
        elif interactContract != None:
            contractAddressStack = [interactContract.lower()]
            isDelegateCallStack = [False]
        else:
            sys.exit("Error: both toAddress and interactContract are None")

        self.msgSenderStack = msgSenderStack
        self.contractAddressStack = contractAddressStack
        self.isDelegateCallStack = isDelegateCallStack

        if toAddress is None and interactContract is not None:
            self.CreateContract = interactContract.lower()
        
        return status, origin

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
            # if "IRevest.FNFTConfig" in Ctypes :
            #     return "Undecoded", "None", "None", "None", "None"


            if "BZxObjects.LoanOrder" in Ctypes or "BZxObjects.LoanPosition" in Ctypes:
                return "Undecoded", "None", "None", "None", "None"
            if "IterableMapping.itmap storage" in Ctypes:
                return "Undecoded", "None", "None", "None", "None"

            
            if currentContract == "0x2069043d7556b1207a505eb459d18d908df29b55":
                for ii in range(len(Ctypes)):
                    if Ctypes[ii] == "uint256[]":
                        Ctypes[ii] = "uint256[3]"
                calldata = self.calldataStack[-2]["calldata"]

            if currentContract == "0x226124e83868812d3dae87eb3c5f28047e1070b7":
                if len(Ctypes) == 2 and Ctypes[0] == "uint256" and Ctypes[1] == "IRevest.LockParam":
                    Ctypes = ["uint256", "address", "uint256", "uint256", "uint256"]

            if currentContract == "0xa81bd16aa6f6b25e66965a2f842e9c806c0aa11f":
                if len(Ctypes) == 4 and Ctypes[0] == "uint256" and Ctypes[1] == "IRevest.FNFTConfig" and \
                    Ctypes[2] == "uint256" and Ctypes[3] == "address":
                    Ctypes = ["uint256", "address", "address", "uint256", "uint256", "uint256", "uint256", \
                              "bool", "bool", "bool", "uint256", "address"]
                    
            if currentContract == "0x2320a28f52334d62622cc2eafa15de55f9987ed9":
                newCtypes = []
                for ii in range(len(Ctypes)):
                    if Ctypes[ii] == "IRevest.FNFTConfig":
                        newCtypes += ["address", "address", "uint256", "uint256", "uint256", "uint256", "bool", "bool", "bool"]
                    else:
                        newCtypes.append(Ctypes[ii])
                Ctypes = newCtypes
                
                

            # if 'IRevest.FNFTConfig' in Ctypes:
            #     return "Undecoded", "None", "None", "None", "None"


    # struct FNFTConfig {
    #     address asset; // The token being stored
    #     address pipeToContract; // Indicates if FNFT will pipe to another contract
    #     uint depositAmount; // How many tokens
    #     uint depositMul; // Deposit multiplier
    #     uint split; // Number of splits remaining
    #     uint depositStopTime; //
    #     bool maturityExtension; // Maturity extensions remaining
    #     bool isMulti; //
    #     bool nontransferrable; // False by default (transferrable) //
    # }

                
    # struct LockParam {
    #     address addressLock;
    #     uint timeLockExpiry;
    #     LockType lockType;
    #     ValueLock valueLock;
    # }
            try:
                Cdecoded = self.decoder.decodeSimpleABI(Ctypes, calldata[8:]) # remove the first 4 bytes, which is the function selector
            except:
                Ctypes = "None"
                Cdecoded = "None"
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
            if currentContract == "0x226124e83868812d3dae87eb3c5f28047e1070b7" and \
                funcSelector == "0x3fe8ca06":
                Rtypes = ["address", "uint", "uint", "uint", "uint", "bool"]
            # if currentContract == "0x7538651d874b7578cf52152c9abd8f6617a38403" and \
            #     funcSelector == "0xe8177dcf":
            #     Rtypes = ["uint"]
            # if currentContract == "0x0eed07ced0c8c36d4a5bff44f2536422bb09be45" and \
            #     funcSelector == "0xe8177dcf":
                # Rtypes = ["uint"]
            if funcSelector == "0xe8177dcf":
                Rtypes = ["uint"]

            if "tuple" in Rtypes:
                print(currentContract)
                print(funcSelector)
                print(name)
                print("tuple in Rtypes")
                pass
            try:
                Rdecoded = self.decoder.decodeReturn(Rtypes, memoryList, offset, length)
            except:
                Rdecoded = "None"
        else:
            Rtypes = "None"
            Rdecoded = self.decoder.extractMemory(memoryList, offset, length)


        return name, Ctypes, Cdecoded, Rtypes, Rdecoded


    def parseLogs(self, contractAddress: str, txHash: str, trace) -> TraceTree:
        LoggingUpperBound = settings["runtime"]["LoggingUpperBound"]
        """Given a trace, return a list of logs restricted to <contractAddress>"""
        """These logs should be ready to feed into an invariant checker"""
        self.txHash = txHash
        ce = CrawlEtherscan()

        self.contractAddress = contractAddress.lower()
        contractAddress = self.contractAddress
        # storage layout of THE contract
        storageMapping = self.analyzer.contract2storageMapping(contractAddress)
        storageMappingMap = {contractAddress: storageMapping} # We also need some other contracts 
        
        funcSigMap = self.analyzer.contract2funcSigMap(contractAddress)
        funcSigMapMap = {contractAddress: funcSigMap}

        self.calldataStack = [{"calldata":"", "preimage":{}, "fixed": False}] # calldata of the function, a stack
        # eg. {
        #     "calldata": "0x12345678",
        #     "calldatasize": "0x12345678",
        # }
        funcSelector = "" # function selector of the function, a temp
        self.funcSelectorStack = [""] # function selector, a stack
        # self.calldataStack
        # self.funcSelectorStack
        # self.msgSenderStack
        # self.contractAddressStack
        # self.isDelegateCallStack

        status, origin = self.setupGlobalState(txHash)
        metaData = {"meta": True, "txHash": txHash, "status": status, "origin": origin}
        # if status == 0:
        #     return metaData
        metaTraceTree = TraceTree(metaData) # function calls represent what we really care
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
        # # }
        
        # if status == 0:
        #     sys.exit("Error: transaction reverted(cannot handle temporarily)")

        
        self.logging = 0  # 0: not logging, >=1: logging
        
        isFirstCall = False
        callValueHelper = None
        if self.contractAddressStack[-1] == contractAddress:
            # means we are calling a function inside the target contract
            self.incrementLogging( self.contractAddressStack[-1] )
            isFirstCall = True
        if self.CreateContract != None:
            infoDict = {"type": "create(2)", "structLogsStart": 0,  "addr": self.CreateContract, "msg.sender": origin, "name": "constructor"}
            newTraceTree =  TraceTree(infoDict)
            metaTraceTree.addInternalCall(newTraceTree, 1)

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

                if len(funcSigMap.keys()) > 0 and self.logging < LoggingUpperBound \
                    and currentContract.lower() == "0xd77e28a1b9a9cfe1fc2eee70e391c05d25853cbf":
                    funcSelector = structLogs[ii + 4]["stack"][-1]
                    funcSelector = addLeadningZeroFuncSelector(funcSelector)
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
                structLogs[ii + 4]["op"] == "JUMPI" and \
                structLogs[ii + 4]["stack"][-2] == "0x1" and \
                structLogs[ii + 5]["op"] == "JUMPDEST": 
                # comparison succeeds
                funcSelector = structLogs[ii + 2]["stack"][-1]
                funcSelector = addLeadningZeroFuncSelector(funcSelector)
                self.printIndentContentLogging("Enter into function ", funcSelector)
                
                if self.logging > 0:
                    # if funcSelector == "0x0933c1ed" or funcSelector == "0xc37f68e2":
                    #     print("now is the time")
                    # print("self.logging", self.logging)
                    funcSigMap = funcSigMapMap[self.contractAddressStack[-1]]
                    # print("contract key, ", self.contractAddressStack[-1])
                    # print("funcSigMapMap keys", funcSigMapMap.keys())
                    if len(funcSigMap.keys()) > 0 and self.logging < LoggingUpperBound:
                        if self.contractAddressStack[-1].lower() == "0x2069043d7556b1207a505eb459d18d908df29b55": 
                            funcSelector = self.funcSelectorStack[-1]
                        if funcSelector in funcSigMap:
                            self.printIndentContentLogging("Function name:", funcSigMap[funcSelector][0], " ||  Function Signature:", funcSigMap[funcSelector][1], funcSigMap[funcSelector][2])
                    else:
                        self.printIndentContentLogging("Function name: Unknown,   Function Signature: Unknown ")

                    if isFirstCall:
                        if len(self.msgSenderStack) == 2 and self.msgSenderStack[0] == self.msgSenderStack[1]:
                            pass
                        # elif len(self.msgSenderStack) != 1:
                        #     sys.exit("Error: len(self.msgSenderStack)!=1")

                        infoDict = None
                        gas = structLogs[ii]["gas"]
                        if callValueHelper != None:
                            if callValueHelper[0] > ii:
                                sys.exit("Error: callValueHelper[0] > ii")
                            else:
                                callValue = callValueHelper[1]
                            infoDict = {"type": "call", "structLogsStart": -1, "addr": contractAddress, \
                                                "gas": gas, "msg.value": callValue, "msg.sender": self.msgSenderStack[0]}
                        else:
                            infoDict = {"type": "call", "structLogsStart": -1, "addr": contractAddress, \
                                                "gas": gas, "msg.sender": self.msgSenderStack[0]}
                        newTraceTree =  TraceTree(infoDict)
                        metaTraceTree.addInternalCall(newTraceTree, self.logging)
                        isFirstCall = False




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

                if self.logging > 0:
                    # print("self.logging", self.logging)
                    funcSigMap = funcSigMapMap[self.contractAddressStack[-1]]
                    # print("contract key, ", self.contractAddressStack[-1])
                    # print("funcSigMapMap keys", funcSigMapMap.keys())
                    self.printIndentContentLogging("Function name:", funcSigMap[funcSelector][0], " ||  Function Signature:", funcSigMap[funcSelector][1], funcSigMap[funcSelector][2])



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


                infoDict = {"type": opcode.lower(), "structLogsStart": ii,  "addr": addr, "msg.sender": msgSender, "name": "constructor"}
                newTraceTree =  TraceTree(infoDict)
                
                if addr == contractAddress and self.logging == 1:
                    # means we are calling a function inside the target contract
                    metaTraceTree.addInternalCall(newTraceTree, self.logging)
                else:
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
                    if addr not in funcSigMapMap: # and not self.analyzer.isVyper(addr):
                        funcSigMapMap[addr] = self.analyzer.contract2funcSigMap(addr)
                    if addr not in storageMappingMap: # and not self.analyzer.isVyper(addr):
                        storageMappingMap[addr] = self.analyzer.contract2storageMapping(addr)
            


            # Call a function inside another contract
            elif structLogs[ii]["op"] == "CALL" and "error" not in structLogs[ii]:
                # gas = Web3.toInt(hexstr = structLogs[ii]["stack"][-1])
                hex_str = structLogs[ii]["stack"][-1]
                gas = int(hex_str, 16)

                # if gas == 16046392:
                #     print("now is the time")

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
                                "inputs": []
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
                            "retOffset": retOffset, "retLength": retLength}
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
                    if addr not in funcSigMapMap: # and not self.analyzer.isVyper(addr):
                        funcSigMapMap[addr] = self.analyzer.contract2funcSigMap(addr)
                    if addr not in storageMappingMap: # and not self.analyzer.isVyper(addr):
                        storageMappingMap[addr] = self.analyzer.contract2storageMapping(addr)
   
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

                # print(self.funcSelectorStack)
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
                    if addr not in funcSigMapMap: # and not self.analyzer.isVyper(addr):
                        funcSigMapMap[addr] = self.analyzer.contract2funcSigMap(addr)
                    if addr not in storageMappingMap: # and not self.analyzer.isVyper(addr):
                        storageMappingMap[addr] = self.analyzer.contract2storageMapping(addr)


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
                            "retOffset": retOffset, "retLength": retLength}
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

                if self.logging > 0:
                    if contractAddress not in self.contractAddressStack:
                        sys.exit("Error: contractAddress not in self.contractAddressStack")
                    if addr not in funcSigMapMap: # and not self.analyzer.isVyper(addr):
                        funcSigMapMap[addr] = self.analyzer.contract2funcSigMap(addr)
                    if addr not in storageMappingMap and len(funcSigMapMap[addr].keys()) > 0: # and not self.analyzer.isVyper(addr):
                        storageMappingMap[addr] = self.analyzer.contract2storageMapping(addr)

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
                
                addr = "0x" + addr[2:].zfill(40)

                self.incrementLogging(addr)

                msgSender = self.getMsgSender(isDelegate=True)
                self.msgSenderStack.append(msgSender)
                self.funcSelectorStack.append(funcSelector)
                funcSelector = ""
                # print(self.funcSelectorStack)

                infoDict = {"type": "delegatecall", "structLogsStart": ii,  "gas": gas, "addr": addr, "msg.sender": msgSender, \
                            "retOffset": retOffset, "retLength": retLength, "proxy": self.contractAddressStack[-1]}
                
                    
                newTraceTree =  TraceTree(infoDict)
                
                if addr == contractAddress and self.logging == 1:
                    # means we are calling a function inside the target contract
                    metaTraceTree.addInternalCall(newTraceTree, self.logging)
                elif self.logging > 1:
                    if self.logging == 2 and isFirstCall:
                        # it means the origin directly calls a proxy, while the proxy calls are not in the trace tree
                        callInfoDict = {"type": "call", "structLogsStart": 0,  "gas": structLogs[0]["gas"], "addr": self.contractAddressStack[-1], "msg.sender": origin, \
                            "retOffset": retOffset, "retLength": retLength}
                        newCallTraceTree =  TraceTree(callInfoDict)
                        metaTraceTree.addInternalCall(newCallTraceTree, self.logging - 1)

                    metaTraceTree.addInternalCall(newTraceTree, self.logging)

                self.calldataStack.append({"calldata":calldata, "preimage":{}, "fixed": True})
                
                self.contractAddressStack.append(addr)
                self.isDelegateCallStack.append(True)

                self.printIndentContentLogging("delegatecall(gas = {}, addr = {}, argsOffset = {}, argsLength = {})".format(gas, addr, argsOffset, argsLength))
                self.printIndentContentLogging("msg.sender = ", msgSender, "(delegate call does not change msg.sender)")
                self.printIndentContentLogging("Currently Entering into a contract", addr)

                # print("self.msgSenderStack = ", self.msgSenderStack)


                if self.logging > 0:
                    if contractAddress not in self.contractAddressStack:
                        sys.exit("Error: contractAddress not in self.contractAddressStack")
                    if addr not in funcSigMapMap: # and not self.analyzer.isVyper(addr):
                        funcSigMapMap[addr] = self.analyzer.contract2funcSigMap(addr)
                    if addr not in storageMappingMap: # and not self.analyzer.isVyper(addr):
                        storageMappingMap[addr] = self.analyzer.contract2storageMapping(addr)

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
                    
                    # print("currentContract", currentContract)
                    # print("funcSelector", funcSelector)
                    # print("funcSigMapMap[currentContract]", funcSigMapMap[currentContract])
                    if self.calldataStack[-1]["fixed"]:
                        funcSelector = "0x" + calldata[0:8]
                    name = self.getFuncName(funcSigMapMap, currentContract, funcSelector)
                    self.printIndentContentLogging("Function Name = ", name)

                    # name, Ctypes, Cdecoded, Rtypes, Rdecoded = self.getFuncSpecs(funcSigMapMap, currentContract, funcSelector, calldata, structLogs[ii]["memory"], offset, length)
                    # self.printIndentContentLogging("Function Name = ", name)
                    # self.printIndentContentLogging("Selector = ", funcSelector)
                    # self.printIndentContentLogging("Decoded returnvalue types = ", Rtypes)
                    # self.printIndentContentLogging("Decoded returnvalue = ", Rdecoded)
                    # self.printIndentContentLogging("Decoded calldata types = ", Ctypes)
                    # self.printIndentContentLogging("Decoded calldata = ", Cdecoded)

                    if len(metaTraceTree.internalCalls) > 0:


                        if name == "getTokenRecord" or name == "getFNFT" or name == "getEthToTokenInputPrice" \
                            or name == "getTokenToEthInputPrice" or name == "ethToTokenSwapInput":
                            metaTraceTree.updateInfo({"name": name}, \
                                                     self.logging, allowOverwrite=True)
                        else:
                            name, Ctypes, Cdecoded, Rtypes, Rdecoded = self.getFuncSpecs(funcSigMapMap, currentContract, funcSelector, calldata, structLogs[ii]["memory"], offset, length)
                            metaTraceTree.updateInfo({"name": name, \
                                                    "Selector": funcSelector, \
                                                    "Decoded returnvalue types": Rtypes, \
                                                    "Decoded returnvalue": Rdecoded, \
                                                    "Decoded calldata types": Ctypes, \
                                                    "Decoded calldata": Cdecoded}, self.logging)
                        

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
                    if self.calldataStack[-1]["fixed"]:
                        funcSelector = "0x" + calldata[0:8]
                    name, Ctypes, Cdecoded, Rtypes, Rdecoded = self.getFuncSpecs(funcSigMapMap, currentContract, funcSelector, calldata)
                    self.printIndentContentLogging("Decoded calldata types = ", Ctypes)
                    self.printIndentContentLogging("Decoded calldata = ", Cdecoded)
                    try: 
                        metaTraceTree.updateInfo({"name": name, \
                                              "Selector": funcSelector, \
                                              "Decoded returnvalue types": None, \
                                              "Decoded returnvalue": None, \
                                              "Decoded calldata types": Ctypes, \
                                              "Decoded calldata": Cdecoded}, self.logging)
                    except IndexError:
                        # potentially it's a call to fallback function
                        pass
               
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
                    name, Ctypes, Cdecoded, Rtypes, Rdecoded = self.getFuncSpecs(funcSigMapMap, currentContract, funcSelector, calldata)
                    self.printIndentContentLogging("Decoded calldata types = ", Ctypes)
                    self.printIndentContentLogging("Decoded calldata = ", Cdecoded)
                    metaTraceTree.updateInfo({"name": name, \
                                              "Selector": funcSelector, \
                                              "Decoded returnvalue types": None, \
                                              "Decoded returnvalue": None, \
                                              "Decoded calldata types": Ctypes, \
                                              "Decoded calldata": Cdecoded}, self.logging)

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
                    if self.calldataStack[-1]["fixed"]:
                        funcSelector = "0x" + calldata[0:8]
                    name, Ctypes, Cdecoded, Rtypes, Rdecoded = self.getFuncSpecs(funcSigMapMap, currentContract, funcSelector, calldata)
                    

                    self.printIndentContentLogging("Decoded calldata types = ", Ctypes)
                    self.printIndentContentLogging("Decoded calldata = ", Cdecoded)
                    metaTraceTree.updateInfo({"name": "selfdestruct", \
                                              "Selector": funcSelector, \
                                              "Decoded returnvalue types": None, \
                                              "Decoded returnvalue": None, \
                                              "Decoded calldata types": Ctypes, \
                                              "Decoded calldata": Cdecoded}, self.logging)

                funcSelector = self.funcSelectorStack.pop()
                self.contractAddressStack.pop()
                self.msgSenderStack.pop()
                self.isDelegateCallStack.pop()
                self.calldataStack.pop()
                self.decrementLogging()

            elif structLogs[ii + 1]["depth"] < structLogs[ii]["depth"] \
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

                if self.logging > 0 and self.logging < LoggingUpperBound:    
                    currentContract = self.contractAddressStack[-1]

                    name, Ctypes, Cdecoded, Rtypes, Rdecoded = self.getFuncSpecs(funcSigMapMap, currentContract, funcSelector, calldata)
                    self.printIndentContentLogging("Decoded calldata types = ", Ctypes)
                    self.printIndentContentLogging("Decoded calldata = ", Cdecoded)
                    metaTraceTree.updateInfo({"name": name + "(gasless)", \
                                              "Selector": funcSelector, \
                                              "Decoded returnvalue types": None, \
                                              "Decoded returnvalue": None, \
                                              "Decoded calldata types": Ctypes, \
                                              "Decoded calldata": Cdecoded}, self.logging)    

                funcSelector = self.funcSelectorStack.pop()
                self.contractAddressStack.pop()
                self.msgSenderStack.pop()
                self.isDelegateCallStack.pop()
                self.calldataStack.pop()
                self.decrementLogging()




            elif "error" in structLogs[ii]:
                sys.exit("Parser: \'error\' in structLogs, but not handled by gasless send")
                

            # print sload
            if structLogs[ii]["op"] == "SLOAD":
                key = structLogs[ii]["stack"][-1]
                value = structLogs[ii + 1]["stack"][-1]
                self.printIndentContentLogging("sload[{}] -> {}".format(key, value))
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
                    metaTraceTree.updateInfoList("sstore", (key, value, pc), self.logging)
                elif structLogs[ii]["depth"] == 0:
                    metaTraceTree.updateInfoList("sstore", (key, value, pc), 0)

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
                if caller != msgSender:
                    if len(self.msgSenderStack) != 1:
                        print("CALLER opcode returns {}, but msg.sender stack[-1] is {}".format(caller, msgSender))
                        print("len:", len(self.calldataStack))
                        print("len:", len(self.msgSenderStack))
                        print("len:", len(self.isDelegateCallStack))
                        print("len:", len(self.contractAddressStack))
                        print("len:", len(self.funcSelectorStack))
                        print("msgSenderStack: ", self.msgSenderStack)
                        print("contractAddressStack: ", self.contractAddressStack)
                        print("isDelegateCallStack: ", self.isDelegateCallStack)
                        sys.exit("Error! msg.sender is different from CALLER inside a Tx")

            # print callvalue
            elif structLogs[ii]["op"] == "CALLVALUE":
                callvalue = structLogs[ii + 1]["stack"][-1]
                if self.logging > 0:
                    if (self.contractAddress == '0xd06527d5e56a3495252a528c4987003b712860ee'  or \
                        self.contractAddress == "0x44fbebd2f576670a6c33f6fc0b00aa8c5753b322") and \
                        self.logging == 1 and isFirstCall:
                        gas = structLogs[ii]["gas"]
                        infoDict = {"type": "call", "structLogsStart": -1, "addr": contractAddress, \
                                    "gas": gas, "msg.value": callvalue, "msg.sender": self.msgSenderStack[0], \
                                    "name": "fallback", "inputs": []}
                        newTraceTree =  TraceTree(infoDict)
                        metaTraceTree.addInternalCall(newTraceTree, self.logging)
                        isFirstCall = False
                    else:
                        metaTraceTree.updateInfo({"msg.value": callvalue}, self.logging)
                elif structLogs[ii]["depth"] == 0:
                    metaTraceTree.updateInfo({"msg.value": callvalue}, 0)


                self.printIndentContentLogging("callvalue -> {}".format(callvalue))

            # print selfbalance
            elif structLogs[ii]["op"] == "SELFBALANCE":
                selfbalance = structLogs[ii + 1]["stack"][-1]
                self.printIndentContentLogging("selfbalance -> {}".format(selfbalance))
            
            # print balance
            elif structLogs[ii]["op"] == "BALANCE":
                addr = structLogs[ii]["stack"][-1]
                addr = "0x" + addr[2:].zfill(40)
                balance = structLogs[ii + 1]["stack"][-1]
                self.printIndentContentLogging("balance[{}] -> {}".format(addr, balance))
            
            # print timestamp
            elif structLogs[ii]["op"] == "TIMESTAMP":
                timestamp = structLogs[ii + 1]["stack"][-1]
                self.printIndentContentLogging("timestamp -> {}".format(timestamp))

            # Test INVALID opcode
            elif structLogs[ii]["op"] == "INVALID":
                pass
                # sys.exit("Error! INVALID opcode is detected")
        
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

                print("msgSenderStack: ", self.msgSenderStack)
                print("contractAddressStack: ", self.contractAddressStack)
                print("isDelegateCallStack: ", self.isDelegateCallStack)
                # sys.exit("Error! msgSenderStack, contractAddressStack, isDelegateCallStack should be empty at the end of a Tx")

        # metaTraceTree.cleanStaticCall()
        return metaTraceTree




    def track(self, contractAddress: str, traceTree, locator: locator,  trace = None): 
        """Given a trace tree, and a value of interest, track the value of interest via dynamic analysis"""
        """Several possibilities: 1. a function call 2. an event emitted 3. a return value"""
        # means we care about the 2nd argument of the function call
        if trace is not None:
            structLogs = trace['structLogs']
        else:
            structLogs = self.structLogs
            
        if locator.type == SELFCALLVALUE:
            ii = traceTree.info["structLogsStart"] + 1
            if structLogs[ii]['op'] == "CALL":
                hex_str = structLogs[ii]["stack"][-1]
                gas = int(hex_str, 16)
                addr = structLogs[ii]["stack"][-2]
                if len(addr) > 42:
                    addr = '0x' + addr[-40:]
                addr = "0x" + addr[2:].zfill(40)
                value = structLogs[ii]["stack"][-3]
                argsOffset = structLogs[ii]["stack"][-4]
                argsLength = structLogs[ii]["stack"][-5]
                retOffset = structLogs[ii]["stack"][-6]
                retLength = structLogs[ii]["stack"][-7]
                argsLengthInt = int(argsLength, base = 16)
                argsOffsetInt = int(argsOffset, base = 16)
                retOffsetInt = int(retOffset, base = 16)
                retLengthInt = int(retLength, base = 16)
                info = traceTree.info
                dataS = dataSource(info)
                dataS.metaData["value"] = value
                dataS.metaData["type"] = "msg.value"
                dataS.metaData["gas"] = gas
                DataSourceList.append(dataS)
            else:
                print("Error parser.py: SELFCALLVALUE does not start with a CALL opcode")


        

        # handle delegate call
        for ii in range(len(traceTree.internalCalls)):
            if "name" in traceTree.internalCalls[ii].info and \
                    traceTree.internalCalls[ii].info["name"] == "fallback" and \
                    len(traceTree.internalCalls[ii].internalCalls) == 1:
                traceTree.internalCalls[ii].info["name"] = traceTree.internalCalls[ii].internalCalls[0].info["name"]
                traceTree.internalCalls[ii].info["Selector"] = traceTree.internalCalls[ii].internalCalls[0].info["Selector"]
                traceTree.internalCalls[ii].info["Decoded returnvalue types"] = traceTree.internalCalls[ii].internalCalls[0].info["Decoded returnvalue types"]
                traceTree.internalCalls[ii].info["Decoded returnvalue"] = traceTree.internalCalls[ii].internalCalls[0].info["Decoded returnvalue"]
                traceTree.internalCalls[ii].info["Decoded calldata types"] = traceTree.internalCalls[ii].internalCalls[0].info["Decoded calldata types"]
                traceTree.internalCalls[ii].info["Decoded calldata"] = traceTree.internalCalls[ii].internalCalls[0].info["Decoded calldata"]
                traceTree.internalCalls[ii].info["DelegateConverted"] = True




        breakpoints = [] 
        for ii in range(len(traceTree.internalCalls)):
            breakpoints.append( traceTree.internalCalls[ii].info["structLogsStart"] )

        ii_end = traceTree.info["structLogsEnd"]
        breakpointsIndex = 0

        Tracker = tracker(contractAddress) # One contract address, one tracker

        ii = traceTree.info["structLogsStart"] + 1

        DataSourceList = []
        while ii < ii_end + 1:
            pc = structLogs[ii]["pc"]
            if locator.type == FUNCTION or locator.type == FALLBACK:
                # handle call and staticcall
                if breakpointsIndex < len(breakpoints) and ii == breakpoints[breakpointsIndex] and \
                    structLogs[ii]['op'] == "CALL" and "error" not in structLogs[ii]:
                        # gas = Web3.toInt(hexstr = structLogs[ii]["stack"][-1])
                        hex_str = structLogs[ii]["stack"][-1]
                        gas = int(hex_str, 16)
                        addr = structLogs[ii]["stack"][-2]
                        if len(addr) > 42:
                            addr = '0x' + addr[-40:]

                        addr = "0x" + addr[2:].zfill(40)
                        
                        value = structLogs[ii]["stack"][-3]
                        argsOffset = structLogs[ii]["stack"][-4]
                        argsLength = structLogs[ii]["stack"][-5]
                        retOffset = structLogs[ii]["stack"][-6]
                        retLength = structLogs[ii]["stack"][-7]

                        argsLengthInt = int(argsLength, base = 16)
                        argsOffsetInt = int(argsOffset, base = 16)
                        retOffsetInt = int(retOffset, base = 16)
                        retLengthInt = int(retLength, base = 16)
                        info = traceTree.internalCalls[breakpointsIndex].info

                        if locator.type == FALLBACK:
                            if info['name'] != "fallback":
                                pass
                            elif addr.lower() == "0x3f2d1bc6d02522dbcdb216b2e75edddafe04b16f" or \
                                addr.lower() == "0x4ef29407a8dbca2f37b7107eab54d6f2a3f2ad60":
                                pass
                            else:
                                msgValueDataSource = Tracker.stackTracker.stack[-3].getInterval()
                                msgValueDataSource.metaData["value"] = value
                                msgValueDataSource.metaData["gas"] = gas
                                msgValueDataSource.metaData["pc"] = pc
                                DataSourceList.append(msgValueDataSource)


                        elif locator.type == FUNCTION:
                            name = locator.funcName
                            argPosition = locator.argPosition
                            value = None
                            type = None
                            if info['name'] != name:
                                pass
                            elif locator.funcAddress != None and locator.funcAddress != addr:
                                pass
                            else:
                                isMatch = True
                                if len(locator.funcPara) > 0:
                                    calldata = traceTree.internalCalls[breakpointsIndex].info["Decoded calldata"]
                                    for (pos, value) in locator.funcPara:
                                        if calldata[pos] != value:
                                            isMatch = False
                                            break
                                if isMatch:
                                    print("now we arrive at the function call {}, ii = {}".format(name, ii))
                                    value = traceTree.internalCalls[breakpointsIndex].info["Decoded calldata"][argPosition]
                                    type = traceTree.internalCalls[breakpointsIndex].info["Decoded calldata types"][argPosition]

                                    infoInputTypes = info["Decoded calldata types"]
                                    lengths = self.decoder.get_memory_lengths(infoInputTypes, argsLengthInt - 4)  # delete the first 4 bytes(function selector)
                                    # print(lengths)
                                    argMemoryInterval = [argsOffsetInt + 4 + sum(lengths[:argPosition]), argsOffsetInt + 4 + sum(lengths[:argPosition + 1])]
                                    # print(argMemoryInterval)
                                    argsDataSource = Tracker.memoryTracker.getInterval(argMemoryInterval[0], argMemoryInterval[1])
                                    argsDataSource.metaData["value"] = value
                                    argsDataSource.metaData["type"] = type
                                    argsDataSource.metaData["gas"] = gas
                                    argsDataSource.metaData["pc"] = pc

                                    # traceTree.internalCalls[breakpointsIndex]

                                    if len(traceTree.internalCalls[breakpointsIndex].internalCalls) == 1 and \
                                        "type" in traceTree.internalCalls[breakpointsIndex].internalCalls[0].info and \
                                        traceTree.internalCalls[breakpointsIndex].internalCalls[0].info["type"] == 'delegatecall':

                                        info = traceTree.internalCalls[breakpointsIndex].internalCalls[0].info


                                    if name == "transfer" or name == "transferFrom":

                                        # AMP 
                                        if info["addr"] == "0xff20817765cb7f73d4bde2e66e067e58d11095c2":
                                            if len(info["sstore"]) == 9 and name == "transfer":
                                                                                                  # self, receiver
                                                argsDataSource.metaData["sstore"] = [name, info["sstore"][0], info["sstore"][5]]
                                            elif len(info["sstore"]) == 7 and name == "transferFrom":
                                                                                                    # from, to        
                                                argsDataSource.metaData["sstore"] = [name, info["sstore"][1], info["sstore"][4]]
                                            else:
                                                argsDataSource.metaData["sstore"] = ["len(sstore) != 9"] + info["sstore"]
                                        
                                        # WBTC
                                        elif info["addr"] == "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599":
                                            if len(info["sstore"]) == 3 and name == "transferFrom":
                                                argsDataSource.metaData["sstore"] = [name, info["sstore"][0], info["sstore"][1]]
                                            elif len(info["sstore"]) == 2 and name == "transfer":
                                                argsDataSource.metaData["sstore"] = [name, info["sstore"][0], info["sstore"][1]]
                                            else:
                                                argsDataSource.metaData["sstore"] = ["WBTC"] + info["sstore"]

                                        # 3CRV
                                        elif info["addr"] == "0x6c3f90f043a72fa612cbac8115ee7e52bde6e490": 
                                            if name == "transferFrom":
                                                argsDataSource.metaData["sstore"] = [name, info["sstore"][0], info["sstore"][1]]
                                            elif len(info["sstore"]) == 2 and name == "transfer":
                                                argsDataSource.metaData["sstore"] = [name, info["sstore"][0], info["sstore"][1]]
                                            else:
                                                argsDataSource.metaData["sstore"] = ["3CRV"] + info["sstore"]

                                        # USDC
                                        elif "proxy" in info and info["proxy"] == '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48':
                                            if name == "transferFrom":
                                                argsDataSource.metaData["sstore"] = [name, info["sstore"][0], info["sstore"][1]]
                                            elif len(info["sstore"]) == 2 and name == "transfer":
                                                argsDataSource.metaData["sstore"] = [name, info["sstore"][0], info["sstore"][1]]
                                            else:
                                                argsDataSource.metaData["sstore"] = ["USDC"] + info["sstore"]
                                        
                                        # Visor
                                        elif info["addr"] == "0xf938424f7210f31df2aee3011291b658f872e91e":
                                            if name == "transferFrom":
                                                argsDataSource.metaData["sstore"] = [name, info["sstore"][0], info["sstore"][1]]
                                            elif len(info["sstore"]) == 2 and name == "transfer":
                                                argsDataSource.metaData["sstore"] = [name, info["sstore"][0], info["sstore"][1]]
                                            else:
                                                argsDataSource.metaData["sstore"] = ["Visor"] + info["sstore"]

                                        # UNI
                                        # transferFrom   optional: allowances[src][spender] = newAllowance; 
                                        #                 balances[src] = sub96(balances[src], amount, "Uni::_transferTokens: transfer amount exceeds balance");
                                        #                 balances[dst] = add96(balances[dst], amount, "Uni::_transferTokens: transfer amount overflows");
                                        #                optional: _writeCheckpoint(srcRep, srcRepNum, srcRepOld, srcRepNew);
                                        #                optional: _writeCheckpoint(dstRep, dstRepNum, dstRepOld, dstRepNew);
                                        elif info["addr"] == "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984":
                                            if len(info["sstore"]) == 4 and name == "transferFrom":
                                                argsDataSource.metaData["sstore"] = [name, info["sstore"][1], info["sstore"][2]]
                                            elif len(info["sstore"]) == 3 and name == "transferFrom":
                                                argsDataSource.metaData["sstore"] = [name, info["sstore"][0], info["sstore"][1]]
                                            elif name == "transfer":
                                                argsDataSource.metaData["sstore"] = [name, info["sstore"][0], info["sstore"][1]]



                                        elif "sstore" in info and len(info["sstore"]) == 2  and name == "transfer":
                                            argsDataSource.metaData["sstore"] = [name, info["sstore"][0], info["sstore"][1]]
                                        elif "sstore" in info and len(info["sstore"]) == 3  and name == "transferFrom":
                                            argsDataSource.metaData["sstore"] = [name, info["sstore"][1], info["sstore"][2]]
                                        elif "sstore" in info and len(info["sstore"]) == 2  and name == "transferFrom":
                                            argsDataSource.metaData["sstore"] = [name, info["sstore"][0], info["sstore"][1]]
                                        elif "sstore" in info:
                                            argsDataSource.metaData["sstore"] = ["wrong", name] + info["sstore"]


                                    DataSourceList.append(argsDataSource)
                                    # print(argsDataSource)
                                    # return argsDataSource


            if breakpointsIndex < len(breakpoints) and ii == breakpoints[breakpointsIndex]:
                # print("reached breakpoint")

                info = traceTree.internalCalls[breakpointsIndex].info
                retOffset = info["retOffset"]
                retLength = info["retLength"]
                retOffsetInt = int(retOffset, base = 16)
                retLengthInt = int(retLength, base = 16)
                if not self.noprint:
                    print("\t", info["name"], "is stored in mem[{}:{}]".format(retOffsetInt, retOffsetInt + retLengthInt) )
                
                Tracker.trackCall(structLogs[ii], info)
                # do something
                ii = info["structLogsEnd"] + 1
                breakpointsIndex += 1
                pass

            lastStructLog = structLogs[ii - 1]
            # print("last op: ", lastStructLog["op"])
            thisStructLog = structLogs[ii]
            # print("this op: ", thisStructLog["op"])
            if ii == ii_end:
                if len(DataSourceList) > 0:
                    return DataSourceList
                else:
                    print("warning: tracker reach the end but no target found")
                    return []
            nextStructLog = structLogs[ii + 1]
            # print("next op: ", nextStructLog["op"])
        
            error = Tracker.stackTrack(structLogs[ii], nextStructLog = structLogs[ii + 1], info = traceTree.info)
            # if len(structLogs[ii + 1]["stack"]) != len(Tracker.stackTracker.stack) and ii != ii_end:
            #     print("last opcode: ", lastStructLog)
            #     print("this opcode: ", thisStructLog)
            #     print("next opcode: ", nextStructLog)
            #     print("ii = ", ii)
            #     sys.exit("Parser Error: stackTrack.stack is not the same length as structLogs[ii + 1]['stack']! txHash = {}".format(self.txHash))

            if len(structLogs[ii + 1]["stack"]) > len(Tracker.stackTracker.stack) and ii != ii_end:
                sys.exit("Parser Error: stackTrack.stack is too short! txHash = {}".format(self.txHash))

            if error == "Error":
                return []
            ii += 1


furtherExpandable = ["calculateSaleReturn"]

proxyMap = {
    "0xf0358e8c3cd5fa238a29301d0bea3d63a17bedbe": "0x9b3be0cc5dd26fd0254088d03d8206792715588b",  # USDC vault: Harvest Finance
    "0x053c80ea73dc6941f518a68e2fc52ac45bde7c9c": "0x9b3be0cc5dd26fd0254088d03d8206792715588b",  # USDT valut: Harvest Finance
    "0x2db6c82ce72c8d7d770ba1b5f5ed0b6e075066d6": "0x3c710b981f5ef28da1807ce7ed3f2a28580e0754",  # Cream.Finance1: crAMP Token
    "0x44fbebd2f576670a6c33f6fc0b00aa8c5753b322": "0x3c710b981f5ef28da1807ce7ed3f2a28580e0754",  # Cream.Finance2: crYUSD Token
    "0x797aab1ce7c01eb727ab980762ba88e7133d2157": "0x3c710b981f5ef28da1807ce7ed3f2a28580e0754",  # Cream.Finance2: crUSDT Token
    "0xe89a6d0509faf730bd707bf868d9a2a744a363c7": "0x3c710b981f5ef28da1807ce7ed3f2a28580e0754",  # Cream.Finance2: crUNI Token 
    "0x8c3b7a4320ba70f8239f83770c4015b5bc4e6f91": "0x3c710b981f5ef28da1807ce7ed3f2a28580e0754",  # Cream.Finance2: crFEI Token
    "0x3a70dfa7d2262988064a2d051dd47521e43c9bdd": "0x5f890841f657d90e081babdb532a05996af79fe6",  # BeanstalkFarms: BEAN3CRV-f
    "0xd652c40fbb3f06d6b58cb9aa9cff063ee63d465d": "0x6523ac15ec152cb70a334230f6c5d62c5bd963f1",  # BeanstalkFarms: BEANLUSD-f
    "0x26267e41ceca7c8e0f143554af707336f27fa051": "0xd77e28a1b9a9cfe1fc2eee70e391c05d25853cbf",  # RariCapital2_1: fETH
    "0xebe0d1cb6a0b8569929e062d67bfbc07608f0a47": "0x67db14e73c2dce786b5bbbfa4d010deab4bbfcf9",  # RariCapital2_1: fUSDC
    "0xe097783483d1b7527152ef8b150b99b9b2700c8d": "0x67db14e73c2dce786b5bbbfa4d010deab4bbfcf9",  # RariCapital2_1: fUSDT
    "0x8922c1147e141c055fddfc0ed5a119f3378c8ef8": "0x67db14e73c2dce786b5bbbfa4d010deab4bbfcf9",  # RariCapital2_1: fFrax
    "0x88a69b4e698a4b090df6cf5bd7b2d47325ad30a3": "0x15fda9f60310d09fea54e3c99d1197dff5107248",  # Nomad bridge: WBTC
    "0x051ebd717311350f1684f89335bed4abd083a2b6": "0x2bbd66fc4898242bdbd2583bbe1d76e8b8f71445",  # DODO
    "0xc1e088fc1323b20bcbee9bd1b9fc9546db5624c5": "0xf480ee81a54e21be47aa02d0f9e29985bc7667c4",  # BeanstalkFarms interface
}

NOPRINT = True
def analyzeOneTx(contract, Tx, path, depositLocators, investLocators, withdrawLocators):

    if Tx.lower() == "0x5282d512c2dafa117ca97f7d0fc052e2ac716b87c06113246a5e5a8cad67c156" \
        or Tx.lower() == "0x58c5eb412f4d0e88d32eba118e74efe438baaeec300d8c28a390e454af996afe":
        return [], [], []

    proxy = None
    if contract in proxyMap:
        proxy = contract
        contract = proxyMap[contract]

    p = VmtraceParser()
    # print(path)
    trace = None
    if path.endswith(".json"):
        trace = readJson(path)
    elif path.endswith(".gz"):
        trace = readCompressedJson(path)

    targetFuncs = []
    for ilocator in (depositLocators + investLocators + withdrawLocators):
        if ilocator is not None and ilocator.targetFunc is not None:
            targetFuncs.append(ilocator.targetFunc)

    metaTraceTree = None
    if proxy is not None and contract == "0x3c710b981f5ef28da1807ce7ed3f2a28580e0754":
        metaTraceTree = p.parseLogs(proxy, Tx, trace)
    else:
        metaTraceTree = p.parseLogs(contract, Tx, trace)

    if isinstance(metaTraceTree, dict) and "status" in metaTraceTree and metaTraceTree["status"] == 0:
        return [], [], []
    splitedTraceTree = metaTraceTree.splitTraceTree(contract, proxy)
    accessList = []
    for traceTree in splitedTraceTree:
        accessList.append(traceTree.info)

    # print("len(splitedTraceTree): ", len(splitedTraceTree))
    a = Analyzer()
    funcSigMap = a.contract2funcSigMap(contract)
    selectors = []
    for key in funcSigMap.keys():
        if funcSigMap[key][0] in targetFuncs:
            selectors.append(key)
    traceStr = str(trace)
    found = False
    for selector in selectors:
        if selector in traceStr:
            found = True
            break
    if not found:
        unifySelectors(accessList)
        return [], accessList, splitedTraceTree


    executionList = []
    for traceTree in splitedTraceTree:
        # if traceTree.info["name"] == "exchange" :
        #     print("now is the time")
        if traceTree.info["name"] == "fallback" and traceTree.info["Selector"] != "0x":
            funcSigMap = a.contract2funcSigMap(contract)
            traceTree.info["name"] = funcSigMap[traceTree.info["Selector"].lower()][0]
        

        if "name" in traceTree.info and traceTree.info["name"] in targetFuncs and traceTree.info["addr"].lower() == contract.lower():
            thisLocator = None
            for ilocator in (depositLocators + investLocators + withdrawLocators):
                if ilocator is not None and ilocator.targetFunc == traceTree.info["name"]:
                    thisLocator = ilocator
                    if not NOPRINT:
                        print("Now work on function: ", traceTree.info["name"], "starting ii = ", traceTree.info["structLogsStart"])
                    dataSources = []
                    if thisLocator.type == SELFCALLVALUE:
                        dataS = dataSource("msg.value")
                        dataS.metaData = traceTree.info
                        dataSources = [dataS]
                    else:
                        dataSources = p.track(contract, traceTree, thisLocator, trace)
                    if not NOPRINT:
                        print("dataSources: ")
                        for dataS in dataSources:
                            print(dataS)
                    if isinstance(dataSources, list) and len(dataSources) == 0:
                        continue
                    for dataS in dataSources:
                        dataS.metaData["targetFunc"] = traceTree.info["name"]
                        dataS.metaData['msg.sender'] = traceTree.info['msg.sender']
                        dataS.metaData['tx.origin'] =  metaTraceTree.info['origin']

                        for ii in range(3):
                            locators = [depositLocators, investLocators, withdrawLocators][ii]
                            if len(locators) > 0:
                                for ilocator in locators:
                                    if ilocator is not None and ilocator.targetFunc == traceTree.info["name"]:
                                        if ii == 0:
                                            dataS.metaData["targetFuncType"] = "deposit"
                                        elif ii == 1:
                                            dataS.metaData["targetFuncType"] = "invest"
                                        elif ii == 2:
                                            dataS.metaData["targetFuncType"] = "withdraw"
                                        break
                                if "targetFuncType" in dataS.metaData:
                                    break
                        if "targetFuncType" not in dataS.metaData:
                            sys.exit("Error: targetFuncType not in dataSource.metaData")

                        toPop = []
                        for ii in range(len(dataS.sources)):
                            childDataSource = dataS.sources[ii]
                            if not isinstance(childDataSource, dict):
                                continue
                            if  "Selector" in childDataSource and childDataSource["name"] in furtherExpandable:
                                # delete dataS.sources[ii]
                                toPop.append(ii)
                        for ii in reversed(toPop):
                            dataS.sources.pop(ii)
                            dataS.children.pop(ii)
                    executionList.append(dataSources)

                  
    unifySelectors(accessList)

    return executionList, accessList, splitedTraceTree