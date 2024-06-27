# a general parser for vmtrace
import struct
import sys
import os
import time
import json
import gc

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from parserPackage.decoder import decoder
from fetchPackage.fetchTrace import fetcher
from utilsPackage.compressor import writeCompressedJson, readCompressedJson



class TxSpectorTranslator:
    def __init__(self):
        self.decoder = decoder()


    def parseLogs(self, trace):
        structLogs = trace['structLogs']
        self.callReserved = {}
        # sometimes we need to rely on last return to determine this call's return value
        lastReturn = (0, 0)

        translated = ""
        ii = -1
        ii_handled = -1
        while ii < len(structLogs) - 1:
            ii += 1
            pc = structLogs[ii]["pc"]
            opcode = structLogs[ii]["op"]
            if opcode == "KECCAK256":
                opcode = "SHA3"

            if ii != 0 and ii != ii_handled:
                lastDepth = structLogs[ii-1]["depth"]
                depth = structLogs[ii]["depth"]
                if lastDepth > depth:
                    if depth in self.callReserved:
                        callResultHex = structLogs[ii]["stack"][-1]
                        callResult = int(callResultHex, 16)
                        toAdd, opcode, retOffset, retLength = self.callReserved[depth]

                        if opcode == "CALL" or opcode == "STATICCALL" or opcode == "CALLCODE" or opcode == "DELEGATECALL":
                            retValueHex = self.decoder.extractMemory(structLogs[ii]["memory"], retOffset, retLength)
                            retValue = 0
                            if retValueHex != "":
                                retValue = int(retValueHex, 16)
                            if retValue == 0 and lastReturn[0] == lastDepth and structLogs[ii-1]["op"] == "RETURN":
                                retValue = lastReturn[1]

                            toAdd = "{}{},{}\n".format(toAdd, callResult, retValue)
                            translated += toAdd
                            ii_handled = ii
                            # print("Use Reserved at pc = {}, ii = {}, lastDepth = {}, depth = {}, callResult = {}, retValue = {}".format(pc, ii, lastDepth, depth, callResult, retValue))
                            del self.callReserved[depth]
                            ii -= 1
                            continue
                        
                        elif opcode == "CREATE" or opcode == "CREATE2":
                            retValue = structLogs[ii]["stack"][-1]
                            toAdd = "{}{}\n".format(toAdd, retValue)
                            translated += toAdd
                            ii_handled = ii
                            # print("Use Reserved at pc = {}, ii = {}, lastDepth = {}, depth = {}, retValue = {}".format(pc, ii, lastDepth, depth, retValue))
                            del self.callReserved[depth]
                            ii -= 1
                            continue


                    else:
                        sys.exit("Error: depth mismatch, pc = {}, ii = {}, lastDepth = {}, depth = {}".format(pc, ii, lastDepth, depth))
            

            toAdd = "{};{};".format(pc, opcode)
            if  opcode == "ADD" or opcode == "MUL" or opcode == "SUB" or \
                opcode == "DIV" or opcode == "SDIV" or opcode == "MOD" or opcode == "SMOD" or \
                opcode == "ADDMOD" or opcode == "MULMOD" or opcode == "EXP" or opcode == "SIGNEXTEND" or \
                opcode == "LT" or opcode == "GT" or opcode == "SLT" or opcode == "SGT" or \
                opcode == "EQ" or opcode == "ISZERO" or opcode == "AND" or opcode == "OR" or \
                opcode == "XOR" or opcode == "NOT":
                pass# confirmed
            elif opcode == "BYTE":
                pass
            elif opcode == "SHL":
                pass
            elif opcode == "SHR":
                pass
            elif opcode == "SAR":
                pass
            elif opcode == "SHA3" or \
                    opcode == "ADDRESS" or opcode == "BALANCE" or opcode == "ORIGIN" or \
                    opcode == "CALLER" or opcode == "CALLVALUE" or opcode == "CALLDATALOAD" or \
                    opcode == "CALLDATASIZE" or opcode == "CODESIZE" or opcode == "GASPRICE" or opcode == "TXGASPRICE" or \
                    opcode == "EXTCODESIZE" or opcode == "RETURNDATASIZE" or opcode == "EXTCODEHASH" or \
                    opcode == "BLOCKHASH" or opcode == "COINBASE" or opcode == "TIMESTAMP" or \
                    opcode == "NUMBER" or opcode == "DIFFICULTY" or opcode == "GASLIMIT" or \
                    opcode == "CHAINID" or opcode == "SELFBALANCE" or opcode == "BASEFEE" or \
                    opcode == "MLOAD" or opcode == "SLOAD" or opcode == "PC" or \
                    opcode == "MSIZE" or opcode == "GAS":
                valueHex = structLogs[ii+1]["stack"][-1]
                value = int(valueHex, 16)
                toAdd += "{}".format(value)


            elif opcode == "CALLDATACOPY" or opcode == "CODECOPY" or opcode == "RETURNDATACOPY":
                structLog = structLogs[ii]
                nextStructLog = structLogs[ii+1]
                destOffset = structLog["stack"][-1]
                offset = structLog["stack"][-2]
                length = structLog["stack"][-3]
                destOffsetInt = int(destOffset, base = 16)
                offsetInt = int(offset, base = 16)
                lengthInt = int(length, base = 16)
                valueHex = self.decoder.extractMemory(nextStructLog["memory"], destOffset, length)
                value = 0
                if valueHex != "":
                    value = int(valueHex, 16)

                toAdd += "{}".format(value)

            elif opcode == "EXTCODECOPY":
                structLog = structLogs[ii]
                nextStructLog = structLogs[ii+1]
                address = structLog["stack"][-1]
                destOffset = structLog["stack"][-2]
                offset = structLog["stack"][-3]
                length = structLog["stack"][-4]
                destOffsetInt = int(destOffset, base = 16)
                offsetInt = int(offset, base = 16)
                lengthInt = int(length, base = 16)
                valueHex = self.decoder.extractMemory(nextStructLog["memory"], destOffset, length)
                value = 0
                if valueHex != "":
                    value = int(valueHex, 16)
                toAdd += "{}".format(value)
            
            elif opcode == "POP":
                pass# confirmed
            elif opcode == "MSTORE":
                pass # confirmed
            elif opcode == "MSTORE8":
                pass# confirmed
            elif opcode == "SSTORE":
                pass# confirmed
            elif opcode == "JUMP":
                pass# confirmed
            elif opcode == "JUMPI":
                pass# confirmed
            elif opcode == "JUMPDEST":
                pass# confirmed
            elif opcode.startswith("PUSH"): # PUSH0-PUSH32
                valueHex = structLogs[ii+1]["stack"][-1]
                value = int(valueHex, 16)
                toAdd += "{}".format(value)
            elif opcode.startswith("DUP"): # DUP1-DUP16
                pass # confirmed
            elif opcode.startswith("SWAP"):
                pass # confirmed
            elif opcode.startswith("LOG"):
                pass # confirmed

            elif opcode == "CREATE":
                structLog = structLogs[ii]
                nextStructLog = structLogs[ii+1]

                # valueHex = nextStructLog["stack"][-1]
                # offsetHex = nextStructLog["stack"][-2]
                # lengthHex = nextStructLog["stack"][-3]

                depth = structLog["depth"]
                nextDepth = nextStructLog["depth"]

                # print("Reserve create at depth {}: toAdd-{}".format(depth, toAdd))

                self.callReserved[depth] = (toAdd, opcode, None, None)
                continue

            elif opcode == "CREATE2":
                structLog = structLogs[ii]
                nextStructLog = structLogs[ii+1]

                # valueHex = nextStructLog["stack"][-1]
                # offsetHex = nextStructLog["stack"][-2]
                # lengthHex = nextStructLog["stack"][-3]

                depth = structLog["depth"]
                nextDepth = nextStructLog["depth"]

                # print("Reserve create2 at depth {}: toAdd-{}".format(depth, toAdd))

                self.callReserved[depth] = (toAdd, opcode, None, None)
                continue


            # Four call opcodes has a special type: 0,1, they need extra type
            # value_extra is used to store more arguments for call, callcode, delegatecall, staticcall
            # op.value is success flag, value_extra is the memory content.


            elif opcode == "CALL":
                structLog = structLogs[ii]
                nextStructLog = structLogs[ii+1]

                gas = structLog["stack"][-1]
                addr = structLog["stack"][-2]
                value = structLog["stack"][-3]
                argsOffset = structLog["stack"][-4]
                argsLength = structLog["stack"][-5]
                retOffset = structLog["stack"][-6]
                retLength = structLog["stack"][-7]

                depth = structLog["depth"]
                nextDepth = nextStructLog["depth"]
                # precompile
                if depth == nextDepth:
                    successValueHex = nextStructLog["stack"][-1]
                    successValue = int(successValueHex, 16)
                    retValueHex = self.decoder.extractMemory(nextStructLog["memory"], retOffset, retLength)
                    retValue = 0
                    if retValueHex != "":
                        retValue = int(retValueHex, 16)
                    toAdd += "{},{}".format(successValue, retValue)
                else:
                    # print("Reserve call at depth {}: toAdd-{}, retOffset-{}, retLength-{}".format(depth, toAdd, retOffset, retLength))
                    if depth in self.callReserved:
                        print("Error: depth {} is already reserved".format(depth))
                    self.callReserved[depth] = (toAdd, opcode, retOffset, retLength)
                    continue
                    
            
            elif opcode == "CALLCODE":

                structLog = structLogs[ii]
                nextStructLog = structLogs[ii+1]

                gas = structLog["stack"][-1]
                addr = structLog["stack"][-2]
                value = structLog["stack"][-3]
                argsOffset = structLog["stack"][-4]
                argsLength = structLog["stack"][-5]
                retOffset = structLog["stack"][-6]
                retLength = structLog["stack"][-7]

                depth = structLog["depth"]
                nextDepth = nextStructLog["depth"]
                # precompile
                if depth == nextDepth:
                    successValueHex = nextStructLog["stack"][-1]
                    successValue = int(successValueHex, 16)
                    retValueHex = self.decoder.extractMemory(nextStructLog["memory"], retOffset, retLength)
                    retValue = 0
                    if retValueHex != "":
                        retValue = int(retValueHex, 16)
                    toAdd += "{},{}".format(successValue, retValue)
                else:
                    # print("Reserve call at depth {}: toAdd-{}, retOffset-{}, retLength-{}".format(depth, toAdd, retOffset, retLength))
                    if depth in self.callReserved:
                        print("Error: depth {} is already reserved".format(depth))
                    self.callReserved[depth] = (toAdd, opcode, retOffset, retLength)
                    continue


            elif opcode == "STATICCALL" or opcode == "DELEGATECALL":
                structLog = structLogs[ii]
                nextStructLog = structLogs[ii+1]

                gas = structLog["stack"][-1]
                addr = structLog["stack"][-2]
                argsOffset = structLog["stack"][-3]
                argsLength = structLog["stack"][-4]
                retOffset = structLog["stack"][-5]
                retLength = structLog["stack"][-6]

                depth = structLog["depth"]
                nextDepth = nextStructLog["depth"]

                # precompile
                if depth == nextDepth:
                    successValueHex = nextStructLog["stack"][-1]
                    successValue = int(successValueHex, 16)
                    retValueHex = self.decoder.extractMemory(nextStructLog["memory"], retOffset, retLength)
                    retValue = 0
                    if retValueHex != "":
                        retValue = int(retValueHex, 16)
                    toAdd += "{},{}".format(successValue, retValue)
                else:
                    # print("Reserve call at depth {}: toAdd-{}, retOffset-{}, retLength-{}".format(depth, toAdd, retOffset, retLength))
                    if depth in self.callReserved:
                        print("Error: depth {} is already reserved".format(depth))
                    self.callReserved[depth] = (toAdd, opcode, retOffset, retLength)
                    continue

                

            elif opcode == "STOP":
                pass # confirmed
            elif opcode == "RETURN" or opcode == "REVERT":
                offset = structLogs[ii]["stack"][-1]
                length = structLogs[ii]["stack"][-2]
                offsetInt = int(offset, 16)
                lengthInt = int(length, 16)

                valueHex = self.decoder.extractMemory(structLogs[ii]["memory"], offset, length)
                value = 0
                if valueHex != "":
                    value = int(valueHex, 16)

                toAdd += "{}".format(value)

                depth = structLogs[ii]["depth"]
                lastReturn = (depth, value)


            elif opcode == "SELFDESTRUCT":
                pass 
            else:
                sys.exit("Error: unknown opcode {}".format(opcode))
            
            translated += toAdd + "\n"
        return translated






