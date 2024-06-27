import sys
import os
from parserPackage.locator import *
from parserPackage.parser import proxyMap
from trackerPackage.dataSource import *
from crawlPackage.crawlQuicknode import CrawlQuickNode
from crawlPackage.crawlEtherscan import CrawlEtherscan
from utilsPackage.compressor import *
from parserPackage.decoder import *

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

import toml
settings = toml.load("settings.toml")

import numpy as np




["0x6c3f90f043a72fa612cbac8115ee7e52bde6e490", # 3cRV good! 2 sstores  transferFrom 0, 1
 "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48", # USDC good! 2 sstores 
 "0xdac17f958d2ee523a2206206994597c13d831ec7", # USDT good! 2 sstores
 "0x853d955acef822db058eb8505911ed77f175b99e", # Frax good! 2 sstores
 "0x6b175474e89094c44da98b954eedeac495271d0f", # DAI good! 2 sstores
 "0x865377367054516e17014ccded1e7d814edc9ce4", # DOLA good! 2 sstores
 "0xff20817765cb7f73d4bde2e66e067e58d11095c2", # AMP CreamFi1_1
 "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984", # UNI good! 2 sstores
 "0x956f47f50a910163d8bf957cf5846d573e7f87ca", # FEI good! 2 sstores
 "0xf938424f7210f31df2aee3011291b658f872e91e", # Visor good! 2 sstores
 "0xb1bbeea2da2905e6b0a30203aef55c399c53d042", # Uniswap UMB4 good! 2 sstores
 "0x56de8bc61346321d4f2211e3ac3c0a7f00db9b76"] # Rena good! 2 sstores

benchmark2token = {
    "BeanstalkFarms": "0x6c3f90f043a72fa612cbac8115ee7e52bde6e490", 
    "BeanstalkFarms_interface": None,
    "HarmonyBridge": "ether",
    "HarmonyBridge_interface": "ether",
    "XCarnival": "ether",
    "RariCapital2_1": "ether",
    "RariCapital2_2": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
    "RariCapital2_3": "0xdac17f958d2ee523a2206206994597c13d831ec7",
    "RariCapital2_4": "0x853d955acef822db058eb8505911ed77f175b99e",
    "DODO": "0xdac17f958d2ee523a2206206994597c13d831ec7",
    "PickleFi": "0x6b175474e89094c44da98b954eedeac495271d0f",
    "Nomad": "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599",
    "PolyNetwork": "ether",
    "Punk_1": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
    "Punk_2": "0xdac17f958d2ee523a2206206994597c13d831ec7",
    "Punk_3": "0x6b175474e89094c44da98b954eedeac495271d0f",
    "SaddleFi": "0x6b175474e89094c44da98b954eedeac495271d0f",
    "Eminence": "0x6b175474e89094c44da98b954eedeac495271d0f",
    "Harvest1_fUSDT": "0xdac17f958d2ee523a2206206994597c13d831ec7",
    "Harvest2_fUSDC": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
    "bZx2": "ether",
    "Warp": "0x6b175474e89094c44da98b954eedeac495271d0f", 
    "Warp_interface": "0x6b175474e89094c44da98b954eedeac495271d0f",
    "CheeseBank_1": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
    "CheeseBank_2": "0xdac17f958d2ee523a2206206994597c13d831ec7",
    "CheeseBank_3": "0x6b175474e89094c44da98b954eedeac495271d0f",
    "ValueDeFi": "0x6c3f90f043a72fa612cbac8115ee7e52bde6e490",
    "InverseFi": "0x865377367054516e17014ccded1e7d814edc9ce4",
    "Yearn1":  "0x6b175474e89094c44da98b954eedeac495271d0f",
    "Yearn1_interface":  "0x6b175474e89094c44da98b954eedeac495271d0f",
    "Opyn": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
    "CreamFi1_1": "0xff20817765cb7f73d4bde2e66e067e58d11095c2",
    "CreamFi1_2": "ether",
    "IndexFi": "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",
    "CreamFi2_1": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
    "CreamFi2_2": "0xdac17f958d2ee523a2206206994597c13d831ec7",
    "CreamFi2_3": "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",
    "CreamFi2_4": "0x956f47f50a910163d8bf957cf5846d573e7f87ca",
    "RariCapital1": "ether", 
    "VisorFi": "0xf938424f7210f31df2aee3011291b658f872e91e",
    "UmbrellaNetwork": "0xb1bbeea2da2905e6b0a30203aef55c399c53d042",
    "RevestFi": "0x56de8bc61346321d4f2211e3ac3c0a7f00db9b76",
    "RevestFi_interface": None,
    "RoninNetwork": "ether"

}


