import os
import sys
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))


from crawlPackage.crawlEtherscan import CrawlEtherscan
# # from crawlPackage.crawlQuicknode import CrawlQuickNode
# # from crawlPackage.crawlTrueBlocks import CrawlTrueBlocks
import subprocess, json, time, random, pickle, math, copy, toml

import pprint

from web3 import Web3, HTTPProvider
from packaging.version import Version
from os import listdir
from os.path import isfile, join


from slither.core.solidity_types.elementary_type import ElementaryType
from slither.core.solidity_types.user_defined_type import UserDefinedType
from slither.core.solidity_types.mapping_type import MappingType
from slither.core.solidity_types.array_type import ArrayType
from slither.core.solidity_types.function_type import FunctionType


from eth_abi import decode
import sqlite3
from crawlPackage.cacheDatabase import _save_transaction_receipt, _load_transaction_receipt, _save_contract, _load_contract



# def writeStats(contractAddress, ContractName, CompilerVersion: str, EVMVersion: str, sourceCode: str):
#     contractAddress = contractAddress.lower()
#     path = SCRIPT_DIR + "/cache/" + contractAddress
#     # print(path)
#     if not os.path.exists(path):
#         os.makedirs(path)

#     with open(path + "/" + ContractName + ".vy", "w") as f:
#         content = "# " + CompilerVersion + "\n"
#         content += "# " + EVMVersion + "\n\n"
#         # replace @version with @version_ to avoid compiler complaining
#         content += sourceCode.replace("@version", "version")
#         f.write(content)


def readStats(contractAddress, cur):
    contractAddress = contractAddress.lower()
    # path = SCRIPT_DIR + "/cache/" + contractAddress + "/"
    # if not os.path.exists(path):
    #     return None, None
    
    contract_dict = _load_contract(contractAddress, cur)
    if contract_dict is None:
        return None, None
    else:
        return contract_dict["CompilerVersion"], contract_dict["EVMVersion"]



