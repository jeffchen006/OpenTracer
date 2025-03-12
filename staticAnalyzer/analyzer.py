import os
import sys
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from crawlPackage.crawlEtherscan import CrawlEtherscan
from crawlPackage.crawlQuicknode import CrawlQuickNode
# from crawlPackage.crawlTrueBlocks import CrawlTrueBlocks
from staticAnalyzer.slitherAnalyzer import slitherAnalyzer
from staticAnalyzer.vyperAnalyzer import vyperAnalyzer

import subprocess
import json 
import time
import random
import pickle
import copy
import sqlite3
from crawlPackage.cacheDatabase import _save_transaction_receipt, _load_transaction_receipt, _save_contract, _load_contract



# Solidity starts from 0.4.11 to 0.8.17
# Vyper starts from 0.1.0-beta.16 to 0.3.7
# Vyper starts to support storage layout option from 0.2.16


def save_object(obj, filename: str):
    # print("filename: ", filename)
    try:
        with open(SCRIPT_DIR + "/cache/" + "{}.pickle".format(filename), "wb") as f:
            pickle.dump(obj, f, protocol=pickle.HIGHEST_PROTOCOL)
    except Exception as ex:
        print("Error during pickling object (Possibly unsupported):", ex)
    finally:
        pass
 

def load_object(filename: str):
    # print("read filename: ", filename)
    try:
        with open(SCRIPT_DIR + "/cache/" + "{}.pickle".format(filename), "rb") as f:
            value = pickle.load(f)
            return value
    except Exception as ex:
        return None
    finally:
        pass