benchmark2vault = {
    "BeanstalkFarms": "0x3a70dfa7d2262988064a2d051dd47521e43c9bdd", 
    "BeanstalkFarms_interface": "0xc1e088fc1323b20bcbee9bd1b9fc9546db5624c5",
    "HarmonyBridge": "0xf9fb1c508ff49f78b60d3a96dea99fa5d7f3a8a6",
    "HarmonyBridge_interface": "0x715cdda5e9ad30a0ced14940f9997ee611496de6",
    "XCarnival": "0xb38707e31c813f832ef71c70731ed80b45b85b2d", # 0x5417da20ac8157dd5c07230cfc2b226fdcfc5663",
    "RariCapital2_1": "0x26267e41ceca7c8e0f143554af707336f27fa051",
    "RariCapital2_2": "0xebe0d1cb6a0b8569929e062d67bfbc07608f0a47",
    "RariCapital2_3": "0xe097783483d1b7527152ef8b150b99b9b2700c8d",
    "RariCapital2_4": "0x8922c1147e141c055fddfc0ed5a119f3378c8ef8",
    "DODO": "0x051ebd717311350f1684f89335bed4abd083a2b6", # "0x509ef8c68e7d246aab686b6d9929998282a941fb", # "0x2bbd66fc4898242bdbd2583bbe1d76e8b8f71445",
    # "PickleFi": "0x6949bb624e8e8a90f87cd2058139fcd77d2f3f87", # "0x6847259b2B3A4c17e7c43C54409810aF48bA5210",
    "PickleFi": "0x6949bb624e8e8a90f87cd2058139fcd77d2f3f87", # "0x6847259b2B3A4c17e7c43C54409810aF48bA5210",

    "Nomad": "0x88a69b4e698a4b090df6cf5bd7b2d47325ad30a3",
    "PolyNetwork": "0x250e76987d838a75310c34bf422ea9f1ac4cc906",
    # "Punk_1": "0x3BC6aA2D25313ad794b2D67f83f21D341cc3f5fb",
    # "Punk_2": "0x1F3b04c8c96A31C7920372FFa95371C80A4bfb0D",
    # "Punk_3": "0x929cb86046E421abF7e1e02dE7836742654D49d6",
    "SaddleFi": "0x2069043d7556b1207a505eb459d18d908df29b55",

    "Eminence": "0x5ade7aE8660293F2ebfcEfaba91d141d72d221e8",
    "Harvest1_fUSDT": "0x053c80ea73dc6941f518a68e2fc52ac45bde7c9c",
    "Harvest2_fUSDC": "0xf0358e8c3cd5fa238a29301d0bea3d63a17bedbe",
    # "bZx2": "0x77f973fcaf871459aa58cd81881ce453759281bc",
    "Warp": "0x6046c3Ab74e6cE761d218B9117d5c63200f4b406", 
    "Warp_interface": "0xba539b9a5c2d412cb10e5770435f362094f9541c",
    "CheeseBank_1": "0x5E181bDde2fA8af7265CB3124735E9a13779c021",
    "CheeseBank_2": "0x4c2a8A820940003cfE4a16294B239C8C55F29695",
    "CheeseBank_3": "0xA80e737Ded94E8D2483ec8d2E52892D9Eb94cF1f",
    # "ValueDeFi": "0x55bf8304c78ba6fe47fd251f37d7beb485f86d26",  # "0xddd7df28b1fb668b77860b473af819b03db61101"
    "ValueDeFi": "0x55bf8304c78ba6fe47fd251f37d7beb485f86d26",  # "0xddd7df28b1fb668b77860b473af819b03db61101"

    "InverseFi": "0x7Fcb7DAC61eE35b3D4a51117A7c58D53f0a8a670",
    # "Yearn1":  "0x9c211bfa6dc329c5e757a223fb72f5481d676dc1", will not be used
    # "Yearn1":  "0x9c211bfa6dc329c5e757a223fb72f5481d676dc1", will not be used

    "Yearn1_interface": "0xacd43e627e64355f1861cec6d3a6688b31a6f952",
    "Opyn": "0x951d51baefb72319d9fbe941e1615938d89abfe2",
    "CreamFi1_1": "0x2db6c82ce72c8d7d770ba1b5f5ed0b6e075066d6",  # 0x3c710b981f5ef28da1807ce7ed3f2a28580e0754
    "CreamFi1_2": "0xd06527d5e56a3495252a528c4987003b712860ee",
    "IndexFi": "0xfa6de2697d59e88ed7fc4dfe5a33dac43565ea41", # "0x5bd628141c62a901e0a83e630ce5fafa95bbdee4",
    "CreamFi2_1": "0x44fbebd2f576670a6c33f6fc0b00aa8c5753b322",
    "CreamFi2_2": "0x797aab1ce7c01eb727ab980762ba88e7133d2157",
    "CreamFi2_3": "0xe89a6d0509faf730bd707bf868d9a2a744a363c7",
    "CreamFi2_4": "0x8c3b7a4320ba70f8239f83770c4015b5bc4e6f91",
    # "RariCapital1": "0xa422890cbbe5eaa8f1c88590fbab7f319d7e24b6", # 0xd6e194af3d9674b62d1b30ec676030c23961275e", # "0xec260f5a7a729bb3d0c42d292de159b4cb1844a3", 
    "VisorFi": "0xc9f27a50f82571c1c8423a42970613b8dbda14ef",
    "UmbrellaNetwork": "0xb3fb1d01b07a706736ca175f827e4f56021b85de",
    "RevestFi": "0xa81bd16aa6f6b25e66965a2f842e9c806c0aa11f",
    "RevestFi_interface": "0x2320a28f52334d62622cc2eafa15de55f9987ed9",
    "RoninNetwork": "0x1a2a1c938ce3ec39b6d47113c7955baa9dd454f2",  # 0x8407dc57739bcda7aa53ca6f12f82f9d51c2f21e

}

