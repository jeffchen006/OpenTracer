import struct
import sys
import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

import time
import json
from crawlPackage.crawlEtherscan import CrawlEtherscan
from crawlPackage.crawlQuicknode import CrawlQuickNode
from staticAnalyzer.analyzer import Analyzer
from web3 import Web3
import copy

from eth_abi import decode, encode
import eth_abi

from slither.core.solidity_types.elementary_type import *


class decoder:
    def __init__(self) -> None:
        pass

    def formatCalldataArray(self, calldataArr: list) -> str:
        """Given a list of calldata, return a string of formatted calldata"""
        calldata = ""
        for calldataItem in calldataArr:
            calldata += self.formatCalldata(calldataItem)
        return calldata

    def formatCalldata(self, calldata: str) -> str:
        """Given a string of hex data, return a string of formatted calldata"""
        calldata = self.addPadding(calldata)
        return calldata.upper()

    def addPaddingUINT256(self, data: str) -> str:
        """Given a string of hex data, add padding to the front"""
        if data.startswith("0x"):
            data = data[2:]
        if len(data) % 64 != 0:
            data = '0' * (64 - len(data) % 64) + data
        return data

    def addPadding(self, data: str) -> str:
        """Given a string of hex data, add padding to the front"""
        if data.startswith("0x"):
            data = data[2:]
        if len(data) % 64 != 0:
            data = '0' * (64 - len(data) % 64) + data
        return data


    def getCalldataHex(self, oldCalldataHex: str, calldataSizeInt: int, startIndexHex: str, calldataRead: str) -> str:
        startIndex = int(startIndexHex, base = 16)
        return self.getCalldata(oldCalldataHex, calldataSizeInt, startIndex, calldataRead)


    def getCalldata(self, oldCalldataHex: str, calldataSize: int, startIndex: int, calldataRead: str) -> str:
        inputcalldataSize = calldataSize
        if calldataSize == -1: 
            # special case: calldataSize is not known
            calldataSize = max(len(oldCalldataHex) // 2, startIndex + 32)

        if oldCalldataHex == "":
            oldCalldataHex = "0" * calldataSize * 2
        startIndexHex = startIndex * 2 # Compensate for '0x'
        calldataReadHex = self.formatCalldata(calldataRead)
        endIndexHex = startIndexHex + 64

        if endIndexHex > calldataSize * 2:
            s = oldCalldataHex[:startIndexHex] + calldataReadHex
        else:
            if endIndexHex > len(oldCalldataHex) and inputcalldataSize != -1:
                sys.exit("Decoder Error: endIndexHex > len(oldCalldataHex)")
                
            # if len(calldataReadHex) != 64:
            #     sys.exit("Decoder Error: len(calldataReadHex) != 64")

            s = oldCalldataHex[:startIndexHex] + calldataReadHex + oldCalldataHex[endIndexHex:]
        return s




    def decodeSimpleABI(self, types: list, data: str) -> list:
        """Given a list of types and data, return a list of decoded data"""
        decodedData = decode(types, bytes.fromhex(data))
        mylist = list(decodedData)
        for i in range(len(mylist)):
            if isinstance(mylist[i], bytes):
                mylist[i] = mylist[i].hex()
        return mylist


    def decodeReturn(self, types: list, memoryList: list, offset, length):
        """Given a list of types, memory (a list of str), an offset (eg. 0x100), a length (eg. 0x20), return decoded return value"""
        memorySnippet = self.extractMemory(memoryList, offset, length)
        decodedData = self.decodeSimpleABI(types, memorySnippet)
        return decodedData


    def extractMemory(self, memoryList: list, offset, length):
        """Given memory (a list of str), an offset (eg. 0x100), a length (eg. 0x20), return memory snippet which represents return value"""
        memoryWhole = ''.join(memoryList)
        offsetInt = int(offset, base = 16)
        lengthInt = int(length, base = 16)
        offsetBytesLen = offsetInt * 2
        lengthBytesLen = lengthInt * 2
        memorySnippet = memoryWhole[offsetBytesLen: offsetBytesLen + lengthBytesLen]
        # print("offsetBytesLen: ", offsetBytesLen)
        # print("offsetBytesLen + lengthBytesLen: ", offsetBytesLen + lengthBytesLen)
        # print("len(memoryWhole): ", len(memoryWhole))
        # print(memorySnippet)
        return memorySnippet
    

    # uint bit
    typeLengths = {
        "uint": 32,
        "uint256": 32,
        "address": 20 + 12, # for padding
    }

    def type2length(self, typeStr: str):
        if typeStr == "uint256[]":
            return None
        elementType = ElementaryType(typeStr)

        if typeStr in self.typeLengths:
            return self.typeLengths[typeStr]

        size = None
        try:
            size = elementType.size / 8
        except:
            size = None
        return size


    def get_memory_lengths(self, param_types, length):
        # Calculate the memory length for each parameter type
        # first decode and then encode, compared with the original length
        memory_lengths = []
        for param_type in param_types:
            if param_type in self.typeLengths:
                memory_lengths.append(self.typeLengths[param_type])
            else:
                sys.exit("decoder.py: Error: unknown type: " + param_type)

        # check if sum of memory lengths is equal to length
        if sum(memory_lengths) != length:
            sys.exit("decoder.py: Error: sum of memory lengths is not equal to length")
        
        return memory_lengths


    def get_padded_size(types):
        size = 0
        padded_size = 0
        for t in types:
            if t.startswith("uint") or t.startswith("int"):
                size += int(t[4:]) // 8
            elif t == "address":
                size += 20
            elif t.startswith("bytes"):
                size += int(t[5:])
            else:
                raise ValueError(f"Unknown type: {t}")
            
            if size % 32 != 0:
                padded_size += (size // 32 + 1) * 32
            else:
                padded_size += size
        
        return (size, padded_size)



if __name__ == "__main__":
    types = ['uint256']
    # calldata = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0009'
    # print(bytes.fromhex("B9A1"))
    # decodedData = decoder.decodeSimpleABI(types, calldata)

    decoder = decoder()
    # calldata = "0xc685fa11e01ec6f000000"
    # calldata = decoder.formatCalldata(calldata)
    # decodedData = decoder.decodeSimpleABI(types, calldata)
    # print(decodedData)

    # test extractMemory
    memory =  ['0000000000000000000000000000000000000000000000000000000000000000', '0000000000000000000000000000000000000000000000000000000000000000', '0000000000000000000000000000000000000000000000000000000000000080', '0000000000000000000000000000000000000000000000000000000000000000', '0000000000000000000000000000000000000000047887633ebc2f527e747ec1']
    # Function Returns memory[0x80:0x80+0x20]
    snippet = decoder.extractMemory(memory, "0x80", "0x20")

    types = ['uint256']
    decodedData = decoder.decodeSimpleABI(types, snippet)
    print(decodedData)

    types = ['address']
    data = "000000000000000000000000BFCF63294AD7105DEA65AA58F8AE5BE2D9D0952A"
    ret = decode(types, bytes.fromhex(data))    
    print(ret)