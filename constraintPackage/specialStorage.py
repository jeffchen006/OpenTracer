import sys
import os
from parserPackage.locator import *
from parserPackage.parser import proxyMap
import copy
from trackerPackage.dataSource import *
from fetchPackage.fetchTrace import fetcher 
from crawlPackage.crawlQuicknode import CrawlQuickNode
from crawlPackage.crawlEtherscan import CrawlEtherscan
from utilsPackage.compressor import *

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

import toml
settings = toml.load("settings.toml")



# check 3 invariants:
# 1. totalsupply
# 2. totalBorrow
# 3. totalReserve

def removePaddingZeros(value: str):
    if value == "0x0000000000000000000000000000000000000000000000000000000000000000":
        return "0x0"
    else:
        # remove padding zeros
        temp = value
        if temp.startswith("0x"):
            temp = temp[2:]
        temp = temp.lstrip("0")
        temp = "0x" + temp
        return temp




def contractSlot2Type(contract, slot):
    tag = None # totalSupply, totalBorrow

    if len(slot) > 7:
        return None
    
    # CheeseBank_1
    if contract == "0x5e181bdde2fa8af7265cb3124735e9a13779c021".lower():
        # https://evm.storage/eth/18021920/0x5e181bdde2fa8af7265cb3124735e9a13779c021
        if slot == "0xb": # totalBorrow
            tag = "totalBorrow"
        elif slot == "0xc": # totalReserve
            tag = "totalReserve"
        elif slot == "0xd": # totalSupply
            tag = "totalSupply"
    
    # CheeseBank_2
    if contract == "0x4c2a8A820940003cfE4a16294B239C8C55F29695".lower():
        # https://evm.storage/eth/18021920/0x4c2a8A820940003cfE4a16294B239C8C55F29695
        if slot == "0xb": # totalBorrow
            tag = "totalBorrow"
        elif slot == "0xc": # totalReserve
            tag = "totalReserve"
        elif slot == "0xd": # totalSupply
            tag = "totalSupply"

    # CheeseBank_3
    if contract == "0xa80e737ded94e8d2483ec8d2e52892d9eb94cf1f".lower():
        # https://evm.storage/eth/18021920/
        if slot == "0xb": # totalBorrow
            tag = "totalBorrow"
        elif slot == "0xc": # totalReserve
            tag = "totalReserve"
        elif slot == "0xd": # totalSupply
            tag = "totalSupply"


    # bZx2
    if contract == "0x85ca13d8496b2d22d6518faeb524911e096dd7e0".lower():
        # https://evm.storage/eth/17931184/0x85ca13d8496b2d22d6518faeb524911e096dd7e0
        if slot == "0x1b": # totalSupply
            tag = "totalSupply"
        elif slot == "0x15": # totalAssetBorrow
            tag = "totalBorrow"
        elif slot == "0xc": # rateMultiplier
            tag = "variable"
        elif slot == "0xb": # baseRate
            tag = "variable"
        elif slot == "0x8": # loanTokenAddress
            tag = "variable"

    # Warp
    if contract == "0x6046c3Ab74e6cE761d218B9117d5c63200f4b406".lower():
        # https://evm.storage/eth/17931184/0x6046c3Ab74e6cE761d218B9117d5c63200f4b406
        if slot == "0x4": # totalBorrow
            tag = "totalBorrow"
        elif slot == "0x5": # totalReserve
            tag = "totalReserve"

    # mainCreamFi1_1
    if contract == "0x3c710b981f5ef28da1807ce7ed3f2a28580e0754".lower():
        # https://evm.storage/eth/17931184/0x3c710b981f5ef28da1807ce7ed3f2a28580e0754
        if slot == "0xa": # borrowIndex
            tag = "variable"
        elif slot == "0xd": # totalSupply
            tag = "totalSupply"
        elif slot == "0xb": # totalBorrows
            tag = "totalBorrow"
        elif slot == "0xc": # totalReserves
            tag = "totalReserve"
        elif slot == "0x13": # internalCash
            tag = "variable"


    # mainCreamFi1_2
    if contract == "0xd06527d5e56a3495252a528c4987003b712860ee".lower():
        # https://evm.storage/eth/17931184/0xd06527d5e56a3495252a528c4987003b712860ee
        if slot == "0xb": # totalBorrows
            tag = "totalBorrow"
        elif slot == "0xc": # totalReserves
            tag = "totalReserve"
        elif slot == "0xd": # totalSupply
            tag = "totalSupply"

    # RariCapital1
    if contract == "0xec260f5a7a729bb3d0c42d292de159b4cb1844a3".lower():
        # https://evm.storage/eth/17931184/0xec260f5a7a729bb3d0c42d292de159b4cb1844a3
        if slot == "0x70": # _netDeposits
            tag = "totalReserve"


    # RariCapital2_1, RariCapital2_2, RariCapital2_3, RariCapital2_4
    if contract == "0x67db14e73c2dce786b5bbbfa4d010deab4bbfcf9".lower():
        # https://evm.storage/eth/17931184/0x67db14e73c2dce786b5bbbfa4d010deab4bbfcf9
        if slot == "0xc": # borrowIndex
            tag = "variable"
        # temporary fix
        elif slot == "0x5": # borrowRateMaxMantissa
            tag = "variable"
        elif slot == "0xb": # accrualBlockNumber
            tag = "variable"
        elif slot == "0xd": # totalBorrows
            tag = "totalBorrow"
        elif slot == "0xe": # totalReserves
            tag = "totalReserve"
        elif slot == "0xf": # totalAdminFees
            tag = "variable"
        elif slot == "0x10": # totalFuseFees
            tag = "variable"
        elif slot == "0x11": # totalSupply
            tag = "totalSupply"

    # mainXCarnival
    if contract == "0x5417da20ac8157dd5c07230cfc2b226fdcfc5663".lower():
        # https://evm.storage/eth/17931184/0x5417da20ac8157dd5c07230cfc2b226fdcfc5663
        if slot == "0x3": # totalSupply
            tag = "totalSupply"
        elif slot == "0xc": # totalReserves
            tag = "totalReserve"
        elif slot == "0xb": # totalBorrows
            tag = "totalBorrow"
        elif slot == "0xf": # totalCash
            tag = "variable"
        elif slot == "0xd": # borrowIndex
            tag = "variable"

    # mainRariCapital2_1, mainRariCapital2_2, mainRariCapital2_3,  mainRariCapital2_4
    if contract == "0xd77e28a1b9a9cfe1fc2eee70e391c05d25853cbf".lower():
        # https://evm.storage/eth/17931184/0xd77e28a1b9a9cfe1fc2eee70e391c05d25853cbf
        if slot == "0x5": # borrowRateMaxMantissa
            tag = "variable"
        elif slot == "0xb": # accrualBlockNumber
            tag = "variable"
        elif slot == "0xd": # totalBorrows
            tag = "variable"
            tag = "totalBorrow"
        elif slot == "0xe": # totalReserves
            tag = "variable"
            tag = "totalReserve"
        elif slot == "0xf": # totalAdminFees
            tag = "variable"
        elif slot == "0x10": # totalFuseFees
            tag = "variable"
        elif slot == "0x11": # totalSupply
            tag = "totalSupply"

    #  mainHarvest2_fUSDC and mainHarvest1_fUSDT
    if contract == "0x9b3be0cc5dd26fd0254088d03d8206792715588b".lower():
        # https://evm.storage/eth/17931184/0x9b3be0cc5dd26fd0254088d03d8206792715588b
        # https://vscode.blockscan.com/ethereum/0x9b3be0cc5dd26fd0254088d03d8206792715588b#line1032
        if slot == "0x35": # _totalSupply 
            tag = "totalSupply"

    # mainValueDeFi
    if contract == "0xddd7df28b1fb668b77860b473af819b03db61101".lower():
        # https://evm.storage/eth/17931184/0xddd7df28b1fb668b77860b47sender3af819b03db61101
        if slot == "0x9e": # min
            tag = "variable"
        elif slot == "0x67": # _totalSupply
            tag = "totalSupply"
        elif slot == "0xa3": # insurance
            tag = "variable"
        elif slot == "0x97": # basedToken
            type = "address"
    
    # BeanstalkFarms
    if contract == "0x5f890841f657d90e081babdb532a05996af79fe6".lower():
        # https://evm.storage/eth/17931184/0x5f890841f657d90e081babdb532a05996af79fe6
        if slot == "0x4": # fee 
            tag = "variable"
        elif slot == "0xc": # rate_multiplier
            tag = "variable"
        elif slot == "0x9": # future_A
            tag = "variable"
        elif slot == "0x11": # totalSupply
            tag = "totalSupply"

    # Dodo
    if contract == "0x2bbd66fc4898242bdbd2583bbe1d76e8b8f71445".lower():
        # https://evm.storage/eth/17931184/0x2bbd66fc4898242bdbd2583bbe1d76e8b8f71445
        if slot == "0x8":  # totalSupply
            tag = "totalSupply"
        elif slot == "0x3": # _block_timestamp_last   _QUOTE_RESERVE_     _BASE_RESERVE_  
            type = "uint"
        elif slot == "0x1": # _BASE_TOKEN_
            type = "address"
        elif slot == "0x10": # _I_
            tag = "variable"
        elif slot == "0xd": # _LP_FEE_RATE_
            tag = "variable"
        elif slot == "0xf": # _K_
            tag = "variable"
    # Yearn
    if contract == "0x9c211bfa6dc329c5e757a223fb72f5481d676dc1".lower():
        # https://evm.storage/eth/17931184/0x9c211bfa6dc329c5e757a223fb72f5481d676dc1
        if slot == "0x7": # slip
            tag = "variable"
        elif slot == "0x8": # tank
            tag = "variable"
        elif slot == "0x4": # withdrawalFee
            tag = "variable"

    # Eminence:
    if contract == "0x5ade7aE8660293F2ebfcEfaba91d141d72d221e8".lower():
        # https://evm.storage/eth/17931184/0x5ade7aE8660293F2ebfcEfaba91d141d72d221e8
        if slot == "0x2": # _totalSupply
            tag = "totalSupply"
        elif slot == "0x4": # reserveBalance
            tag = "totalReserve"
        elif slot == "0x5": # reserveRatio
            type = "uint32"

    # indexFi
    if contract == "0x5bd628141c62a901e0a83e630ce5fafa95bbdee4".lower():
        # https://evm.storage/eth/17931184/0x5bd628141c62a901e0a83e630ce5fafa95bbdee4
        if slot == "0x7": # _swapFee
            tag = "variable"
        elif slot == "0x2": # _totalSupply
            tag = "totalSupply"
        elif slot == "0xa": # _totalWeight
            tag = "variable"

    # InverseFi
    if contract == "0x7Fcb7DAC61eE35b3D4a51117A7c58D53f0a8a670".lower():
        # https://evm.storage/eth/17931184/0x7Fcb7DAC61eE35b3D4a51117A7c58D53f0a8a670
        if slot == "0xd": # totalSupply
            tag = "totalSupply"
        elif slot == "0xc": # totalReserves
            tag = "totalReserve"
        elif slot == "0xb": # totalBorrows            
            tag = "totalBorrow"

    # # Opyn
    # if contract == "0x951d51baefb72319d9fbe941e1615938d89abfe2".lower():
    #     # https://evm.storage/eth/17931184/0x951d51baefb72319d9fbe941e1615938d89abfe2
    #     if slot == "0x16": # 
    #         # IERC20 collateral 
    #         # int32 underlyingExp
    #         # int32 collateralExp 
    #         tag = "variable"
    #     elif slot == "0x10": # exponent
    #         tag = "variable"
    #     elif slot == "0xf": # value
    #         tag = "variable"

    return tag




