import sys
import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from utilsPackage.compressor import writeCompressedJson, readCompressedJson

from parserPackage.decoder import decoder
from trackerPackage.dataSource import *
from staticAnalyzer.analyzer import Analyzer
from trackerPackage.memoryTracker import *
from trackerPackage.storageTracker import *
from trackerPackage.stackTracker import *



class tracker:
    # one tracker for one function calls, excluding internal calls
    # -func1(tracker1)
    # --------func2(tracker2)
    # --------------func3(tracker3)
    # -------------------------

    
    def __init__(self, currentContract: str, indent: int = 0) -> None:
        self.currentContract = currentContract
        # self.storageMapping = self.analyzer.contract2storageMapping(currentContract)
        self.indent = indent

        self.preimage = {}

        self.storageTracker = storageTracker()
        self.memoryTracker = memoryTracker()
        self.stackTracker = stackTracker()
        self.decoder = decoder()
        self.analyzer = Analyzer()

        # some special parameters
        self.caller = None
        self.origin = None
        self.address = None
        self.info = None
        self.returndata = {} 
        self.stateChanges = [] # This is what we want at the end of the data flow analysis

        # storageMapping: {0: ('Ownable._owner', 'address'), 32: ('Pausable.pauser', 'address'), 52: ('Pausable.paused', 'bool'), 64: ('Blacklistable.blacklister', 'address'), 96: ('Blacklistable.blacklisted', ('address', 'bool')), 128: ('FiatTokenV1.name', 'string'), 160: ('FiatTokenV1.symbol', 'string'), 192: ('FiatTokenV1.decimals', 'uint8'), 224: ('FiatTokenV1.currency', 'string'), 256: ('FiatTokenV1.masterMinter', 'address'), 276: ('FiatTokenV1.initialized', 'bool'), 288: ('FiatTokenV1.balances', ('address', 'uint256')), 320: ('FiatTokenV1.allowed', ('address', ('address', 'uint256'))), 352: ('FiatTokenV1.totalSupply_', 'uint256'), 384: ('FiatTokenV1.minters', ('address', 'bool')), 416: ('FiatTokenV1.minterAllowed', ('address', 'uint256')), 448: ('Rescuable._rescuer', 'address'), 480: ('EIP712Domain.DOMAIN_SEPARATOR', 'bytes32'), 512: ('GasAbstraction.TRANSFER_WITH_AUTHORIZATION_TYPEHASH', 'bytes32'), 544: ('GasAbstraction.APPROVE_WITH_AUTHORIZATION_TYPEHASH', 'bytes32'), 576: ('GasAbstraction.INCREASE_ALLOWANCE_WITH_AUTHORIZATION_TYPEHASH', 'bytes32'), 608: ('GasAbstraction.DECREASE_ALLOWANCE_WITH_AUTHORIZATION_TYPEHASH', 'bytes32'), 640: ('GasAbstraction.CANCEL_AUTHORIZATION_TYPEHASH', 'bytes32'), 672: ('GasAbstraction._authorizationStates', ('address', ('bytes32', 'GasAbstraction.AuthorizationState'))), 704: ('Permit.PERMIT_TYPEHASH', 'bytes32'), 736: ('Permit._permitNonces', ('address', 'uint256')), 768: ('FiatTokenV2._initializedV2', 'bool')}
        # ====> Used to reason about types
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
        # ====> Used to reason about sload/sstore keys

    def find(self, name: str):
        for item in self.stackTracker.stack:
            if item.find(name):
                return True
        if self.memoryTracker.find(name):
            return True
        return False
    
    def printStack(self):
        print("{")
        for item in self.stackTracker.stack:
            print("\t", item)
        print("}")

    def getStack(self):
        returnArr = []
        for item in self.stackTracker.stack:
            returnArr.append(item.__str__())
        return returnArr

    def printIndentContent(self, *values: object):
        """Given an indent and a content, print the content with the indent"""
        for _ in range(self.indent - 1):
            print("\t", end = '')
        print(*values)
        
    def trackCall(self, structLog, info, nextStructLog = None):
        '''
        trackCall: collect call information
        info is a info dict from traceTree
        {'type': 'call', 'structLogsStart': 47245, 'gas': 1340855, \
                        'addr': '0x5ade7ae8660293f2ebfcefaba91d141d72d221e8', \
                        'msg.value': '0x0', 'msg.sender': '0x3882a1e71636c4d5896af656793cb358e6e9713f', \
                        'retOffset': '0x80', 'retLength': '0x20', 'structLogsEnd': 49641, \
                        'name': 'sell', 'Selector': '0xd79875eb', 
                        'Decoded returnvalue types': ['uint256'], \
                        'Decoded returnvalue': [7075278925487910960029682], 
                        'Decoded calldata types': ['uint256', 'uint256'], \
                        'Decoded calldata': [867220366005357465624543947, 0]}, 
                                                     
        "nextStructLog is solely for double checking "
        '''
        opcode = structLog["op"]
        depth = structLog["depth"]
        pc = structLog["pc"]
        self.info = info

        if opcode == "STATICCALL":
            gas = structLog["stack"][-1]
            addr = structLog["stack"][-2]
            argsOffset = structLog["stack"][-3]
            argsLength = structLog["stack"][-4]
            retOffset = structLog["stack"][-5]
            retLength = structLog["stack"][-6]

            if retOffset != info['retOffset'] or retLength != info['retLength']:
                sys.exit("Tracker Error: retOffset {} retLength {} not equal to info retOffset {} retLength {}".format(retOffset, retLength, info['retOffset'], info['retLength']))

            funcSpec = {"name": info["name"], "inputs": info['Decoded calldata'], \
                        "inputTypes": info["Decoded calldata types"], \
                        "outputs": info['Decoded returnvalue'], \
                        "outputTypes": info["Decoded returnvalue types"], \
                        "Selector": info["Selector"], \
                        "structLogsStart": info["structLogsStart"],
                        "structLogsEnd": info["structLogsEnd"],
                        "addr": addr,  "gas":  gas, "pc": pc
                        }
            argsLengthInt = int(argsLength, base = 16)
            argsOffsetInt = int(argsOffset, base = 16)
            dataSrcInfo = self.memoryTracker.getInterval(argsOffsetInt, argsOffsetInt + argsLengthInt)
            dataS = dataSource(funcSpec)

            dataS.merge(dataSrcInfo)
            for ii in range(len(funcSpec['inputs'])):
                if funcSpec['inputs'][ii] == self.caller and any("CALLER" in sublist for sublist in dataSrcInfo.sources):
                    funcSpec['inputs'][ii] = "CALLER-{}".format(self.caller)
                    # remove CALLER from dataS
                    dataS.remove("CALLER")
                if funcSpec['inputs'][ii] == self.address and any("ADDRESS" in sublist for sublist in dataSrcInfo.sources):
                    funcSpec['inputs'][ii] = "ADDRESS-{}".format(self.address)
                    # remove ADDRESS from dataS
                    dataS.remove("ADDRESS")
                if funcSpec['inputs'][ii] == self.origin and any("ORIGIN" in sublist for sublist in dataSrcInfo.sources):
                    funcSpec['inputs'][ii] = "ORIGIN-{}".format(self.origin)
                    # remove ORIGIN from dataS
                    dataS.remove("ORIGIN")
            retOffsetInt = int(retOffset, base = 16)
            retLengthInt = int(retLength, base = 16)

            if info["name"] != "fallback":
                self.memoryTracker.overwriteInterval(retOffsetInt, retOffsetInt + retLengthInt, dataS)

            if retLengthInt != 0: # if retLengthInt == 0, then the return value is ignored, likely to be a fallback function
                self.returndata[depth] = (retLengthInt, dataS)

            self.stackTracker.pop(6)
            entry = stackEntry(32)
            entry.addInterval(31, 32, dataS)
            self.stackTracker.push( entry )
            pass

        elif opcode == "CALL":
            gas = structLog["stack"][-1]
            addr = structLog["stack"][-2]
            value = structLog["stack"][-3]
            argsOffset = structLog["stack"][-4]
            argsLength = structLog["stack"][-5]
            retOffset = structLog["stack"][-6]
            retLength = structLog["stack"][-7]
            if value != info['msg.value'] or retOffset != info['retOffset'] or retLength != info['retLength']:
                sys.exit("Tracker Error: value {} retOffset {} retLength {} not equal to info value {} retOffset {} retLength {}".format(value, retOffset, retLength, info['msg.value'], info['retOffset'], info['retLength']))

            funcSpec = {"name": info["name"], 
                        'msg.value': info['msg.value'], \
                        "structLogsStart": info["structLogsStart"],
                        "structLogsEnd": info["structLogsEnd"],
                        "addr": addr
                        }
            if "Decoded calldata" in info:
                funcSpec["inputs"] = info["Decoded calldata"]
            if "Decoded calldata types" in info:
                funcSpec["inputTypes"] = info["Decoded calldata types"]
            if "Decoded returnvalue" in info:
                funcSpec["outputs"] = info["Decoded returnvalue"]
            if "Decoded returnvalue types" in info:
                funcSpec["outputTypes"] = info["Decoded returnvalue types"]
            if "Selector" in info:
                funcSpec["Selector"] = info["Selector"]
            if "inputs" in info:
                funcSpec["inputs"] = info["inputs"]
            funcSpec["gas"] = gas
            funcSpec["pc"] = pc

            argsLengthInt = int(argsLength, base = 16)
            argsOffsetInt = int(argsOffset, base = 16)
            dataSrcInfo = self.memoryTracker.getInterval(argsOffsetInt, argsOffsetInt + argsLengthInt)
            dataS = dataSource(funcSpec)
            dataS.merge(dataSrcInfo)

            for ii in range(len(funcSpec['inputs'])):
                if funcSpec['inputs'][ii] == self.caller and any("CALLER" in sublist for sublist in dataSrcInfo.sources):
                    funcSpec['inputs'][ii] = "CALLER-{}".format(self.caller)
                    # remove CALLER from dataS
                    dataS.remove("CALLER")
                if funcSpec['inputs'][ii] == self.address and any("ADDRESS" in sublist for sublist in dataSrcInfo.sources):
                    funcSpec['inputs'][ii] = "ADDRESS-{}".format(self.address)
                    # remove ADDRESS from dataS
                    dataS.remove("ADDRESS")
                if funcSpec['inputs'][ii] == self.origin and any("ORIGIN" in sublist for sublist in dataSrcInfo.sources):
                    funcSpec['inputs'][ii] = "ORIGIN-{}".format(self.origin)
                    # remove ORIGIN from dataS
                    dataS.remove("ORIGIN")

            retOffsetInt = int(retOffset, base = 16)
            retLengthInt = int(retLength, base = 16)
            if info["name"] != "fallback":
                self.memoryTracker.overwriteInterval(retOffsetInt, retOffsetInt + retLengthInt, dataS)

            if retLengthInt != 0: # if retLengthInt == 0, then the return value is ignored, likely to be a fallback function
                self.returndata[depth] = (retLengthInt, dataS)
            self.stackTracker.pop(7)
            entry = stackEntry(32)
            entry.addInterval(31, 32, dataS)
            self.stackTracker.push( entry )
            pass
        
        elif opcode == "DELEGATECALL":   # means executing arbitrary code in the context of the addr
            gas = structLog["stack"][-1]
            addr = structLog["stack"][-2]
            argsOffset = structLog["stack"][-3]
            argsLength = structLog["stack"][-4]
            retOffset = structLog["stack"][-5]
            retLength = structLog["stack"][-6]

            if retOffset != info['retOffset'] or retLength != info['retLength']:
                sys.exit("Tracker Error: retOffset {} retLength {} not equal to info retOffset {} retLength {}".format(retOffset, retLength, info['retOffset'], info['retLength']))


            funcSpec = {"name": info["name"], "inputs": info['Decoded calldata'], \
                        "inputTypes": info["Decoded calldata types"], \
                        "outputs": info['Decoded returnvalue'], \
                        "outputTypes": info["Decoded returnvalue types"], \
                        "Selector": info["Selector"], \
                        "structLogsStart": info["structLogsStart"],
                        "structLogsEnd": info["structLogsEnd"],
                        "addr": addr,  "gas":  gas, "pc": pc
                        }
            
            argsLengthInt = int(argsLength, base = 16)
            argsOffsetInt = int(argsOffset, base = 16)
            dataSrcInfo = self.memoryTracker.getInterval(argsOffsetInt, argsOffsetInt + argsLengthInt)
            dataS = dataSource(funcSpec)

            dataS.merge(dataSrcInfo)


            for ii in range(len(funcSpec['inputs'])):
                if funcSpec['inputs'][ii] == self.caller and any("CALLER" in sublist for sublist in dataSrcInfo.sources):
                    funcSpec['inputs'][ii] = "CALLER-{}".format(self.caller)
                    # remove CALLER from dataS
                    dataS.remove("CALLER")
                if funcSpec['inputs'][ii] == self.address and any("ADDRESS" in sublist for sublist in dataSrcInfo.sources):
                    funcSpec['inputs'][ii] = "ADDRESS-{}".format(self.address)
                    # remove ADDRESS from dataS
                    dataS.remove("ADDRESS")
                if funcSpec['inputs'][ii] == self.origin and any("ORIGIN" in sublist for sublist in dataSrcInfo.sources):
                    funcSpec['inputs'][ii] = "ORIGIN-{}".format(self.origin)
                    # remove ORIGIN from dataS
                    dataS.remove("ORIGIN")


            retOffsetInt = int(retOffset, base = 16)
            retLengthInt = int(retLength, base = 16)

            if info["name"] != "fallback":
                self.memoryTracker.overwriteInterval(retOffsetInt, retOffsetInt + retLengthInt, dataS)

            if retLengthInt != 0: # if retLengthInt == 0, then the return value is ignored, likely to be a fallback function
                self.returndata[depth] = (retLengthInt, dataS)

            self.stackTracker.pop(6)
            entry = stackEntry(32)
            entry.addInterval(31, 32, dataS)
            self.stackTracker.push( entry )
            pass

        else:
            sys.exit("Tracker Error: trackCall() called with opcode {}".format(opcode))




    def stackTrack(self, structLog, nextStructLog = None, tags = None, info = None) -> None:
        opcode = structLog["op"]
        depth = structLog["depth"]
        pc = structLog["pc"]
        # for masking
        # Binary   | Hex
        # 0000     | 0x0
        # 0011     | 0x3
        # 1100     | 0xc
        # 1111     | 0xf

        def contains_only_f_and_0(string):
            valid_chars = set('f0')
            return set(string) <= valid_chars
        
        def contains_only_0(string):
            valid_chars = set('0')
            return set(string) <= valid_chars
        
        def contains_only_f(string):
            valid_chars = set('f')
            return set(string) <= valid_chars

        if opcode == "AND":
            # handle 0xffffffffffffffffffffffffffffffffffffffff
            # handle 0xffffffff00000000000000000000000000000000000000000000000000000000
            first = structLog["stack"][-1]
            second = structLog["stack"][-2]
            firstEntry = self.stackTracker.stack[-1]
            secondEntry = self.stackTracker.stack[-2]

            if contains_only_f(first[2:]):
                length = len(first[2:])
                # if length % 2 != 0:
                #     sys.exit("Tracker Error: AND with length % 2 != 0")
                self.stackTracker.pop(2)
                removeLength = int(32 - length / 2)
                secondEntry.removeInterval(0, removeLength)
                self.stackTracker.push( secondEntry )

            elif contains_only_f(second[2:]):
                length = len(second[2:])
                # if length % 2 != 0:
                #     sys.exit("Tracker Error: AND with length % 2 != 0")
                self.stackTracker.pop(2)
                removeLength = int(32 - length / 2)
                firstEntry.removeInterval(0, removeLength)
                self.stackTracker.push( firstEntry )
            elif first ==  "0xffffffff00000000000000000000000000000000000000000000000000000000":
                self.stackTracker.pop(2)
                secondEntry.removeInterval(4, 32)
                self.stackTracker.push( secondEntry )
            elif second == "0xffffffff00000000000000000000000000000000000000000000000000000000":
                self.stackTracker.pop(2)
                firstEntry.removeInterval(4, 32)
                self.stackTracker.push( firstEntry )
            elif first ==  "0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff00":
                self.stackTracker.pop(2)
                secondEntry.removeInterval(31, 32)
                self.stackTracker.push( secondEntry )
            elif second == "0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff00":
                self.stackTracker.pop(2)
                firstEntry.removeInterval(31, 32)
                self.stackTracker.push( firstEntry )
            elif first ==  "0xffffffffffffffffffffffffff000000000000000000000000ffffffffffffff":
                self.stackTracker.pop(2)
                secondEntry.removeInterval(13, 25)
                self.stackTracker.push( secondEntry )
            elif second == "0xffffffffffffffffffffffffff000000000000000000000000ffffffffffffff":
                self.stackTracker.pop(2)
                firstEntry.removeInterval(13, 25)
                self.stackTracker.push( firstEntry ) 
            elif first ==  "0xffffffffffffffffffffffffffffffffffffffffffffffffff0000000000ffff":
                self.stackTracker.pop(2)
                secondEntry.removeInterval(25, 30)
                self.stackTracker.push( secondEntry )
            elif second == "0xffffffffffffffffffffffffffffffffffffffffffffffffff0000000000ffff":
                self.stackTracker.pop(2)
                firstEntry.removeInterval(25, 30)
                self.stackTracker.push( firstEntry )
            elif first ==  "0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff00ff":
                self.stackTracker.pop(2)
                secondEntry.removeInterval(30, 31)
                self.stackTracker.push( secondEntry )
            elif second == "0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff00ff":
                self.stackTracker.pop(2)
                firstEntry.removeInterval(30, 31)
                self.stackTracker.push( firstEntry )
            elif first ==  "0xffffffffffffffffffffffff0000000000000000000000000000000000000000":
                self.stackTracker.pop(2)
                secondEntry.removeInterval(12, 32)
                self.stackTracker.push( secondEntry )
            elif second == "0xffffffffffffffffffffffff0000000000000000000000000000000000000000":
                self.stackTracker.pop(2)
                firstEntry.removeInterval(12, 32)
                self.stackTracker.push( firstEntry )
            elif first  == "0xff000000000000000000000000ffffffffffffffffffffffffffffffffffffff":
                self.stackTracker.pop(2)
                secondEntry.removeInterval(1, 13)
                self.stackTracker.push( secondEntry )
            elif second == "0xff000000000000000000000000ffffffffffffffffffffffffffffffffffffff":
                self.stackTracker.pop(2)
                firstEntry.removeInterval(1, 13)
                self.stackTracker.push( firstEntry )
            elif contains_only_f_and_0(first[2:]):
                self.stackTracker.pop(2)
                # calculate how many 0 junks
                counter = 0
                start = 0
                end = 0
                last = "f"
                for i in range(len(first[2:])):
                    if first[2:][i] == "0" and last == "f":
                        start = i
                        counter += 1
                    last = first[2:][i]
                    if last == "0":
                        end = i
                if counter > 1:
                    print("first: ", first)
                    print("second: ", second)
                    sys.exit("Tracker Error: AND with 0x0 or 0xf")
                else:
                    secondEntry.removeInterval( int(start/2), int((end+1)/2) )
                self.stackTracker.push( secondEntry )


            elif contains_only_f_and_0(second[2:]):
                self.stackTracker.pop(2)
                # calculate how many 0 junks
                counter = 0
                start = 0
                end = 0
                last = "f"
                for i in range(len(second[2:])):
                    if second[2:][i] == "0" and last == "f":
                        start = i
                        counter += 1
                    last = second[2:][i]
                    if last == "0":
                        end = i
                if counter > 1:
                    print("first: ", first)
                    print("second: ", second)
                    sys.exit("Tracker Error: AND with 0x0 or 0xf")
                else:
                    firstEntry.removeInterval( int(start/2), int((end+1)/2) )
                self.stackTracker.push( firstEntry )

            else:
                self.stackTracker.merge_last_n(2, 32)

        elif opcode == "OR":
            self.stackTracker.merge_last_n(2, 32)
            pass
        
        elif opcode == "XOR":
            # we assume XOR is never used in masking
            self.stackTracker.merge_last_n(2, 32)
            pass

        elif opcode == "ADD" or opcode == "MUL" or opcode == "SUB" \
            or opcode == "DIV" or opcode == "SDIV" or opcode == "MOD" \
            or opcode == "SMOD" or opcode == "EXP" or opcode == "SIGNEXTEND":
            if self.stackTracker.stack[-1].length != 32 or  self.stackTracker.stack[-2].length != 32:
                print(self.stackTracker.stack[-1])
                print(self.stackTracker.stack[-2])
                sys.exit("Tracker Error: {} with length != 32".format(opcode))
            self.stackTracker.merge_last_n(2, 32)

        elif opcode == "LT" or opcode == "GT" or opcode == "SLT" or opcode == "SGT" or opcode == "EQ":
            if self.stackTracker.stack[-1].length != 32 or  self.stackTracker.stack[-2].length != 32:
                print(self.stackTracker.stack[-1])
                print(self.stackTracker.stack[-2])
                sys.exit("Tracker Error: {} with length != 32".format(opcode))       
            self.stackTracker.merge_last_n(2, 32)

        elif opcode == "BYTE": 
            i = structLog["stack"][-1]
            x = structLog["stack"][-2]

            int_i = int(i, base = 16) # 31 -> last two bytes 31-32
                                      # 30 -> second last two bytes 30-31
            firstEntry = self.stackTracker.stack[-1]
            secondEntry = self.stackTracker.stack[-2]
            self.stackTracker.pop(2)

            dataSrc = secondEntry.getInterval(int_i, int_i + 1)

            entry = stackEntry(32)
            entry.addInterval(31, 32, dataSrc)
            self.stackTracker.push( entry )


        elif opcode == "SHL":   
            shift = structLog["stack"][-1]
            value = structLog["stack"][-2]

            shiftInt = int(shift, base = 16)
            # if shiftInt % 8 != 0:
            #     sys.exit("Tracker Error: SHL with shift % 8 != 0 but == {}".format(shiftInt))
            firstEntry = self.stackTracker.stack[-1]
            secondEntry = self.stackTracker.stack[-2]
            self.stackTracker.pop(2)

            secondEntry.shiftInterval( (-1) * (shiftInt / 8) )
            self.stackTracker.push( secondEntry )
            
            
        elif opcode == "SHR":
            shift = structLog["stack"][-1]
            value = structLog["stack"][-2]
            shiftInt = int(shift, base = 16)
            firstEntry = self.stackTracker.stack[-1]
            secondEntry = self.stackTracker.stack[-2]
            self.stackTracker.pop(2)
            secondEntry.shiftInterval( (shiftInt / 8) )
            self.stackTracker.push( secondEntry )
            
        elif opcode == "SAR":
            self.stackTracker.merge_last_n(2, 32)
            pass


        elif opcode == "ADDMOD" or opcode == "MULMOD":
            if self.stackTracker.stack[-1].length != 32 or self.stackTracker.stack[-2].length != 32 or self.stackTracker.stack[-3].length != 32:
                print(self.stackTracker.stack[-1])
                print(self.stackTracker.stack[-2])
                sys.exit("Tracker Error: {} with length != 32".format(opcode))
            self.stackTracker.merge_last_n(3, 32)

        elif opcode == "ISZERO" or opcode == "NOT":
            if self.stackTracker.stack[-1].length != 32:
                sys.exit("Tracker Error: {} with length != 32".format(opcode))
            self.stackTracker.merge_last_n(1, 32)


        elif opcode == "SHA3" or opcode == "KECCAK256":
            # hash = keccak256(memory[offset:offset+length])
            offset = structLog["stack"][-1]
            length = structLog["stack"][-2]
            if length == "0x0":
                sys.exit("tracker: Error! SHA3 with length 0x0")

            key = self.decoder.extractMemory(structLog["memory"], offset, length)

            offsetInt = int(offset, base = 16)
            lengthInt = int(length, base = 16)
            dataSrcInfo = self.memoryTracker.getInterval(offsetInt, offsetInt + lengthInt)

            hashValue = nextStructLog["stack"][-1]

            # remove 0x from hashValue and add padding 0s
            hashValue = hashValue[2:]
            hashValue = "0" * (64 - len(hashValue)) + hashValue
            hashValue = "0x" + hashValue
            self.stackTracker.pop(2)

            if len(key) == 128:
                currentContract = self.currentContract
                # if self.storageMapping is None:
                #     sys.exit("Tracker: Error! currentContract not in storageMappingMap")
                mappingSlot = None
                if self.analyzer.isVyper(currentContract):
                    mapPositionHex = key[0:64]
                    mappingSlot = key[64:]
                    self.preimage[hashValue] = ("Vyper", mapPositionHex, mappingSlot)
                    # print("mapping storage position of Vyper = ", mapPositionHex)
                else:
                    mapPositionHex = key[64:]
                    mappingSlot = key[:64]
                    self.preimage[hashValue] = ("Solc", mapPositionHex, mappingSlot)

                specialValue = None

                if self.caller is not None and int(mappingSlot, 16) == int(self.caller, 16) and any("CALLER" in sublist for sublist in dataSrcInfo.sources):
                    specialValue = "CALLER-{}".format(mappingSlot)
                elif self.address is not None and int(mappingSlot, 16) == int(self.address, 16) and any("ADDRESS" in sublist for sublist in dataSrcInfo.sources):
                    specialValue = "ADDRESS-{}".format(mappingSlot)
                elif self.origin is not None and int(mappingSlot, 16) == int(self.origin, 16) and any("ORIGIN" in sublist for sublist in dataSrcInfo.sources):
                    specialValue = "ORIGIN-{}".format(mappingSlot)
                
                if isinstance(dataSrcInfo.sources, list) and len(dataSrcInfo.sources) == 1:
                    if isinstance( dataSrcInfo.sources[0], tuple) and dataSrcInfo.sources[0][0] == "msg.data":
                        specialValue = "msg.data[{}:{}]-{}".format(dataSrcInfo.sources[0][1], dataSrcInfo.sources[0][2], mappingSlot)

                if specialValue is not None:
                    self.preimage[hashValue] = (self.preimage[hashValue][0], self.preimage[hashValue][1], specialValue)
                
                # convert mapping storage position to storage slot
                mapPosition = int(mapPositionHex, 16) * 32 # 32 bytes per slot

                storageMapping = self.analyzer.contract2storageMapping(currentContract)

                if storageMapping is None:
                    self.stackTracker.push( stackEntry(32, dataSource( ("SHA3", pc) )) )
                    return 
                elif mapPosition not in storageMapping and "0x" + mapPositionHex not in self.preimage:
                    storageMapping = self.analyzer.contract2storageMapping(currentContract)

                    print("warning: mapPosition {} not in storageMappingMap".format(mapPositionHex)  + " and not in preimage" )
                    # sys.exit("Error! mapPosition {} not in storageMappingMap".format(mapPositionHex) + " and not in preimage")

                self.stackTracker.push( stackEntry(32, dataSource( ("SHA3", pc) )) )
                return
            
            elif len(key) == 64:
                self.stackTracker.push( stackEntry(32, dataSource( ("SHA3-64", key, pc)  )) )
            else:
                self.stackTracker.push( stackEntry(32, dataSource( ("SHA3-{}".format(len(key)), key, pc ) )) )
                # sys.exit("Tracker Error: SHA3 with length != 128 or 64")



            # elif len(key) == 64:
            #     sys.exit("Cannot handle dynamic array")
            #     # dynamic array
            #     # slot = arraySlot + keccak256(key)
            #     self.printIndentContent("SHA3[mem[{0}: {0} + {1}]] for dynamic array".format(offset, length))
            #     self.printIndentContent("SHA3({0}) = {1}".format(key, hashValue))
            #     currentContract = self.currentContract
            #     if self.analyzer.isVyper(currentContract):
            #         self.preimage[hashValue] = ("Vyper", key)
            #     else:
            #         self.preimage[hashValue] = ("Solc", key)

            # sys.exit("tracker: shouldn't reach here")
            # offsetInt = int(offset, base = 16)
            # lengthInt = int(length, base = 16)
            # self.stackTracker.pop(2)
            # dataSrcInfo = self.memoryTracker.getInterval(offsetInt, offsetInt + lengthInt)

            # newInfo = ("SHA3", )
            # dataSrcInfo = dataSource()
            # self.stackTracker.push( dataSrcInfo )
            

        elif opcode == "TIMESTAMP" or opcode == "NUMBER" or opcode == "DIFFICULTY" or opcode == "GASLIMIT" \
            or opcode == "BASEFEE" or opcode == "CHAINID" or opcode == "SELFBALANCE" or opcode == "CALLVALUE" \
            or opcode == "CALLDATASIZE" or opcode == "CODESIZE" or opcode == "GASPRICE" or opcode == "RETURNDATASIZE" \
            or opcode == "MSIZE" or opcode == "GAS" or opcode == "PC" or opcode == "BALANCE":
            value = nextStructLog["stack"][-1]
            dataS = dataSource( (opcode, value, pc) )
            self.stackTracker.push( stackEntry(32, dataS ) )

        elif opcode == "CALLER" or opcode == "ORIGIN" or opcode == "ADDRESS" or opcode == "COINBASE":
            value = nextStructLog["stack"][-1]
            address = "0x" + value[2:].zfill(40)
            if opcode == "CALLER":
                # print("set caller to be ", address)
                self.caller = address
            elif opcode == "ORIGIN":
                # print("set origin to be ", address)
                self.origin = address
            elif opcode == "ADDRESS":
                # print("set address to be ", address)
                self.address = address
            entry = stackEntry(32)
            dataS = dataSource( (opcode, address,  pc) )
            entry.addInterval(12, 32, dataS )
            self.stackTracker.push( entry )


        elif opcode == "CALLDATALOAD":
            index = structLog["stack"][-1]
            indexInt = int(index, base = 16)
            value = nextStructLog["stack"][-1]
            valueInt = int(value, base = 16)
            self.stackTracker.pop(1)
            info = ("msg.data", indexInt, indexInt + 32, valueInt,  pc)
            dataS = dataSource( info )
            self.stackTracker.push( stackEntry(32, dataS) )

        elif opcode == "CALLDATACOPY":
            # new data source!
            # memory[destOffset:destOffset+length] = msg.data[offset:offset+length]
            destOffset = structLog["stack"][-1]
            offset = structLog["stack"][-2]
            length = structLog["stack"][-3]
            
            destOffsetInt = int(destOffset, base = 16)
            offsetInt = int(offset, base = 16)
            lengthInt = int(length, base = 16)
            
            if length != "0x0":
                value = self.decoder.extractMemory(nextStructLog["memory"], destOffset, length)
                # print(value)
                valueInt = int(value, base = 16)

                info = ("msg.data", offsetInt, offsetInt + lengthInt, valueInt, pc)
                dataS = dataSource( info )
                self.memoryTracker.overwriteInterval(destOffsetInt, destOffsetInt + lengthInt, dataS )

            self.stackTracker.pop(3)


        elif opcode == "CODECOPY":
            # new data source!
            # memory[destOffset:destOffset+length] = address(this).code[offset:offset+length]
            destOffset = structLog["stack"][-1]
            offset = structLog["stack"][-2]
            length = structLog["stack"][-3]
            
            destOffsetInt = int(destOffset, base = 16)
            offsetInt = int(offset, base = 16)
            lengthInt = int(length, base = 16)

            info = ("address(this).code", offsetInt, offsetInt + lengthInt, pc)
            dataS = dataSource( info )

            self.memoryTracker.overwriteInterval(destOffsetInt, destOffsetInt + lengthInt, dataS )

            self.stackTracker.pop(3)

        elif opcode == "EXTCODESIZE":
            # self.stackTracker.pop(1)
            # addr = nextStructLog["stack"][-1]
            # self.stackTracker.push({("address({}).code.size").format(addr)})
            # Do nothing because the data source keeps
            pass

        elif opcode == "RETURNDATACOPY":
            # new data source!
            # memory[destOffset:destOffset+length] = RETURNDATA[offset:offset+length]
            destOffset = structLog["stack"][-1]
            offset = structLog["stack"][-2]
            length = structLog["stack"][-3]

            destOffsetInt = int(destOffset, base = 16)
            offsetInt = int(offset, base = 16)
            lengthInt = int(length, base = 16)

            retLengthInt = 0
            dataS = None
            if depth in self.returndata:
                retLengthInt = self.returndata[depth][0]
                dataS = self.returndata[depth][1]
                if offsetInt + lengthInt > retLengthInt:
                    pass
                    # print("offsetInt = ", offsetInt)
                    # print("lengthInt = ", lengthInt)
                    # print("retLengthInt = ", retLengthInt)
                    #  sys.exit("Tracker Error: RETURNDATACOPY with offset + length > retLength")
            else:
                info = ("RETURNDATACOPY", "could be wrong", pc)
                dataS = dataSource( info )


            self.memoryTracker.overwriteInterval(destOffsetInt, destOffsetInt + lengthInt, dataS)

            self.stackTracker.pop(3)
            # sys.exit("stackTracer: RETURNDATACOPY is not supported yet")
            
        elif opcode == "EXTCODEHASH":
            # ----------------            -------------
            # |  ADDR   |            =>   |   HASH   |
            # ----------------            -------------
            
            # addr = nextStructLog["stack"][-1]
            # self.stackTracker.push({"keccak256(address({}).code".format(addr)})
            # Do nothing because the data source keeps
            pass

        elif opcode == "BLOCKHASH":
            # ----------------                   -------------
            # |  blockNumber   |        =>   |   HASH   |
            # ----------------                   -------------
            # self.stackTracker.pop(1)
            # blockNumber = nextStructLog["stack"][-1]
            # self.stackTracker.push({("blockhash({})").format(blockNumber)})
            # Do nothing because the data source keeps
            pass

        elif opcode == "POP":
            self.stackTracker.pop(1)

        elif opcode == "MLOAD":
            # new data source!
            self.stackTracker.pop(1)

            offset = structLog["stack"][-1]
            offsetInt = int(offset, base = 16)

            dataSrcVec = self.memoryTracker.getIntervalDetails(offsetInt, offsetInt + 32)
            self.stackTracker.push(stackEntry(32, dataSrcVec))

        elif opcode == "MSTORE":
            # Add to memory location!!!
            # new data source!
            offset = structLog["stack"][-1]
            offsetInt = int(offset, base = 16)
            value = structLog["stack"][-2]

            entry = self.stackTracker.stack[-2]
            self.memoryTracker.overwriteStackEntry(offsetInt, offsetInt + 32, entry)

            self.stackTracker.pop(2)

        elif opcode == "MSTORE8": # add one byte
            # Add to memory location!!!
            offset = structLog["stack"][-1]
            offsetInt = int(offset, base = 16)
            value = structLog["stack"][-2]
            
            entry = self.stackTracker.stack[-2]
            self.memoryTracker.overwriteStackEntry(offsetInt, offsetInt + 1, entry)

            self.stackTracker.pop(2)

        elif opcode == "SLOAD":
            # new data source!
            key = structLog["stack"][-1]
            # remove 0x from key and add padding 0s
            key = key[2:]
            key = "0" * (64 - len(key)) + key
            key = "0x" + key

            keyInt = int(key, base = 16)
            keyStackEntry = self.stackTracker.pop(1)
            value = nextStructLog["stack"][-1]
            entry = stackEntry(32)
            if entry is not None and keyStackEntry is not None:
                entry.merge(keyStackEntry)
            dataSrcVec = self.storageTracker.readDetails(keyInt)


            isSHA3 = False
            if keyStackEntry is not None:
                for dataSrc in keyStackEntry.dataSrcMap:
                    if dataSrc[2].find("SHA3"):
                        isSHA3 = True
                        break
                
            isFind = False
            shift = None
            for shift in [0, 1, -1, 2, -2, 3, -3, 4, -4, 5, -5, 6, -6, 7, -7, 8, -8, 9, -9, 10, -10]:
                addShiftInt = int(key, 16) + shift
                addShift = "0x" + f"{addShiftInt:0{len(key)-2}x}"
                if addShift in self.preimage:
                    isFind = True
                    break
            if isFind:
                addShiftInt = int(key, 16) + shift
                addShift = "0x" + f"{addShiftInt:0{len(key)-2}x}"

                info = (self.currentContract, "Mapping", self.preimage[addShift][1], self.preimage[addShift][2], -1 * shift, value, pc)
                dataS = dataSource(info)
                entry.overwriteInterval(0, 32, dataS )
            elif isSHA3:
                sys.exit("Tracker Error: Key is computed by SHA3 but not found in preimage")
            else:
                info = (self.currentContract, "SLOAD", key, value, pc)
                # entryStr = str(entry)
                # if len(key) >= 10:
                #     info = (self.currentContract, "SLOAD", str(entry), value, pc)
                #     pass
                dataS = dataSource(info)
                entry.overwriteInterval(0, 32, dataS )

            self.stackTracker.push( entry )

        elif opcode == "SSTORE":
            # Add to storage location!!!
            keySrcInfo = self.stackTracker.pop(1)
            valueSrcInfo = self.stackTracker.pop(1)

            key = structLog["stack"][-1]
            # remove 0x from key and add padding 0s
            key = key[2:]
            key = "0" * (64 - len(key)) + key
            key = "0x" + key
            
            keyInt = int(key, base = 16)
            value = structLog["stack"][-2]
            
            if keySrcInfo is not None:
                self.storageTracker.store(keyInt, valueSrcInfo)
            if valueSrcInfo is not None:
                self.storageTracker.store(keyInt, valueSrcInfo)

            self.stateChanges.append( (key, value, keySrcInfo, valueSrcInfo) )
            pass

        elif opcode == "JUMP":
            self.stackTracker.pop(1)

        elif opcode == "JUMPI":
            self.stackTracker.pop(2)

        elif opcode == "JUMPDEST":
            pass

        elif opcode.startswith("PUSH"):
            numBytes = int(opcode[4:])
            self.stackTracker.push( stackEntry(32) )
            pass

        elif opcode == "DUP1" or opcode == "DUP2" or opcode == "DUP3" or opcode == "DUP4" \
            or opcode == "DUP5" or opcode == "DUP6" or opcode == "DUP7" or opcode == "DUP8" \
            or opcode == "DUP9" or opcode == "DUP10" or opcode == "DUP11" or opcode == "DUP12" \
            or opcode == "DUP13" or opcode == "DUP14" or opcode == "DUP15" or opcode == "DUP16":
            # read how many dup
            # read the value
            dup_n = int(opcode[3:])
            self.stackTracker.dup(dup_n)


        elif opcode == "SWAP1" or opcode == "SWAP2" or opcode == "SWAP3" or opcode == "SWAP4" \
            or opcode == "SWAP5" or opcode == "SWAP6" or opcode == "SWAP7" or opcode == "SWAP8" \
            or opcode == "SWAP9" or opcode == "SWAP10" or opcode == "SWAP11" or opcode == "SWAP12" \
            or opcode == "SWAP13" or opcode == "SWAP14" or opcode == "SWAP15" or opcode == "SWAP16":
            # read how many swap
            # read the value
            swap_n = int(opcode[4:])
            self.stackTracker.swap(swap_n)

        elif opcode == "LOG0" or opcode == "LOG1" or opcode == "LOG2" or opcode == "LOG3" or opcode == "LOG4":
            # read how many log
            # read the value
            log_n = int(opcode[3:])
            self.stackTracker.pop(log_n + 2)

        # Below should not be checked ...

        elif opcode == "CREATE":
            sys.exit("StackTracker: {} should not be touched".format(opcode))
            # valueSrcInfo = self.stackTracker.pop(1)
            # offsetSrcInfo = self.stackTracker.pop(1)
            # lengthSrcInfo = self.stackTracker.pop(1)

            # newAddrSrc = dataSource()
            # newAddrSrc.merge(valueSrcInfo)
            # newAddrSrc.merge(offsetSrcInfo)
            # newAddrSrc.merge(lengthSrcInfo)

            # self.stackTracker.push(newAddrSrc)

        elif opcode == "CREATE2":
            sys.exit("StackTracker: {} should not be touched".format(opcode))
            # valueSrcInfo = self.stackTracker.pop(1)
            # offsetSrcInfo = self.stackTracker.pop(1)
            # lengthSrcInfo = self.stackTracker.pop(1)
            # saltSrcInfo = self.stackTracker.pop(1)

            # newAddrSrc = dataSource()
            # newAddrSrc.merge(valueSrcInfo)
            # newAddrSrc.merge(offsetSrcInfo)
            # newAddrSrc.merge(lengthSrcInfo)
            # newAddrSrc.merge(saltSrcInfo)

            # self.stackTracker.push(newAddrSrc)
            

        elif opcode == "STATICCALL":
            hex_str = structLog["stack"][-1]
            gas = int(hex_str, 16)
            addr = structLog["stack"][-2]
            argsOffset = structLog["stack"][-3]
            argsLength = structLog["stack"][-4]
            retOffset = structLog["stack"][-5]
            retLength = structLog["stack"][-6]
            if len(addr) > 42:
                addr = '0x' + addr[-40:]
            if addr == "0x1": # ecrecover
                self.stackTracker.merge_last_n(6, int(retLength, 16))
            elif addr == "0x2":
                pass
            elif addr == "0x3":
                pass
            elif addr == "0x4":
                pass
            else:
                sys.exit("StackTracker: {} should not be touched".format(opcode))


        elif  opcode == "CALL" or opcode == "CALLCODE":
            hex_str = structLog["stack"][-1]
            gas = int(hex_str, 16)
            addr = structLog["stack"][-2]
            value = structLog["stack"][-3]
            argsOffset = structLog["stack"][-4]
            argsLength = structLog["stack"][-5]
            retOffset = structLog["stack"][-6]
            retLength = structLog["stack"][-7]
            if len(addr) > 42:
                addr = '0x' + addr[-40:]
            if addr == "0x1": # ecrecover
                self.stackTracker.merge_last_n(6, int(retLength, 16))
            elif addr == "0x2":
                pass
            elif addr == "0x3":
                pass
            elif addr == "0x4":
                pass
            else:
                sys.exit("StackTracker: {} should not be touched".format(opcode))


        elif  opcode == "RETURN" or opcode == "DELEGATECALL":
            # new data source!
            sys.exit("StackTracker: {} should not be touched".format(opcode))

        elif opcode == "REVERT" or opcode == "STOP":
            return "Error"
            # sys.exit("StackTracker: {} not supported. The transaction is reverted".format(opcode))

        elif opcode == "SELFDESTRUCT":
            sys.exit("StackTracker: {} not supported. The contract is self-destructed".format(opcode))


        else:
            raise Exception("Unknown opcode: " + opcode)




    




