import os
import sys
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from crawlPackage.crawlEtherscan import CrawlEtherscan
# from crawlPackage.crawlQuicknode import CrawlQuickNode
# from crawlPackage.crawlTrueBlocks import CrawlTrueBlocks
from web3 import Web3, HTTPProvider

from slither.slither import Slither
from slither.core.solidity_types.elementary_type import ElementaryType
from slither.core.solidity_types.user_defined_type import UserDefinedType
from slither.core.solidity_types.mapping_type import MappingType
from slither.core.solidity_types.array_type import ArrayType
from slither.core.solidity_types.function_type import FunctionType


import pickle
import math
import copy
import toml
settings = toml.load("settings.toml")





"""This is a wapper class for slither"""
class slitherAnalyzer:
    def __init__(self) -> None:
        self.etherScan = CrawlEtherscan()
        self.cur = None


    def Contract2storageLayout(self, contractAddress: str) -> dict:
        """Given a contract address, return a map (<func selector> -> <func signature>)"""
        if not self.etherScan.isVerified(contractAddress):
            return {}
        slither = Slither(contractAddress, **{"etherscan_api_key": self.etherScan.getEtherScanAPIkey()} )
        compilation_uints = slither.compilation_units
        if len(compilation_uints) != 1:
            sys.exit("Error: multiple compilation units!")
        compilation_unit = compilation_uints[0]        
        # Compared with compute_storage_layout() from compilation_unit
        # storage_layout2 also includes the constant and immutable variables
        storage_layout = {}
        for contract in compilation_unit.contracts_derived:
            storage_layout[contract.name] = {}
            slot = 0
            offset = 0
            for var in contract.state_variables_ordered:
                _type = var.type
                size, new_slot = var.type.storage_size
                if new_slot:
                    if offset > 0:
                        slot += 1
                        offset = 0
                elif size + offset > 32:
                    slot += 1
                    offset = 0
                storage_layout[contract.name][var.canonical_name] = (
                    slot,
                    offset,
                    _type
                )
                if new_slot:
                    slot += math.ceil(size / 32)
                else:
                    offset += size
        return storage_layout
    
    def Contract2storageMapping(self, contractAddress: str) -> dict:
        """Given a contract address, return a map (<storage slot> -> <list of variables>)"""
        storageLayout = self.Contract2storageLayout(contractAddress)
        storageMapping = self.StorageLayout2StorageMapping(storageLayout)
        return storageMapping


    def parseType(self, _type):
        _type_stored = None
        if isinstance(_type, ElementaryType):
            _type_stored = _type._type
        elif isinstance(_type, UserDefinedType):
            # _type_stored = self.parseType(_type._type)
            _type_stored = str(_type)
        elif isinstance(_type, MappingType):
            _type_stored = (self.parseType(_type._from), self.parseType(_type._to))
        elif isinstance(_type, ArrayType):
            #  print attributes of the array type
            # print("meet arrat type")
            if _type._length is None:
                _type_stored = self.parseType(_type._type) + "[]"
            else:
                _type_stored = self.parseType(_type._type) + "[" + str(_type._length_value) + "]"

        elif isinstance(_type, FunctionType):
            sys.exit("Error! Cannot handle function type for now!")

        return _type_stored


    def StorageLayout2StorageMapping(self, storageLayout: dict) -> dict:
        """Given a storage layout, return a map (<storage slot> -> <list of variables>)"""
        storageMapping = {}
        for contractName in storageLayout:
            for varName in storageLayout[contractName]:
                slot, offset, _type = storageLayout[contractName][varName]
                byte = slot * 32 + offset
                if byte not in storageMapping:
                    """Ideally, _type_stored should be something parsable by eth_abi"""
                    _type_stored = self.parseType(_type)
                    storageMapping[byte] = (varName, _type_stored)
        return storageMapping

    def Contract2funcSigMap(self, contractAddress: str) -> dict:
        """Given a contract address, return a map (<func selector> -> <func signature>)"""

        slither = Slither(contractAddress, **{"etherscan_api_key": self.etherScan.getEtherScanAPIkey()} )
        funcSigMap = {}
        for contract in slither.contracts_derived:
            for function in contract.functions:
                funcSig = function.signature
                # eg. ('rely', ['address'], [])
                funcSigTuple = None
                if function.view or function.pure:
                    funcSigTuple = (funcSig[0], funcSig[1], funcSig[2], True)
                else:
                    funcSigTuple = (funcSig[0], funcSig[1], funcSig[2], False)
                funcSigStr = function.solidity_signature
                # eg. 'rely(address)'
                if funcSig[0] == "constructor":
                    funcSelector = "constructor"
                else:    
                    funcSelector = Web3.keccak(text=funcSigStr).hex()[0:10]
                funcSigMap[funcSelector] = funcSigTuple

        return funcSigMap

    def contract2storageLayout_solc(self, contractAddress: str) -> dict:
        """Given a contract address, return a map (<func selector> -> <func signature>)"""
        storageLayout = self.slitherAnalyzer.Contract2storageLayout(contractAddress)
        return storageLayout
        
    



