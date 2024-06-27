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
from parserPackage.decoder import *

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

import toml
settings = toml.load("settings.toml")



def precheck(executionList):
    funcList = {}
    for tx, dataS in executionList:
        sources = dataS["sources"]
        children = dataS["children"]
        metaData = dataS["metaData"]

        if not all(v is None for v in children):
            print(children)
            sys.exit("dataFlowInfer: children is not None")

        for source in sources:
            if isinstance(source, dict):
                for ii in range(len(source["inputs"])):
                    if source["inputs"][ii] == metaData["msg.sender"] or source["inputs"][ii] == metaData["tx.origin"]:
                        sys.exit("dataFlowInfer: msg.sender or tx.origin is used as input, but this work should be done in Tracker")
                funcList[source["addr"] + "." + source["name"] + str(source["inputs"])] = metaData
                # print("func {} of contract {} is called".format(source["name"], source["addr"]))
            elif isinstance(source, tuple):
                pass

            elif isinstance(source, str):
                if source == "msg.value":
                    pass
                else:
                    print("source is str")
                    print(source)

    # for entry in funcList:
    #     print(entry)    
    #     print(funcList[entry]) 


def funcMsgDataRange2Type(msgDataStart, msgDataEnd, types):
    index = 4 # for func selector

    if len(types) == 4 and types[0] == "address" and types[1] == "address" and types[2] == "uint256[]" and types[3] == "uint256":
        types = ["address", "address", "uint256", "uint256",  "uint256", "uint256",  "uint256",  "uint256",  "uint256", "uint256", "uint256", "uint256"]
    if len(types) == 2 and types[0] == "uint256[2]" and types[1] == "uint256":
        types = ["uint256", "uint256", "uint256"]

    de = decoder()
    for type in types:
        start = index
        length = de.type2length(type)
        end = index + length
        # print("start = {}, end = {}".format(start, end))
        if start == msgDataStart and end == msgDataEnd:
            # print("Found: ", type)
            # sys.exit(0)
            return type
        index = end
    sys.exit("dataFlowInfer: funcMsgDataRange2Type:  error Cannot find type")


def ABIName2Types(ABI, name: str):
    inputs = []
    for function in ABI:
        if "type" in function and function["type"] == "function" and function["name"] == name:
            for input in function["inputs"]:
                # if input["type"] != input["internalType"]:
                #     print("input[type] = {}".format(input["type"]))
                #     print("input[internalType] = {}".format(input["internalType"]))
                #     sys.exit("dataFlowInfer: error ")
                inputs.append(input["type"])
            return inputs
    sys.exit("dataFlowInfer: ABIName2Types:  error Cannot find types")


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