if __name__ == "__main__":
    # test mergeLastEntriesInStack
    A = [{'a', 'b'}, {'c', 'd'}, {'e', 'f'}, {'g', 'h'}, {'i', 'j'}, {'pp': 1, "aa": 2}]
    B = stackTracker(A)
    B.merge_last_n(2)
    print(B)

    # # test dup
    # A = [{'a', 'b'}, {'c', 'd'}, {'e', 'f'}, {'g', 'h'}, {'i', 'j'}]
    # B = stackTracker(A)
    # B.dup(2)
    # print(B)

    # # test swap
    # A = [{'a', 'b'}, {'c', 'd'}, {'e', 'f'}, {'g', 'h'}, {'i', 'j'}]
    # B = stackTracker(A)
    # B.swap(2)
    # print(B)

    # # test memoryTracker
    # mT = memoryTracker()
    # mT.addInterval(0, 5, {"0,5"})
    # mT.addInterval(5, 10, {"5,10"})
    # mT.addInterval(0, 15, {"0,15"})
    # mT.addInterval(7, 25, {"7,25"})
    # print(mT)
    

    # # YearnContractAddress = "0xACd43E627e64355f1861cEC6d3a6688B31a6F952"
    # # YearnHackTx = "0xf6022012b73770e7e2177129e648980a82aab555f9ac88b8a9cda3ec44b30779"

    # # path = "./YearnHackTxFull.pickle.gz"
    # # trace = readCompressedJson(path)

    # import json
    # print(SCRIPT_DIR + "/EMNHackFullTrace.json")
    # path = SCRIPT_DIR + "/EMNHackFullTrace.json"
    # with open(path, "r") as f:
    #     trace = json.load(f)

    # tempTracker = tracker("0xe38684752ebe4c333c921800a8109bc97cd6fa3d")

    # structLogs = trace["structLogs"]

    # for ii in range(len(structLogs)):
    #     if structLogs[ii]["depth"] == 1:
    #         print(structLogs[ii]["gas"])
    #         tempTracker.stackTrack(structLogs[ii], structLogs[ii + 1])