class vyperAnalyzer: 

    def __init__(self) -> None:
        self.etherScan = CrawlEtherscan()
        self.cur = None
    

    def contract2Sourcecode(self, contractAddress: str):
        """Given a contract address, return the source code"""
        # check if the source code is already in the cache
        CompilerVersion, EVMVersion = readStats(contractAddress, self.cur)
        if CompilerVersion is not None and EVMVersion is not None:
            return CompilerVersion, EVMVersion
        results =  self.etherScan.Contract2Sourcecode(contractAddress)
        if "vyper" not in results["CompilerVersion"]:
            return None, None
        if len(results) > 1:
            sys.exit("vyperAnalyzer: cannot handle multiple Vyper contracts in one contract address")
        
        result = results[0]
        sourceCode = result["SourceCode"]
        ABI = result["ABI"]
        ContractName = result["ContractName"]
        CompilerVersion = result["CompilerVersion"]
        EVMVersion = result["EVMVersion"]

        # writeStats(contractAddress, ContractName, CompilerVersion, EVMVersion, sourceCode)

        return CompilerVersion, EVMVersion
    
    
    def handleSourceAndVersion(self, contractAddress: str) -> list:
        CompilerVersion, EVMVersion = self.contract2Sourcecode(contractAddress)

        if EVMVersion != "Default":
            return 
            # sys.exit("vyperAnalyzer: cannot handle non-default EVM version for now")

        compilerVersion = Version(CompilerVersion)
        storageLayoutVersion = Version("0.2.16")

        useCompiler = CompilerVersion
        if compilerVersion < storageLayoutVersion:
            useCompiler = "0.2.16" # Vyper starts to support storage layout option from 0.2.16

        subprocess.run(["vyper-select", "use", useCompiler], stdout=subprocess.PIPE, check=True)



    def Contract2funcSigMap(self, contractAddress: str) -> list:
        """Given a contract address, return a list of funcSigMap"""
        self.handleSourceAndVersion(contractAddress)

        mypath = os.path.join(SCRIPT_DIR, "cache", contractAddress.lower())
        onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]
        onlyfiles = [f for f in onlyfiles if f.endswith(".vy")]
        if len(onlyfiles) != 1:
            sys.exit("vyperAnalyzer: Error: multiple files in the same folder {}!".format(mypath))

        test_item = os.path.join(mypath, onlyfiles[0])
        abi = None
        with subprocess.Popen(["vyper", test_item, "-f", "abi"], stdout=subprocess.PIPE) as process:
            counter = 0
            for line in process.stdout:
                counter += 1
                if counter > 2:
                    sys.exit("vyperAnalyzer: Error: vyper compile abi exceeds 2 lines!")
                if counter == 1:
                    abi = json.loads(line)

        functionSigMap = self.etherScan.Contract2funcSigMap(contractAddress, abi)
        return functionSigMap
        
        

    def Contract2storageLayout(self, contractAddress: str) -> list:
        """Given a contract address, return a list of storageLayout"""
        self.handleSourceAndVersion(contractAddress)

        mypath = os.path.join(SCRIPT_DIR, "cache", contractAddress.lower())
        onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]
        onlyfiles = [f for f in onlyfiles if f.endswith(".vy")]
        if len(onlyfiles) != 1:
            sys.exit("vyperAnalyzer: Error: multiple files in the same folder {}!".format(mypath))

        test_item = os.path.join(mypath, onlyfiles[0])
        storageLayout = None
        with subprocess.Popen(["vyper", test_item, "-f", "layout"], stdout=subprocess.PIPE) as process:
            counter = 0
            for line in process.stdout:
                counter += 1
                if counter > 2:
                    sys.exit("vyperAnalyzer: Error: vyper compile layout exceeds 2 lines!")
                if counter == 1:
                    storageLayout = json.loads(line)
        # print(storageLayout)
        return storageLayout


    
    def parseType(self, typeStr):
        # eg. HashMap[address, HashMap[address, uint256][address, uint256]][address, HashMap[address, uint256][address, uint256]]
        # Find the position of ] which matches the first [
        # Check if typeStr is a basic type
        # remove all whitespaces
        typeStr = typeStr.replace(" ", "")
        

        try:
            ElementaryType(typeStr)
            return typeStr
        except:
            pass

        # Mapping
        if typeStr[:7] == "HashMap":
            # print(typeStr)
            pos = 0
            commaPos = 0
            for i in range(len(typeStr)):
                if typeStr[i] == "[":
                    pos += 1
                elif typeStr[i] == "]":
                    pos -= 1
                    if pos == 0:
                        break
                elif typeStr[i] == ",":
                    if pos == 1:
                        commaPos = i
            keyType = typeStr[8:commaPos]
            valueType = typeStr[commaPos+1:i]
            _type_stored = (self.parseType(keyType), self.parseType(valueType))
            return _type_stored
        
        else:
            if typeStr[-1] == "]" and typeStr[-2] != "[":
                # Fixed Size Array
                leftBracketPos = -1
                rightBracketPos = -1
                for i in range(len(typeStr)):
                    if typeStr[i] == "[":
                        if leftBracketPos == -1:
                            leftBracketPos = i
                        else:
                            sys.exit("vyperAnalyzer: Error: cannot handle nested array!, typeStr: {}".format(typeStr))
                    elif typeStr[i] == "]":
                        if rightBracketPos == -1:
                            rightBracketPos = i
                        else:
                            sys.exit("vyperAnalyzer: Error: cannot handle nested array!, typeStr: {}".format(typeStr))

                elementType = typeStr[:leftBracketPos]
                arraySize = int(typeStr[leftBracketPos+1:rightBracketPos])
                _type_stored = self.parseType(elementType) + "[" + str(arraySize) + "]"
                return _type_stored
            elif typeStr[-1] == "]" and typeStr[-2] == "[":
                # Dynamic Array
                return self.parseType(typeStr[:-2]) + "[]"
            else:
                if typeStr == "String":
                # Not sure if it;s correct but keep it for now
                    return "string" 

                elif typeStr == "VotedSlope" or typeStr == "Point":
                    # Hope it is not used in later processing
                    return typeStr

                elif typeStr == "nonreentrantlock" or typeStr == "LockedBalance":
                    return typeStr
                
                else:
                    # Hope it is not used in later processing
                    return typeStr

                # else:
                #     sys.exit("vyperAnalyzer: Error: cannot handle type {}, typeStr: {}".format(typeStr, typeStr))
            
            

    def StorageLayout2StorageMapping(self, storageLayout: list, is024: bool = False) -> list:
        """Given a storageLayout, return a list of storageMapping"""
        """is024: if Vyper version is 0.2.4"""
        # eg. {'name': {'type': 'String[64]', 'location': 'storage', 'slot': 0}, 
        # 'symbol': {'type': 'String[32]', 'location': 'storage', 'slot': 4}, 
        # 'decimals': {'type': 'uint256', 'location': 'storage', 'slot': 7}, 
        # 'balanceOf': {'type': 'HashMap[address, uint256][address, uint256]', 'location': 'storage', 'slot': 8}, 
        # 'allowances': {'type': 'HashMap[address, HashMap[address, uint256][address, uint256]][address, HashMap[address, uint256][address, uint256]]', 
        #               'location': 'storage', 'slot': 9}, 
        # 'total_supply': {'type': 'uint256', 'location': 'storage', 'slot': 10}, 
        # 'minter': {'type': 'address', 'location': 'storage', 'slot': 11}}
        storageMapping = {}
        if is024:
            # sort storageLayout by its value["slot"]
            storageLayout = sorted(storageLayout.items(), key=lambda x: x[1]["slot"])
            counter = 0
            for item in storageLayout:
                varName = item[0]
                value = item[1]
                if value["location"] == "storage":
                    _type_stored = self.parseType(value["type"])
                    storageMapping[counter * 32] = (varName, _type_stored)
                    counter += 1
                else:
                    sys.exit("vyperAnalyzer: Error: location is not storage!")
            return storageMapping
        
        for varName, value in storageLayout.items():
            if value["location"] == "storage":
                _type_stored = self.parseType(value["type"])
                storageMapping[value["slot"] * 32] = (varName, _type_stored) # 32 is the size of a slot
            else:
                sys.exit("vyperAnalyzer: Error: cannot handle non-storage type [{}] yet!".format(value["location"]))
        return storageMapping
    

    def Contract2storageMapping(self, contractAddress: str) -> dict:
        """Given a contract address, return a dict of storageMapping"""
        CompilerVersion, _ = self.contract2Sourcecode(contractAddress)
        storageLayout = self.Contract2storageLayout(contractAddress)
        if storageLayout is None:
            return None
        is024 = (CompilerVersion == "0.2.4")
        storageMapping = self.StorageLayout2StorageMapping(storageLayout, is024=is024)
        return storageMapping