def solve1benchmark(exploitTx, use_cache = True):

    fe = fetcher()
    result_dict = None
    # path = SCRIPT_DIR + '/../TxSpectorHelper/cache2/{}.json'.format(exploitTx)
    # if not (use_cache and os.path.exists(path)):
    #     result_dict = fe.getTrace(exploitTx, FullTrace=False)
    #     with open(path, 'w') as f:
    #         json.dump(result_dict, f, indent = 2)
        

    path = SCRIPT_DIR + '/../TxSpectorHelper/cache/{}.json.gz'.format(exploitTx)
    if not (use_cache and os.path.exists(path)):
        result_dict = fe.getTrace(exploitTx, FullTrace=False,  FullStack=True)
        # with open(path, 'w') as f:
        #     json.dump(result_dict, f, indent = 2)
        writeCompressedJson(path, result_dict)

    path2 = SCRIPT_DIR + '/../TxSpectorHelper/example.json'
    
    for ii, op in enumerate(result_dict["structLogs"]):
        result_dict["structLogs"][ii]["len"] = len(op["stack"])

    # store the trace in example.json
    with open(path2, 'w') as f:
        json.dump(result_dict, f, indent = 2)
    

    kk = readCompressedJson(path)
    translated = TxSpectorTranslator().parseLogs(kk)
    path = SCRIPT_DIR + '/../TxSpectorHelper/translated/{}.txt'.format(exploitTx)
    with open("{}.txt".format(exploitTx), "w") as f:
        f.write(translated)

    gc.collect()



if __name__ == "__main__":

    solve1benchmark("0xadbc02bda46eb54e411ca73655c9b6993805c75535be3084ea316cd334b35c9c", False)