def inferSpecialStorage(accesslistTable):    
    crawlEtherscan = CrawlEtherscan()
    for contract, accessList in accesslistTable:
        if contract in proxyMap:
            contract = proxyMap[contract]
        # build read-only functions
        ABI = crawlEtherscan.Contract2ABI(contract)
        readOnlyFunctions = ["fallback"]
        nonReadOnlyFunctions = []
        for function in ABI:
            if function["type"] == "function" and (function["stateMutability"] == "view" or function["stateMutability"] == "pure"):
                readOnlyFunctions.append(function["name"])
            if function["type"] == "function" and (function["stateMutability"] != "view" and function["stateMutability"] != "pure"):
                nonReadOnlyFunctions.append(function["name"])


        # stage 1: training
        specialStorageMap = {}
        # { 
        #   "slot": (type, [ value1, value2, ... ])
        # }

        for tx, funcCallList in accessList:
            if len(funcCallList) != 1:
                print(funcCallList)
                sys.exit("money flow infer2: not one function call in a transaction")

            for funcCall in funcCallList[0]:
                contract = funcCall["addr"] 
                proxy = funcCall["proxy"] if "proxy" in funcCall else None
                if "sstore" not in funcCall:
                    continue
                for slot, value, pc in funcCall["sstore"]:
                    if isinstance(value, str):
                        value = int(value, 16)
                    tag1 = contractSlot2Type(contract, slot)
                    tag2 = contractSlot2Type(proxy, slot)
                    tag = None
                    if tag1 == "totalSupply" or tag2 == "totalSupply":
                        tag = "totalSupply"
                    elif tag1 == "totalBorrow" or tag2 == "totalBorrow":
                        tag = "totalBorrow"
                    # elif tag1 == "totalReserve" or tag2 == "totalReserve":
                    #     tag = "totalReserve"

                    if tag is not None:
                        if slot not in specialStorageMap:
                            specialStorageMap[slot] = (tag, [value])
                        else:
                            specialStorageMap[slot][1].append(value)
                    
        


        invariantMap = {}
        # { 
        #    "totalSupply": (lowerBound, upperBound),
        #    "totalBorrow": (lowerBound, upperBound),
        # }

        # stage 2: infer
        for slot in specialStorageMap:
            tag, values = specialStorageMap[slot]
            if tag not in invariantMap:
                invariantMap[tag] = (min(values), max(values))
            else:
                sys.exit("special storage: multiple slots for the same tag")

        # print("==specialStorage map: ")
        # print(specialStorageMap)
        print("==invariant map: ")
        print(invariantMap)