if __name__ == "__main__":

    analyzer = vyperAnalyzer()
    Curve3PoolContractAddress = "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7"

    
    CompilerVersion, EVMVersion = analyzer.contract2Sourcecode(Curve3PoolContractAddress)
    # print(sourceCode)

    # functionSigMap = analyzer.Contract2funcSigMap(Curve3PoolContractAddress)
    # print(functionSigMap)
    print(CompilerVersion)
    print(EVMVersion)

    # funcSigMap = analyzer.Contract2funcSigMap(Curve3PoolContractAddress)
    # print(funcSigMap)

    # # EMN contract
    # contractAddress = "0x5ade7aE8660293F2ebfcEfaba91d141d72d221e8"

    # # test Contract2storageLayout
    # storageLayout = analyzer.Contract2storageLayout("0xbfcf63294ad7105dea65aa58f8ae5be2d9d0952a")
    # print(storageLayout)
    # storageMapping = analyzer.Contract2storageMapping("0xbfcf63294ad7105dea65aa58f8ae5be2d9d0952a")
    # print(storageMapping)

    # # store storageMapping into a json file
    # # pretty print

    # with open("storageMapping.json", "w") as f:
    #     json.dump(storageMapping, f, indent=4)

    # # # test parseType
    # # type1 = "String[64]"
    # # type2 = "String[32]"
    # # type3 = "uint256"
    # # type4 = "HashMap[address, uint256][address, uint256]"
    # # type5 = "HashMap[address, HashMap[address, uint256][address, uint256]][address, HashMap[address, uint256][address, uint256]]"
    # # type6 = "address"
    # # types = [type1, type2, type3, type4, type5, type6]
    # # for typeStr in types:
    # #     print(analyzer.parseType(typeStr))

    # # test StorageLayout2StorageMapping