def readValuePCTypeFromSource(source, metaData, ABI):
    value = None
    pc = None
    type = None
    dataType = None
    if isinstance(source, tuple):
        if source[0] == "msg.data": 
            # should be ('msg.data', start, end, value, pc)


            if len(source) == 4:
                print("error")
                sys.exit("error")
            value = source[3]
            pc = source[-1]
            dataType = "argument"

            if metaData["targetFunc"] == "handle" and source[1] == 164 and source[2] == 297:
                type = "bytes"
            elif metaData["targetFunc"] == "unlock" and source[1] == 132 and source[2] == 206:
                type = "bytes"

            # struct TxArgs {
            #     bytes toAssetHash;
            #     bytes toAddress;
            #     uint256 amount;
            # }
            

            # 0xddc1f59d  
            # 0000000000000000000000000000000000000000000000000000000000000000  0 - 32  i = 0  int128
            # 0000000000000000000000000000000000000000000000000000000000000001  32 - 64  j = 1  int128
            # 000000000000000000000000000000000000000000000000000000001cb783fb  64 - 96  _dx = 0x1cb783fb  uint256
            # 0000000000000000000000000000000000000000000000000000000000000000  96 - 128 _min_dy = 0  uint256
            # 000000000000000000000000a464e6dcda8ac41e03616f95f4bc98a13b8922dc  128 - 160  _receiver = 0xa464e6dcda8ac41e03616f95f4bc98a13b8922dc address

            elif metaData["targetFunc"] == "exchange" and source[3] == 0:
                if source[1] == 132 and source[2] == 196:
                    type = "bytes"
                elif source[1] == 132 and source[2] == 228:
                    type = "bytes"
                elif source[1] == 164 and source[2] == 228:
                    type = "bytes"
                elif source[1] == 164 and source[2] == 260:
                    type = "bytes"

            elif metaData["targetFunc"] == "remove_liquidity_one_coin" and source[3] == 0:
                if source[1] == 132 and source[2] == 196:
                    type = "bytes"
                elif source[1] == 132 and source[2] == 228:
                    type = "bytes"
                elif source[1] == 100 and source[2] == 164:
                    type = "bytes"
                elif source[1] == 100 and source[2] == 196:
                    type = "bytes"
            else:
                types = ABIName2Types(ABI, metaData["targetFunc"])
                type = funcMsgDataRange2Type(source[1], source[2], types)
            
            # if metaData["targetFunc"] == "exchange" and "int" in type:
            #     print(metaData["targetFunc"])
            #     print(source)

        elif source[1] == "SLOAD":
            # remove padding zeros for source[2]
            source = (source[0], source[1], removePaddingZeros(source[2]), source[3])

            # todo storage mapping
            value = int(source[-2], 16)
            pc = source[-1]

            dataType = "storage"


            if len(source[2]) > 7: 
                type = "unknown(toDebug)"
            
            # bZx2
            if source[0] == "0x85ca13d8496b2d22d6518faeb524911e096dd7e0":
                # https://evm.storage/eth/17931184/0x85ca13d8496b2d22d6518faeb524911e096dd7e0
                if source[2] == "0x1b": # totalSupply
                    type = "uint256"
                elif source[2] == "0x15": # totalAssetBorrow
                    type = "uint256"
                elif source[2] == "0xc": # rateMultiplier
                    type = "uint256"
                elif source[2] == "0xb": # baseRate
                    type = "uint256"
                elif source[2] == "0x8": # loanTokenAddress
                    type = "address"
                elif source[2] == "0x7401a89df8a9dd78c2fa76725dfb51036ea142fc2baf6d8388f41af046c1690" or \
                    source[2] == "0x312c53086145320a8a8445bc3e3bf2208a6063363d3fdc561900226a66f81fe":
                    type = "unknown(toDebug)"
                    type = None

            # mainCreamFi1_1
            if source[0] == "0x3c710b981f5ef28da1807ce7ed3f2a28580e0754":
                # https://evm.storage/eth/17931184/0x3c710b981f5ef28da1807ce7ed3f2a28580e0754
                if source[2] == "0x175ae2e7110df3644daf25235f8a30489611f42116e1143164cddbda86763564" or \
                    source[2] == "0x39f7066fe7087b8b36bddb5699da6241ebfe90c61eaa733be5bd394055ccc95b" or \
                    source[2] == "0xe1fd333728a368ab7d362d86ee1061afb1e3c9360949dd90f4b3ed0c255118c" or \
                    source[2] == "0xe1fd333728a368ab7d362d86ee1061afb1e3c9360949dd90f4b3ed0c255118b":
                    type = "unknown(toDebug)"
                elif len(source[2]) > 7: 
                    type = "unknown(toDebug)"
                elif source[2] == "0xa": # borrowIndex
                    type = "uint256"
                elif source[2] == "0xd": # totalSupply
                    type = "uint256"
                elif source[2] == "0xb": # totalBorrows
                    type = "uint256"
                elif source[2] == "0xc": # totalReserves
                    type = "uint256"
                elif source[2] == "0x13": # internalCash
                    type = "uint256"

            # RariCapital2_1, RariCapital2_2, RariCapital2_3, RariCapital2_4
            if source[0] == "0x67db14e73c2dce786b5bbbfa4d010deab4bbfcf9":
                # https://evm.storage/eth/17931184/0x67db14e73c2dce786b5bbbfa4d010deab4bbfcf9
                if source[2] == "0x4132299f61b68b6f8d596dda582c1f57aa3301267d410645b4107420e0303db9":
                    type = "unknown(toDebug)"
                elif source[2] == "0xc": # borrowIndex
                    type = "uint256"
                # temporary fix
                elif source[2] == "0x5": # borrowRateMaxMantissa
                    type = "uint256"
                elif source[2] == "0xb": # accrualBlockNumber
                    type = "uint256"
                elif source[2] == "0xd": # totalBorrows
                    type = "uint256"
                elif source[2] == "0xe": # totalReserves
                    type = "uint256"
                elif source[2] == "0xf": # totalAdminFees
                    type = "uint256"
                elif source[2] == "0x10": # totalFuseFees
                    type = "uint256"
                elif source[2] == "0x11": # totalSupply
                    type = "uint256"


                elif source[2] == "0x80dbc5d3f0e0389e0b8d69a7ab375b8d56c6b51af32790997a9c525d16f73bd":
                    type = "unknown(toDebug)"
                elif source[2] == "0x80dbc5d3f0e0389e0b8d69a7ab375b8d56c6b51af32790997a9c525d16f73bc":
                    type = "unknown(toDebug)"
                elif source[2] == "0x708aa9625783bc519922701c9fd51c68eeb57a08c2ad164a6a993406a3c54626" or \
                    source[2] == "0x505c80be4ea04e60e068fc17a4e2aacedd0ffa2eb884b1c1431b48867bb183a" or \
                    source[2] == "0x505c80be4ea04e60e068fc17a4e2aacedd0ffa2eb884b1c1431b48867bb1839" or \
                    source[2] == "0x1054ddf7a1ff0d6eb7ee6aad404213ec0509ebfd3d990dfa4d41b6723803d685" or \
                    source[2] == "0xdd0766d0e33e8644542c47e62d93499b074e63cfa4634ec10d3fb82a96f056b4" or \
                    source[2] == "0x8802a1109073a266a8a3cd91ebf1aa11ceb66d9ab8c74b0ad946a721b5c02d9b" or \
                    source[2] == "0x38aba75aa7a13f06d8666d042c65a635740f79e93ad07243e589a1225acdf6ca" or \
                    source[2] == "0x6ea343eccd71e6ae52094a60d4899e7bc51622b406ce4164793d2e1ad41813ef" or \
                    source[2] == "0x1e46977cbe524007d4f220c1ce9c859c506baeaa284a8e32ad9e5dbef3c41c52" or \
                    source[2] == "0xed12667540ee44b7cc102a0adfdc1a572f7bfa68436b9e452ea27f486c8938d6" or \
                    source[2] == "0xd4b7454a8a0b0d07774c286444802a162d27215c0f5c7444587940d0bb950e9a" or \
                    source[2] == "0x6b8a6e3ac99e15bca83fdb55f69da00b77c28635275c5d79092fc38b13ae9483" or \
                    source[2] == "0xfd2fccc3e4a07610a93e73b96db95104e3c504cc2def28a03bca173551b809fc":
                    type = "unknown(toDebug)"
                else:
                    print("logs: ", source[2])
                    type = "unknown(toDebug)"
            
            # mainXCarnival
            if source[0] == "0x5417da20ac8157dd5c07230cfc2b226fdcfc5663":
                # https://evm.storage/eth/17931184/0x5417da20ac8157dd5c07230cfc2b226fdcfc5663
                if source[2] == "0x3": # decimals
                    type = "uint8"
                elif source[2] == "0xc": # totalReserves
                    type = "uint256"
                elif source[2] == "0xb": # totalBorrows
                    type = "uint256"
                elif source[2] == "0xf": # totalCash
                    type = "uint256"
                elif source[2] == "0xd": # borrowIndex
                    type = "uint256"
                elif source[2] == "0x5fae251ae169e8e40026ce4ce85a026bc3adcccdc8459be361195e4cd9240780" or \
                    source[2] == "0xf53d7d0eac8d4a28c5e36c803b226f3ef35ce8inferMoneyFlowsff0302108a97c0d862a51c6fa4": 
                    type = "unknown(toDebug)"



            # mainRariCapital2_1, mainRariCapital2_2, mainRariCapital2_3,  mainRariCapital2_4
            if source[0] == "0xd77e28a1b9a9cfe1fc2eee70e391c05d25853cbf":
                # https://evm.storage/eth/17931184/0xd77e28a1b9a9cfe1fc2eee70e391c05d25853cbf
                if source[2] == "0x5": # borrowRateMaxMantissa
                    type = "uint256"
                elif source[2] == "0xb": # accrualBlockNumber
                    type = "uint256"
                elif source[2] == "0xd": # totalBorrows
                    type = "uint256"
                elif source[2] == "0xe": # totalReserves
                    type = "uint256"
                elif source[2] == "0xf": # totalAdminFees
                    type = "uint256"
                elif source[2] == "0x10": # totalFuseFees
                    type = "uint256"
                elif source[2] == "0x11": # totalSupply
                    type = "uint256"

            #  mainHarvest2_fUSDC and mainHarvest1_fUSDT
            if source[0] == "0x9b3be0cc5dd26fd0254088d03d8206792715588b":
                # https://evm.storage/eth/17931184/0x9b3be0cc5dd26fd0254088d03d8206792715588b
                # https://vscode.blockscan.com/ethereum/0x9b3be0cc5dd26fd0254088d03d8206792715588b#line1032
                if source[2] == "0x469a3bad2fab7b936c45eecd1f5da52af89cead3e2ed7f732b6f3fc92ed32308" or \
                    source[2] == "0x39122c9adfb653455d0c05043bd52fcfbc2be864e832efd3abc72ce5a3d7ed5a":
                    #   bytes32 internal constant _VAULT_FRACTION_TO_INVEST_DENOMINATOR_SLOT 
                    # = 0x469a3bad2fab7b936c45eecd1f5da52af89cead3e2ed7f732b6f3fc92ed32308;
                    #   bytes32 internal constant _VAULT_FRACTION_TO_INVEST_NUMERATOR_SLOT 
                    # = 0x39122c9adfb653455d0c05043bd52fcfbc2be864e832efd3abc72ce5a3d7ed5a;
                    type = "uint256"
                elif source[2] == "0x35": # _totalSupply 
                    type = "uint256"

            # mainValueDeFi
            if source[0] == "0xddd7df28b1fb668b77860b473af819b03db61101":
                # https://evm.storage/eth/17931184/0xddd7df28b1fb668b77860b47sender3af819b03db61101
                if source[2] == "0x9e": # min
                    type = "uint256"
                elif source[2] == "0x67": # _totalSupply
                    type = "uint256"
                elif source[2] == "0xa3": # insurance
                    type = "uint256"
                elif source[2] == "0x97": # basedToken
                    type = "address"
                    
            if source[0] == "0x5f890841f657d90e081babdb532a05996af79fe6":
                # https://evm.storage/eth/17931184/0x5f890841f657d90e081babdb532a05996af79fe6
                if source[2] == "0xc2575a0e9e593c00f959f8c92f12db2869c3395a3b0502d05e2516446f71f85c" or \
                    source[2] == "0xc2575a0e9e593c00f959f8c92f12db2869c3395a3b0502d05e2516446f71f85b":
                    type = "uint256" # balances[0], balances[1]
                elif source[2] == "0x4": # fee 
                    type = "uint256"
                elif source[2] == "0xc": # rate_multiplier
                    type = "uint256"
                elif source[2] == "0x9": # future_A
                    type = "uint256"
                elif source[2] == "0x11": # totalSupply:
                    type = "uint256"
            # Dodo
            if source[0] == "0x2bbd66fc4898242bdbd2583bbe1d76e8b8f71445":
                # https://evm.storage/eth/17931184/0x2bbd66fc4898242bdbd2583bbe1d76e8b8f71445
                if source[2] == "0x8":  # totalSupply
                    type = "uint256"
                elif source[2] == "0x3": # _block_timestamp_last   _QUOTE_RESERVE_     _BASE_RESERVE_  
                    type = "uint"
                elif source[2] == "0x1": # _BASE_TOKEN_
                    type = "address"
                elif source[2] == "0x10": # _I_
                    type = "uint256"
                elif source[2] == "0xd": # _LP_FEE_RATE_
                    type = "uint256"
                elif source[2] == "0xf": # _K_
                    type = "uint256"
            # Yearn
            if source[0] == "0x9c211bfa6dc329c5e757a223fb72f5481d676dc1":
                # https://evm.storage/eth/17931184/0x9c211bfa6dc329c5e757a223fb72f5481d676dc1
                if source[2] == "0x7": # slip
                    type = "uint256"
                elif source[2] == "0x8": # tank
                    type = "uint256"
                elif source[2] == "0x4": # withdrawalFee
                    type = "uint256"

            # Yearn_interface
            if source[0] == "0xacd43e627e64355f1861cec6d3a6688b31a6f952":
                # https://evm.storage/eth/17931184/0xacd43e627e64355f1861cec6d3a6688b31a6f952
                if source[2] == "0x2": # _totalSupply
                    type = "uint256"
                elif source[2] == "0x6": # min
                    type = "uint256"
                elif source[2] == "0x5": # token
                    type = "address"

            # Eminence:
            if source[0] == "0x5ade7aE8660293F2ebfcEfaba91d141d72d221e8":
                # https://evm.storage/eth/17931184/0x5ade7aE8660293F2ebfcEfaba91d141d72d221e8
                if source[2] == "0x2": # _totalSupply
                    type = "uint256"
                elif source[2] == "0x4": # reserveBalance
                    type = "uint256"
                elif source[2] == "0x5": # reserveRatio
                    type = "uint32"

            # indexFi
            if source[0] == "0x5bd628141c62a901e0a83e630ce5fafa95bbdee4":
                # https://evm.storage/eth/17931184/0x5bd628141c62a901e0a83e630ce5fafa95bbdee4
                if source[2] == "0x7": # _swapFee
                    type = "uint256"
                elif source[2] == "0x2": # _totalSupply
                    type = "uint256"
                elif source[2] == "0xa": # _totalWeight
                    type = "uint256"

                elif source[2] == "0x27f1d00d974319457b7f4b014e8dc0e0ed663e9946393800361dc41f57c046e" or \
                    source[2] == "0x53dc03a44b06740ad6d18337cb5d144c601fc34ffaee097aeec293d4555bf62c" or \
                    source[2] == "0x27f1d00d974319457b7f4b014e8dc0e0ed663e9946393800361dc41f57c046d" or \
                    source[2] == "0x3f1c90dbdf914a4ad25fb9c9814e0f51ef0c2551722cbb7728bbfc25dffa708b" or \
                    source[2] == "0xd61d9f947a2224b51d54f059447c0eb936e880551a0d14029555a4f5e4c6d441" or \
                    source[2] == "0xbfcc2b9326d560154a295d5f7823ad4bf4002413ac800ade371399e47660f618" or \
                    source[2] == "0x8b63a218d1b565bd827fd00bd44f9414f2fa51ac57b11d2e006e7dff13d7e5fc" or \
                    source[2] == "0x6b91aa999d2dc454b5f5cb0d0d0450562d0b059b8091712274352607fb6ba57d" or \
                    source[2] == "0xf696318862e84cd7fd086a2f4e6aa03ad7846b2556de0b02ff94394799f2312b":

                    type = "unknown(toDebug)"
                elif len(source[2]) >= 7:
                    type = "unknown(toDebug)"
                

            # InverseFi
            if source[0] == "0x7Fcb7DAC61eE35b3D4a51117A7c58D53f0a8a670":
                # https://evm.storage/eth/17931184/0x7Fcb7DAC61eE35b3D4a51117A7c58D53f0a8a670
                if source[2] == "0xd": # totalSupply
                    type = "uint256"
                elif source[2] == "0xc": # totalReserves
                    type = "uint256"
                elif source[2] == "0xb": # totalBorrows            
                    type = "uint256"

            if source[0] == "0x951d51baefb72319d9fbe941e1615938d89abfe2":
                # https://evm.storage/eth/17931184/0x951d51baefb72319d9fbe941e1615938d89abfe2
                if source[2] == "0x16": # 
                    # IERC20 collateral 
                    # int32 underlyingExp
                    # int32 collateralExp 
                    type = "int32"
                elif source[2] == "0x10": # exponent
                    type = "int32"
                elif source[2] == "0xf": # value
                    type = "uint256"
                    


    # 0x11: totalSupply
    # 0xd: totalBorrows
    # 0xe: totalReserves
    # 0xf: totalAdminFees
    # 0x10: totalFuseFees
    # 0x5: borrowRateMaxMantissa

            
        elif source[1] == "Mapping":
            # todo storage mapping
            # print(source)
            value = int(source[-2], 16)
            pc = source[-1]

            dataType = "mapping"

            if len(source) == 6:
                source = (source[0], source[1], source[2], source[3], 0, source[4], source[5])

            # bZx2
            if source[0] == "0x85ca13d8496b2d22d6518faeb524911e096dd7e0" :
                if source[2] == "0000000000000000000000000000000000000000000000000000000000000019":
                # https://evm.storage/eth/17931138/0x85ca13d8496b2d22d6518faeb524911e096dd7e0
                # balances[caller]
                    if  source[3] == "CALLER" and source[4] == 0:
                        type = "uint256"

            if source[0] == "0x3c710b981f5ef28da1807ce7ed3f2a28580e0754":
                # https://evm.storage/eth/17931138/0x3c710b981f5ef28da1807ce7ed3f2a28580e0754
                if source[2] == "0000000000000000000000000000000000000000000000000000000000000010": 
                    # accountBorrows  mapping(address => CTokenStorage.BorrowSnapshot))
                    #     struct BorrowSnapshot {
                    #        uint256 principal;
                    #        uint256 interestIndex;
                    #     }
                    if source[3] == "CALLER" and source[4] == 0:
                        type = "uint256"
                    elif source[3] == "CALLER" and source[4] == 1:
                        type = "uint256"
            
            if source[0] == "0x67db14e73c2dce786b5bbbfa4d010deab4bbfcf9":
                # https://evm.storage/eth/17931138/0x67db14e73c2dce786b5bbbfa4d010deab4bbfcf9
                if source[2] == "0000000000000000000000000000000000000000000000000000000000000014": 
                    # accountBorrows  mapping(address => BorrowSnapshot)
                    #     struct BorrowSnapshot {
                    #     uint principal;
                    #     uint interestIndex;
                    # } 
                    if source[3] == "CALLER":
                        if source[4] == 0 or source[4] == 1:
                            type = "uint256"   


            if source[0] == "0x5417da20ac8157dd5c07230cfc2b226fdcfc5663":
                # https://evm.storage/eth/17931138/0x5417da20ac8157dd5c07230cfc2b226fdcfc5663
                if source[2] == "0000000000000000000000000000000000000000000000000000000000000011":
                     # orderBorrows  mapping(address => XTokenStorage.BorrowSnapshot)
                    # struct BorrowSnapshot {
                    #     uint256 principal;
                    #     uint256 interestIndex;
                    # }
                    if source[3] == "msg.data[4:36]" and source[4] == 0:
                        type = "uint256"
                    if source[3] == "msg.data[4:36]" and source[4] == 1:
                        type = "uint256"
            
            if source[0] == "0x5bd628141c62a901e0a83e630ce5fafa95bbdee4":
                # https://evm.storage/eth/17931138/0x5bd628141c62a901e0a83e630ce5fafa95bbdee4
                if source[2] == "0000000000000000000000000000000000000000000000000000000000000009":
                    # _records  mapping(address => IIndexPool.Record)
                    # struct Record {
                    #     bool bound;
                    #     bool ready;
                    #     uint40 lastDenormUpdate;
                    #     uint96 denorm;
                    #     uint96 desiredDenorm;
                    #     uint8 index;
                    #     uint256 balance;
                    # }
                    if source[3] == "msg.data[4:36]" and source[4] == 0:
                        type = "uint"
                    elif source[3] == "msg.data[4:36]" and source[4] == 1:
                        type = "uint"
                    elif source[3] == "msg.data[68:100]" and source[4] == 0:
                        type = "uint256"
                    elif source[3] == "msg.data[68:100]" and source[4] == 1:
                        type = "uint256"
                    elif source[3] == "0000000000000000000000001f9840a85d5af5bf1d1762f925bdaddc4201f984" and \
                        (source[4] == 0 or source[4] == 1):
                        # UNI token
                        type = "uint256"

                elif source[2] == "000000000000000000000000000000000000000000000000000000000000000b":
                    # _minimumBalances  mapping(address => uint256)
                    if source[3] == "msg.data[4:36]" and source[4] == 0:
                        type = "uint256"

            
            # Yearn_interface
            if source[0] == "0xacd43e627e64355f1861cec6d3a6688b31a6f952":
                # https://evm.storage/eth/17931138/0xacd43e627e64355f1861cec6d3a6688b31a6f952
                if source[2] == "0000000000000000000000000000000000000000000000000000000000000000":  # _balances
                    if source[3] == "CALLER" and source[4] == 0:
                        type = "uint"
            


        elif source[0] == "SELFBALANCE":
            value = source[1]
            if isinstance(value, str):
                value = int(value, 16)
            pc = source[-1]
            type = "uint256"
            dataType = "selfbalance"

        elif source[0] == "CALLVALUE":
            value = metaData["value"]
            if isinstance(value, str):
                value = int(value, 16)
            pc = -1
            type = "uint256"
            dataType = "callvalue"

        elif source[0] == "BALANCE":
            value = source[1]
            if isinstance(value, str):
                value = int(value, 16)
            pc = source[-1]
            type = "uint256"
            dataType = "balance"

        elif source[0] == "ADDRESS" or source[0] == "CALLER" or source[0] == "ORIGIN":
            return None, None, "address", "address"
        else:
            print(source)
            sys.exit("dataFlowRange1: source is not identified")


    elif isinstance(source, str) and source == "msg.value":
        value = metaData["msg.value"]
        if isinstance(value, str):
            value = int(value, 16)
        pc = -1
        type = "uint256"
        dataType = "callvalue"

    elif isinstance(source, dict):
        # todo check output types
        if len(source["outputs"]) == 1:
            value =  source["outputs"][0]
            pc = source["pc"]
            type = source["outputTypes"][0]
        else:
            sys.exit("what to do with multiple outputs?")
        
        if "name" in source:
            
            if source['name'] == 'balanceOf':
                dataType = "balance"

            elif source["name"] == "totalSupply" or source["name"] == "investedUnderlyingBalance" or \
                    source["name"] == "getFeeRate" or source["name"] == "withdrawalProtectionFee" or \
                    source["name"] == "get_virtual_price" :
                dataType = "externalStaticCall"


    if dataType is None:
        print(source)


    return value, pc, type, dataType