class Analyzer:

    
    def __init__(self) -> None:
        self.crawlEtherscan = CrawlEtherscan()
        self.slitherAnalyzer = slitherAnalyzer()
        self.vyperAnalyzer = vyperAnalyzer()
        self.isVyperCache = {}
        self.storageMappingMapping = {}
        self.funcSigMapMapping = {}
        self.unableCompileAddresses = []

        SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
        etherScanDatabase = SCRIPT_DIR + "/../crawlPackage/database/etherScan.db"
        if os.path.exists(etherScanDatabase):
            self.conn = sqlite3.connect(etherScanDatabase)
            self.cur = self.conn.cursor()

            self.slitherAnalyzer.cur = self.cur
            self.vyperAnalyzer.cur = self.cur
            

    
    # def contract2storageLayout(self, contractAddress: str) -> dict:
    #     """Given a contract address, return a map (<func selector> -> <func signature>)"""
    #     filename = "{}_storageLayout".format(contractAddress.lower())
    #     storage_layout = load_object(filename)
    #     if storage_layout is not None:
    #         return storage_layout
    #     if self.isVyper(contractAddress):
    #         storage_layout = self.vyperAnalyzer.Contract2storageLayout(contractAddress)
    #     else:
    #         storage_layout = self.slitherAnalyzer.Contract2storageLayout(contractAddress)
    #     if storage_layout == None:
    #         sys.exit("Error: cannot read storage layout of {}!".format(contractAddress))
            
    #     save_object(storage_layout, filename)
    #     return storage_layout

    def contract2storageMapping(self, contractAddress: str) -> dict:
        """Given a contract, return a map (<position in bytes> -> <variables and its properties>)"""
        if contractAddress in self.storageMappingMapping:
            return self.storageMappingMapping[contractAddress]

        if contractAddress in self.unableCompileAddresses:
            return None

        anotherFileName = "UnableCompileAddresses"
        UnableCompileAddresses = load_object(anotherFileName)
        if UnableCompileAddresses is None:
            self.unableCompileAddresses = []
        else:
            self.unableCompileAddresses = UnableCompileAddresses
            
        filename = "{}_storageMapping".format(contractAddress.lower())
        storage_mapping = load_object(filename)
        if storage_mapping is not None and storage_mapping != {}:
            self.storageMappingMapping[contractAddress] = storage_mapping
            return storage_mapping
        
        try:
            if not self.isVyper(contractAddress):
                storage_mapping = self.slitherAnalyzer.Contract2storageMapping(contractAddress)
                self.storageMappingMapping[contractAddress] = storage_mapping
            else:
                storage_mapping = self.vyperAnalyzer.Contract2storageMapping(contractAddress)
                self.storageMappingMapping[contractAddress] = storage_mapping
        except:
            storage_mapping = None

        if storage_mapping == None:
            # print("Error: cannot read storage mapping of {}!".format(contractAddress))
            # print("possible reason: the contract is written in Vyper < 0.2.16")
            self.unableCompileAddresses.append(contractAddress)
            save_object(self.unableCompileAddresses, anotherFileName)
            pass
        save_object(storage_mapping, filename)
        return storage_mapping

    def imple2funcSigMap(self, contractAddress: str, implementationAddress: str):
        filename = "{}_funcSigMap".format(contractAddress.lower())
        funcSigMap2 = load_object(filename)

        funcSigMap = self.contract2funcSigMap(implementationAddress)
        for funcSelector in funcSigMap:
            if funcSelector not in funcSigMap2:
                funcSigMap2[funcSelector] = funcSigMap[funcSelector]
        save_object(funcSigMap2, filename)
        # print(funcSigMap2)
        return funcSigMap2



    def contract2funcSigMap(self, contractAddress: str):
        """Given a contract address, return a list of function selectors"""
        """{selector: (name, input_types, output_types)}"""
        """eg. {'0x771602f7': ('add', ['uint256', 'uint256'], ['uint256'], readOnly?)...}"""
        if contractAddress in self.funcSigMapMapping:
            return self.funcSigMapMapping[contractAddress]
        
        filename = "{}_funcSigMap".format(contractAddress.lower())
        funcSigMap2 = load_object(filename)
        if funcSigMap2 is not None:
            self.funcSigMapMapping[contractAddress] = funcSigMap2
            return funcSigMap2
        
        anotherFileName = "UnverifiedAddresses"
        UnverifiedAddresses = load_object(anotherFileName)
        if UnverifiedAddresses is None:
            self.UnverifiedAddresses = []
        else:
            self.UnverifiedAddresses = UnverifiedAddresses
        
        if contractAddress in self.UnverifiedAddresses:
            return {}
        
        # func sig map from public ABI
        funcSigMap = self.crawlEtherscan.Contract2funcSigMap2(contractAddress)
        if len(funcSigMap.keys()) == 0: # means the contract is not verified on etherscan
            self.funcSigMapMapping[contractAddress] = {}
            self.UnverifiedAddresses.append(contractAddress)
            save_object(self.UnverifiedAddresses, anotherFileName)
            return {}
        
        funcSigMap2 = None

        unableCompile = [
            "0x0b89ccd6b803ccec4f0e0fbefaee1f7d16e734e2",
            "0x90995dbd1aae85872451b50a569de947d34ac4ee", 
        ]
        if contractAddress in unableCompile:
            return funcSigMap
        try: 
            self.crawlEtherscan.Contract2Sourcecode(contractAddress)
            if not self.isVyper(contractAddress):
                # func sig map from slither
                funcSigMap2 = self.slitherAnalyzer.Contract2funcSigMap(contractAddress)
            else:
                # func sig map from vyper compile results
                funcSigMap2 = self.vyperAnalyzer.Contract2funcSigMap(contractAddress)
        except Exception as ex:
            print("contractAddress is", contractAddress)
            return funcSigMap
        
        # merge two maps
        for funcSelector in funcSigMap:
            # <funcSelector not in funcSigMap2> means it is a read-only function, in every case, it's a public variable query function. 
            if funcSelector not in funcSigMap2:
                funcSigMap2[funcSelector] = funcSigMap[funcSelector]

        switch_filename = "switchMap"
        switchMap = load_object(switch_filename)
        if switchMap is None:
            switchMap = {}
        keys = list(switchMap.keys())
        for key in keys:
            if "0x" in key:
                switchMap.pop(key)

        # convert non primitive types to address
        for funcSelector in funcSigMap2:
            for jj in [1, 2]:
                if jj == 2 and funcSelector == "constructor":
                    continue
                for ii in range(len(funcSigMap2[funcSelector][jj])):
                    if  funcSigMap2[funcSelector][jj][ii] in switchMap:
                        funcSigMap2[funcSelector][jj][ii] = switchMap[ funcSigMap2[funcSelector][jj][ii] ]
            

        # check if there is a function selector collision
        for funcSelector in funcSigMap:
            if funcSelector == "constructor":
                continue
            if funcSelector in funcSigMap2:
                if ( len(funcSigMap[funcSelector]) != len(funcSigMap2[funcSelector]) \
                or len(funcSigMap[funcSelector][1]) != len(funcSigMap2[funcSelector][1]) \
                or len(funcSigMap[funcSelector][2]) != len(funcSigMap2[funcSelector][2]) \
                or funcSigMap[funcSelector][0] != funcSigMap2[funcSelector][0] ):

                    funcSigMap2[funcSelector] = funcSigMap[funcSelector]
                    # print(funcSigMap[funcSelector])
                    # print(funcSigMap2[funcSelector])
                    # sys.exit("Error: function selector different lengths !")

                for ii in [1, 2]:
                    for jj in range(len(funcSigMap[funcSelector][ii])):
                        if funcSigMap[funcSelector][ii][jj] != funcSigMap2[funcSelector][ii][jj]:
                           switchMap[ copy.deepcopy(funcSigMap2[funcSelector][ii][jj]) ] = funcSigMap[funcSelector][ii][jj]
                           funcSigMap2[funcSelector][ii][jj] = funcSigMap[funcSelector][ii][jj]


        self.funcSigMapMapping[contractAddress] = funcSigMap2
        save_object(switchMap, switch_filename)        
        save_object(funcSigMap2, filename)

        return funcSigMap2


    def contract2funcSelectors(self, contractAddress: str) -> list:
        """Given a contract address, return a list of function selectors"""
        funcSigMap = self.contract2funcSigMap(contractAddress)
        funcSelectors = list(funcSigMap.keys())
        print(funcSelectors)
        return funcSelectors

    def isVyper(self, contractAddress: str):
        """Given a contract address, return True if the contract is Vyper"""
        if contractAddress in self.isVyperCache:
            return self.isVyperCache[contractAddress]
            
        CompilerVersion, _ = self.vyperAnalyzer.contract2Sourcecode(contractAddress)
        if CompilerVersion is None or (not CompilerVersion.startswith("vyper")):
            self.isVyperCache[contractAddress] = False
            return False
        self.isVyperCache[contractAddress] = True
        return True