if __name__ == "__main__":
    slitherAnalyzer = slitherAnalyzer()
    # # test Contract2funcSigMap
    contractAddress = "0x5ade7aE8660293F2ebfcEfaba91d141d72d221e8"

    # Yearn contract
    contractAddress = "0xacd43e627e64355f1861cec6d3a6688b31a6f952"

    # StrategyDAI3pool
    contractAddress = "0x9c211bfa6dc329c5e757a223fb72f5481d676dc1"

    # DAI
    contractAddress = "0x6b175474e89094c44da98b954eedeac495271d0f"

    funcSigMap = slitherAnalyzer.Contract2funcSigMap(contractAddress)
    import pprint
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(funcSigMap)

    # print("=====================================")

    # test Contract2storageLayout
    storageLayout = slitherAnalyzer.Contract2storageLayout(contractAddress)
    print(storageLayout)

    # print("=====================================")

    storageMapping = slitherAnalyzer.StorageLayout2StorageMapping(storageLayout)
    print(storageMapping)

    # Test check if a contract is written in Vyper or not

    # UniswapAddress = "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984"
    # slither = Slither(contractAddress, **{"etherscan_api_key": CrawlEtherscan().getEtherScanAPIkey()} )
    # # Test storage layout
    # storageMapping = slitherAnalyzer.Contract2storageMapping("0x9e65ad11b299ca0abefc2799ddb6314ef2d91080")
    # print(storageMapping)

    # # {0: ('StrategyDAI3pool.want', 'address'), 
    # # 32: ('StrategyDAI3pool._3pool', 'address'), 
    # # 64: ('StrategyDAI3pool._3crv', 'address'), 
    # # 96: ('StrategyDAI3pool.y3crv', 'address'), 
    # # 128: ('StrategyDAI3pool.ypool', 'address'), 
    # # 160: ('StrategyDAI3pool.ycrv', 'address'), 
    # # 192: ('StrategyDAI3pool.yycrv', 'address'), 
    # # 224: ('StrategyDAI3pool.dai', 'address'), 
    # # 256: ('StrategyDAI3pool.ydai', 'address'), 
    # # 288: ('StrategyDAI3pool.usdc', 'address'), 
    # # 320: ('StrategyDAI3pool.yusdc', 'address'), 
    # # 352: ('StrategyDAI3pool.usdt', 'address'), 
    # # 384: ('StrategyDAI3pool.yusdt', 'address'), 
    # # 416: ('StrategyDAI3pool.tusd', 'address'), 
    # # 448: ('StrategyDAI3pool.ytusd', 'address'), 
    # # 480: ('StrategyDAI3pool.governance', 'address'), 
    # # 512: ('StrategyDAI3pool.controller', 'address'), 
    # # 544: ('StrategyDAI3pool.strategist', 'address'), 
    # # 576: ('StrategyDAI3pool.DENOMINATOR', 'uint256'), 
    # # 608: ('StrategyDAI3pool.treasuryFee', 'uint256'), 
    # # 640: ('StrategyDAI3pool.withdrawalFee', 'uint256'), 
    # # 672: ('StrategyDAI3pool.strategistReward', 'uint256'), 
    # # 704: ('StrategyDAI3pool.threshold', 'uint256'), 
    # # 736: ('StrategyDAI3pool.slip', 'uint256'), 
    # # 768: ('StrategyDAI3pool.tank', 'uint256'), 
    # # 800: ('StrategyDAI3pool.p', 'uint256'), 
    # # 832: ('StrategyDAI3pool.flag', 'bool')}