# the benchmark contracts that does not support money flow ratio analysis
vaultContractBenchmarks = ["Punk_1", "Punk_2", "Punk_3", \
                           "ValueDeFi", "Yearn1", "RariCapital1", \
                            "bZx2", "PickleFi"]

vaultContractBenchmarks = ["bZx2", "RariCapital1"]


etherBenchmarks = [
    "bZx2", "RoninNetwork", "HarmonyBridge", "XCarnival", \
    'RariCapital2_1', "RariCapital1", "PolyNetwork", \
    "IndexFi"  # UNI, its transfer and transferFrom haev multiple sstores
]


# check X invariants
# 1. upper bounds for data flow
# 2. ranges for data flow

def inferMoneyFlows(executionTable, originalContract, transferToken):
    crawlQuickNode = CrawlQuickNode()
    crawlEtherscan = CrawlEtherscan()

    
    for contract, executionList in executionTable:
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
        moneyFlowMap = {
        # { "func+type": 
        #          { 
        #             "transferAmount": []
        #             "transferPC": []
        #             "transferTokenBalance": []
        #          }
        # }
        }

        lastBlockBalance = [0, 0]
        blocks = []

        for tx, dataS in executionList:
            if tx == "0x30fd944ddd5a68a9ab05048a243b852daf5f707e0448696b172cea89e757f4e5" or \
                tx == "0x7ae864faf81979eba3bffa7a2a72f4ded858694ced79c63d613020d064bc06f4":
                # buggy tx
                continue


            sources = dataS["sources"]
            children = dataS["children"]
            metaData = dataS["metaData"]

            targetFunc = metaData["targetFunc"]
            targetFuncType = metaData["targetFuncType"]
            name = targetFunc + "+" + targetFuncType 

            if name not in moneyFlowMap:
                moneyFlowMap[ name ] = {
                    "transferAmount": [], 
                    "transferPC": [],
                }

            pc = None
            if "pc" in metaData:
                pc = metaData["pc"]
            elif len(sources) == 1 and isinstance(sources[0], str) and sources[0] ==  "msg.value":
                pc = -1
            else:
                sys.exit("dataFlowInfer: pc is not in metaData")
            if pc == None:
                sys.exit("dataFlowInfer: pc is None")
            # gas = metaData["gas"]
            # type = metaData["type"]
            # if type != "uint256":
            #     print(type)

            transferAmount = None
            if "value" in metaData:
                transferAmount = metaData["value"]
            elif len(sources) == 1 and isinstance(sources[0], str) and sources[0] ==  "msg.value":
                # if "msg.value" not in metaData:
                #     print(tx)
                #     continue
                transferAmount = metaData["msg.value"] 
                if isinstance(transferAmount, str):
                    transferAmount = int(transferAmount, 16)
            else:
                print(sources)
                sys.exit("dataFlowInfer: transferAmount is not in metaData")
            
            if isinstance(transferAmount, str):
                transferAmount = int(transferAmount, 16)
            
            if transferAmount == None:
                print(sources)
                sys.exit("dataFlowInfer: transferAmount is None")


            moneyFlowMap[name]["transferAmount"].append(transferAmount)
            moneyFlowMap[name]["transferPC"].append(pc)

            transferTokenBalance = None
            block = crawlQuickNode.Tx2Block(tx)
            if "sstore" in metaData and len(metaData["sstore"]) == 3 and isinstance(metaData["sstore"][0], str) and \
                (metaData["sstore"][0] == "transferFrom" or metaData["sstore"][0] == "transfer"):
                if metaData["sstore"][0] == "transferFrom":
                    postBalance = int(metaData["sstore"][2][1], 16)
                    transferTokenBalance = postBalance - transferAmount
                    lastBlockBalance = [block, transferTokenBalance]
                elif metaData["sstore"][0] == "transfer":
                    postBalance = int(metaData["sstore"][1][1], 16)
                    transferTokenBalance = postBalance + transferAmount
                    lastBlockBalance = [block, transferTokenBalance]
            else:
                # print("sstore not in metaData")
                if block not in blocks:
                    blocks.append(block)
                    blocks.append(block - 1)

                transferTokenBalance = None
                if lastBlockBalance[0] == block - 1:
                    transferTokenBalance = lastBlockBalance[1]
                else:
                    if lastBlockBalance[0] != 0:
                        # we are about to replace lastBlockBalance
                        temp = crawlQuickNode.TokenBalanceOf(transferToken, originalContract, lastBlockBalance[0] + 1)
                        if temp != lastBlockBalance[1]:
                            print("dataFlowInfer: error: temp={} != lastBlockBalance[1]={}".format(temp, lastBlockBalance[1]))
                            sys.exit(0)
                    transferTokenBalance = crawlQuickNode.TokenBalanceOf(transferToken, originalContract, block - 1)
                    lastBlockBalance = [block - 1, transferTokenBalance]
                    # print("lastBlockBalance = {}".format(lastBlockBalance))
            
            if targetFuncType == "withdraw" or targetFuncType == "invest":
                lastBlockBalance[1] -= transferAmount
                if lastBlockBalance[1] < 0:
                    sys.exit("dataFlowInfer: lastBlockBalance[1] < 0")
            elif targetFuncType == "deposit":
                lastBlockBalance[1] += transferAmount
            else:
                sys.exit("dataFlowInfer: targetFuncType is not withdraw or invest or deposit")

            if name in moneyFlowMap and "transferTokenBalance" in moneyFlowMap[name]:
                moneyFlowMap[name]["transferTokenBalance"].append(transferTokenBalance)


        for name in moneyFlowMap:
            if "transferPC" in moneyFlowMap[name] and len(moneyFlowMap[name]["transferPC"]) >= 2:
                maxPC = max(moneyFlowMap[name]["transferPC"])
                minPC = min(moneyFlowMap[name]["transferPC"])
                if maxPC != minPC and name != "unlock+withdraw" and name != "borrowTokenFromDeposit+deposit" and \
                    name != "deposit+deposit" and name != "redeemUnderlying+withdraw":
                    print("name = {}, maxPC = {}, minPC = {}".format(name, maxPC, minPC))
                    # sys.exit("dataFlowInfer: error: maxPC != minPC")

                
        invariantMap = {
        # { "func": 
        #          { 
        #             "transferAmount": (smallest value, largest value)
        #             "transferRatio": (smallest value, largest value)
        #          }
        # }
        }

        # stage 2: infer
        # print(moneyFlowMap)
        for func in moneyFlowMap:
            maxValue = max(moneyFlowMap[func]["transferAmount"])
            minValue = min(moneyFlowMap[func]["transferAmount"])
            if len(moneyFlowMap[func]["transferAmount"]) >= 2 and maxValue != minValue:
                invariantMap[func] = {"transferAmount": (minValue, maxValue)}

        for func in moneyFlowMap:
            # transferRatio = transferAmount / transferTokenBalance
            if "transferAmount" in moneyFlowMap[func] and "transferTokenBalance" in moneyFlowMap[func]:
                transferRatioList = []
                for x, y in zip(moneyFlowMap[func]["transferAmount"], moneyFlowMap[func]["transferTokenBalance"]):
                    if y == 0 or x == 0:
                        continue
                    transferRatioList.append(x / y)
                # apply z-score method to filter outliers
                data = np.array(transferRatioList)
                data_mean = np.mean(data)
                data_std = np.std(data)
                transferRatioList = [x for x in transferRatioList if abs(x - data_mean) <= 3 * data_std]
                maxValue = max(transferRatioList)
                minValue = min(transferRatioList)
                if len(transferRatioList) >= 2 and maxValue != minValue:
                    invariantMap[func]["transferRatio"] = (minValue, maxValue)

        print("==invariant map: ")
        print(invariantMap)
        print("Interpretation of the above invariant map: ")

        print("For the invariant moneyFlow:")

        for func in invariantMap:
            print("\tIt can be applied to function {}:".format(func))
            print("\t with lowerbound of transferAmount = {}".format(invariantMap[func]["transferAmount"][0]))
            print("\t with upperbound of transferAmount = {}".format(invariantMap[func]["transferAmount"][1]))

            