# check X invariants
# 1. upper bounds for data flow
# 2. ranges for data flow

def inferDataFlows(executionTable, enterFuncs, exitFuncs):
    crawlQuickNode = CrawlQuickNode()
    crawlEtherscan = CrawlEtherscan()

    for  contract, executionList in executionTable:
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

        # pc = -1 means callvalue
        
        # dataType: mapping
        # only consider <=
        mappingMap = {
        # { "func+type": 
        #          { 
        #             pc: []
        #             "value": [value0, value1, ...]
        #          }
        # }
        # 
        }
        # dataType = callvalue
        # only consider <=
        callvalueMap = {
        # { "func+type": 
        #          { 
        #             pc: []
        #             "value": [value0, value1, ...]
        #          }
        # }
        # 
        }
        # dataType = externalStaticCall/balance/selfbalance/storage/argument
        dataFlowMap = {
        # { "func+type": 
        #          { 
        #             pc: (source, [value0, value1, ...])
        #             "transferAmount": [value0, value1, ...]
        #             "transferPC": [pc0, pc1, pc2, ...]
        #          }
        # }
        }
        # precheck(executionList)
        for tx, dataS in executionList:
            if tx == "0x30fd944ddd5a68a9ab05048a243b852daf5f707e0448696b172cea89e757f4e5":
                # buggy tx
                continue
            sources = dataS["sources"]
            children = dataS["children"]
            for child in children:
                if child is not None:
                    print("bug")
                    sys.exit("dataFlowInfer: child is not None")
            metaData = dataS["metaData"]

            targetFunc = metaData["targetFunc"]
            targetFuncType = metaData["targetFuncType"]
            name = targetFunc + "_" + targetFuncType 

            # if targetFunc == "unlock":
            #     print("now is the time")

            # if name not in dataFlowMap:
            #     dataFlowMap[ name ] = {"transferAmount": [], "transferPC": []}


            pc = None
            if "pc" in metaData:
                pc = metaData["pc"]
            elif len(sources) == 1 and isinstance(sources[0], str) and sources[0] ==  "msg.value":
                pc = -1
            else:
                sys.exit("dataFlowInfer: pc is not in metaData")
            if pc == None:
                sys.exit("dataFlowInfer: pc is None")


            # data type: 1. externalStaticCall    <= >=
            #            2. oracle     <= >=
            #            3. balance    
            #            4. selfbalance
            #            5. callvalue  <=
            #            6. mapping    <=
            #            7. storage    
            #            8. argument

            for source in sources:
                value, pc, type, dataType = readValuePCTypeFromSource(source, metaData, ABI)
                # if dataType == None:
                #     print(source)

                if value == None and pc == None:
                    continue

                if type is None:
                    print("buggy tx: {}".format(tx))
                    print(source)
                    sys.exit("dataFlowInfer: type is None")

                elif "toDebug" in type:
                    print("buggy tx: {}".format(tx))
                    print(source)
                    sys.exit("dataFlowInfer: type is toDebug")


                if dataType == "mapping":
                    hasMapping = True
                    if name not in mappingMap:
                        mappingMap[name] = {}

                    if pc not in mappingMap[name]:
                        mappingMap[name][pc] = [value]
                    else:
                        mappingMap[name][pc].append(value)
                elif dataType == "callvalue":
                    hasCallvalue = True
                    if name not in callvalueMap:
                        callvalueMap[name] = [value]
                    else:
                        callvalueMap[name].append(value)

                else:
                    if "int" in type:
                        hasDataFlow = True
                        if name not in dataFlowMap:
                            dataFlowMap[name] = {}
                        if pc not in dataFlowMap[name]:
                            dataFlowMap[name][pc] = (source, [value])
                        else:
                            dataFlowMap[name][pc][1].append(value)

                if type is None:
                    print("taint: ", source)
                    sys.exit("dataFlowInfer: type is None")

                    

        invariantMap = {
            "mapping": {},
            "callvalue": {},
            "dataFlow": {}
        # { 
        #  "mapping": 
        #          {
        #             "func+type": 
        #                           { 
        #                               pc: (smallest value, largest value)
        #                           }       
        #          }
        #  "callvalue":
        #          {
        #             "func+type": (smallest value, largest value)
        #          }
        # 
        #   "dataFlow": 
        #          { 
        #             "func+type": 
        #                           { 
        #                               pc: [source, (smallest value, largest value)]
        #                           }
        #          }
        # }
        }

        # print("hasMapping: {}".format(hasMapping))
        # print("hasCallvalue: {}".format(hasCallvalue))
        # print("hasDataFlow: {}".format(hasDataFlow))
    
        # stage 2: infer
        # mapping
        for func in mappingMap:
            if mappingMap[func] == {}:
                continue
            if func not in invariantMap["mapping"]:
                invariantMap["mapping"][func] = {}
            for pc in mappingMap[func]:
                minValue = min(mappingMap[func][pc])
                maxValue = max(mappingMap[func][pc])
                invariantMap["mapping"][func][pc] = (minValue, maxValue)

        # print("mapping map: ")
        # print(mappingMap)

        # callvalue
        for func in callvalueMap:
            if callvalueMap[func] == {}:
                continue
            minValue = min(callvalueMap[func])
            maxValue = max(callvalueMap[func])
            invariantMap["callvalue"][func] = (minValue, maxValue)

        # print("callvalue map: ")
        # print(callvalueMap)
        # dataFlow
        for func in dataFlowMap:
            if dataFlowMap[func] == {}:
                continue
            for pc in dataFlowMap[func]:
                source = dataFlowMap[func][pc][0]
                maxValue = max(dataFlowMap[func][pc][1])
                minValue = min(dataFlowMap[func][pc][1])
                if len(dataFlowMap[func][pc][1]) >= 2 and maxValue != minValue:
                    if func not in invariantMap["dataFlow"]:
                        invariantMap["dataFlow"][func] = {}
                    invariantMap["dataFlow"][func][pc] = [source, (minValue, maxValue)]

        print("==invariant map: ")
        import pprint
        pp = pprint.PrettyPrinter(indent=2)
        pp.pprint(invariantMap)

        print("Interpretation of the above invariant map: ")

        

        for key in invariantMap:
            print("For the invariant {}:".format(key))
            for func in invariantMap[key]:
                print("\tIt can be applied to function {}:".format(func))

                for key2 in invariantMap[key][func]:
                    print("\t\tFor Data Source read from pc = {}".format(key2))
                    print("\t\t\twith lowerbound = {}".format( invariantMap[key][func][key2][1][0] ))
                    print("\t\t\twith upperbound = {}".format( invariantMap[key][func][key2][1][1] ))
                    