if __name__ == "__main__":
    analyzer = Analyzer()
    # analyzer.contract2storageMapping("0x15fda9f60310d09fea54e3c99d1197dff5107248")

    # analyzer.imple2funcSigMap("0x2069043d7556b1207a505eb459d18d908df29b55", "0xc68bf77e33f1df59d8247dd564da4c8c81519db6")
    # analyzer.imple2funcSigMap("0x44fbebd2f576670a6c33f6fc0b00aa8c5753b322", "0x3c710b981f5ef28da1807ce7ed3f2a28580e0754")

    contract = "0x2320a28f52334d62622cc2eafa15de55f9987ed9"

    # contract = "0xD533a949740bb3306d119CC777fa900bA034cd52"
    funcMap = analyzer.contract2funcSigMap(contract)
    print(funcMap)

#     # EMN contract
#     contractAddress = "0x5ade7aE8660293F2ebfcEfaba91d141d72d221e8"

#     # Yearn contract
#     contractAddress = "0xacd43e627e64355f1861cec6d3a6688b31a6f952"
# #  KeyError: '0xf8897945'

#     funcSigMap = analyzer.contract2funcSigMap(contractAddress)

#     # StrategyDAI3pool
#     contractAddress = "0x9c211bfa6dc329c5e757a223fb72f5481d676dc1"
#     funcSigMap = analyzer.contract2funcSigMap(contractAddress)

#     # test isVyper
#     # EMN contract
#     contractAddress = "0x5ade7aE8660293F2ebfcEfaba91d141d72d221e8"
#     print(analyzer.isVyper(contractAddress))

    # contractAddress = "0x6b175474e89094c44da98b954eedeac495271d0f"
    # funcSigMap = analyzer.contract2funcSigMap(contractAddress)
    # import pprint
    # pp = pprint.PrettyPrinter(indent=4)
    # pp.pprint(funcSigMap)


    # # test contract2storageMapping
    # contractAddress = "0xd77e28a1b9a9cfe1fc2eee70e391c05d25853cbf"
    # storageMapping = analyzer.contract2storageMapping(contractAddress)
    # print(storageMapping)

    
    # ('0x85ca13d8496b2d22d6...1e096dd7e0', 'Mapping', '00000000000000000000...0000000019', 'CALLER', '0x195f9f44489b43e04', 5527)


    





