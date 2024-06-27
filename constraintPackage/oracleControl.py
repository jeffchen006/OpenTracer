import sys
import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from parserPackage.locator import *
from parserPackage.parser import proxyMap
from trackerPackage.dataSource import *
from utilsPackage.compressor import *
from parserPackage.decoder import *



import toml
settings = toml.load("settings.toml")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


Benchmark2Contract = {
    "RoninNetwork": "0x8407dc57739bcda7aa53ca6f12f82f9d51c2f21e", 
    "HarmonyBridge": "0xf9fb1c508ff49f78b60d3a96dea99fa5d7f3a8a6", 
    "HarmonyBridge_interface": "0x715cdda5e9ad30a0ced14940f9997ee611496de6", 
    "Nomad": "0x88a69b4e698a4b090df6cf5bd7b2d47325ad30a3", 
    "PolyNetwork": "0x250e76987d838a75310c34bf422ea9f1ac4cc906", 
    "bZx2": "0x85ca13d8496b2d22d6518faeb524911e096dd7e0", 
    "Warp": "0x6046c3Ab74e6cE761d218B9117d5c63200f4b406", 
    "Warp_interface": "0xba539b9a5c2d412cb10e5770435f362094f9541c",
    "CheeseBank_1": "0x5E181bDde2fA8af7265CB3124735E9a13779c021", 
    "CheeseBank_2": "0x4c2a8A820940003cfE4a16294B239C8C55F29695", 
    "CheeseBank_3": "0xA80e737Ded94E8D2483ec8d2E52892D9Eb94cF1f", 
    "InverseFi": "0x7Fcb7DAC61eE35b3D4a51117A7c58D53f0a8a670", 
    "CreamFi1_1": "0x3c710b981f5ef28da1807ce7ed3f2a28580e0754", 
    "CreamFi1_2": "0xd06527d5e56a3495252a528c4987003b712860ee", 
    "CreamFi2_1": "0x44fbebd2f576670a6c33f6fc0b00aa8c5753b322", 
    "CreamFi2_2": "0x797aab1ce7c01eb727ab980762ba88e7133d2157", 
    "CreamFi2_3": "0xe89a6d0509faf730bd707bf868d9a2a744a363c7", 
    "CreamFi2_4": "0x8c3b7a4320ba70f8239f83770c4015b5bc4e6f91", 
    "RariCapital1": "0xec260f5a7a729bb3d0c42d292de159b4cb1844a3", 
    "RariCapital2_1": "0x26267e41ceca7c8e0f143554af707336f27fa051", 
    "RariCapital2_2": "0xebe0d1cb6a0b8569929e062d67bfbc07608f0a47", 
    "RariCapital2_3": "0xe097783483d1b7527152ef8b150b99b9b2700c8d", 
    "RariCapital2_4": "0x8922c1147e141c055fddfc0ed5a119f3378c8ef8", 
    "XCarnival": "0x5417da20ac8157dd5c07230cfc2b226fdcfc5663", 
    "Harvest1_fUSDT": "0x053c80ea73dc6941f518a68e2fc52ac45bde7c9c", 
    "Harvest2_fUSDC": "0xf0358e8c3cd5fa238a29301d0bea3d63a17bedbe", 
    "ValueDeFi": "0xddd7df28b1fb668b77860b473af819b03db61101", 
    "Yearn1": "0x9c211bfa6dc329c5e757a223fb72f5481d676dc1", 
    "VisorFi": "0xc9f27a50f82571c1c8423a42970613b8dbda14ef", 
    "UmbrellaNetwork": "0xb3fb1d01b07a706736ca175f827e4f56021b85de", 
    "PickleFi": "0x6847259b2B3A4c17e7c43C54409810aF48bA5210", 
    "Eminence": "0x5ade7aE8660293F2ebfcEfaba91d141d72d221e8", 
    "Opyn": "0x951d51baefb72319d9fbe941e1615938d89abfe2", 
    "IndexFi": "0x5bd628141c62a901e0a83e630ce5fafa95bbdee4", 
    "RevestFi": "0xa81bd16aa6f6b25e66965a2f842e9c806c0aa11f", 
    "RevestFi_interface": "0x2320a28f52334d62622cc2eafa15de55f9987ed9", 
    "DODO": "0x2bbd66fc4898242bdbd2583bbe1d76e8b8f71445", 
    "Punk_1": "0x3BC6aA2D25313ad794b2D67f83f21D341cc3f5fb", 
    "Punk_2": "0x1F3b04c8c96A31C7920372FFa95371C80A4bfb0D", 
    "Punk_3": "0x929cb86046E421abF7e1e02dE7836742654D49d6", 
    "BeanstalkFarms": "0x3a70dfa7d2262988064a2d051dd47521e43c9bdd", 
}


benchmark2suspiciousFuncs = {
    "bZx2": ["borrowTokenFromDeposit"],
    "CheeseBank_1": ["borrow"], 
    "CheeseBank_2": ["borrow"],
    "CheeseBank_3": ["borrow"],
    "Warp_interface": ["borrowSC", "getBorrowLimit"],
    "InverseFi": ["borrow"], 
    "CreamFi2_1": ["borrow"],
    "CreamFi2_2": ["borrow"],
    "CreamFi2_3": ["borrow"],
    "CreamFi2_4": ["borrow"],
    "Harvest1_fUSDT": ["deposit", "withdraw"],
    "Harvest2_fUSDC": ["deposit", "withdraw"],
    "ValueDeFi": ["depositFor", "withdrawFor"],
}


benchmark2Oracle = {
    "bZx2": [
        ("0x38a5cf926a0b9b5fe3a265c57d184ad8c0af05b6", "getExpectedRate", ["0x57ab1ec28d129707052df4df418d58a2d46d5f51", "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", 10000000000000000, False]),
        ("0x38a5cf926a0b9b5fe3a265c57d184ad8c0af05b6", "getExpectedRate", ["0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", "0x57ab1ec28d129707052df4df418d58a2d46d5f51", 10000000000000000, False]),
    ],
    "Warp_interface": [
        ("0x4a224cd0517f08b26608a2f73bf390b01a6618c8", "getUnderlyingPrice", ["0xa478c2975ab1ea89e8196811f51a7b7ade33eb11"]),
        ("0x4a224cd0517f08b26608a2f73bf390b01a6618c8", "getUnderlyingPrice", ["0xbb2b8038a1640196fbe3e38816f3e67cba72d940"]),
        ("0x4a224cd0517f08b26608a2f73bf390b01a6618c8", "getUnderlyingPrice", ["0x0d4a11d5eeaac28ec3f61d100daf4d40471f1852"]),
        ("0x4a224cd0517f08b26608a2f73bf390b01a6618c8", "getUnderlyingPrice", ["0xb4e16d0168e52d35cacd2c6185b44281ec28c9dc"]),
    ], 
    "CheeseBank_1": [
        ("0x833e440332caa07597a5116fbb6163f0e15f743d", "getUnderlyingPrice", ["0xa80e737ded94e8d2483ec8d2e52892d9eb94cf1f"]),
        ("0x833e440332caa07597a5116fbb6163f0e15f743d", "getUnderlyingPrice", ["0x7e4956688367fb28de3c0a62193f59b1526a00e7"]),
        ("0x833e440332caa07597a5116fbb6163f0e15f743d", "getUnderlyingPrice", ["0x5e181bdde2fa8af7265cb3124735e9a13779c021"]),
        ("0x833e440332caa07597a5116fbb6163f0e15f743d", "getUnderlyingPrice", ["0x4c2a8a820940003cfe4a16294b239c8c55f29695"]),

        ("0x9e30a82e98c17650b4e4ce6c45a9779349073b35", "getUnderlyingPrice", ["0x5e181bdde2fa8af7265cb3124735e9a13779c021"]),
        ("0x9e30a82e98c17650b4e4ce6c45a9779349073b35", "getUnderlyingPrice", ["0x7e4956688367fb28de3c0a62193f59b1526a00e7"]),
        ("0x9e30a82e98c17650b4e4ce6c45a9779349073b35", "getUnderlyingPrice", ["0xa80e737ded94e8d2483ec8d2e52892d9eb94cf1f"]),

    ],
    "CheeseBank_2": [
        ("0x833e440332caa07597a5116fbb6163f0e15f743d", "getUnderlyingPrice", ["0xa80e737ded94e8d2483ec8d2e52892d9eb94cf1f"]),
        ("0x833e440332caa07597a5116fbb6163f0e15f743d", "getUnderlyingPrice", ["0x7e4956688367fb28de3c0a62193f59b1526a00e7"]),
        ("0x833e440332caa07597a5116fbb6163f0e15f743d", "getUnderlyingPrice", ["0x5e181bdde2fa8af7265cb3124735e9a13779c021"]),
        ("0x833e440332caa07597a5116fbb6163f0e15f743d", "getUnderlyingPrice", ["0x4c2a8a820940003cfe4a16294b239c8c55f29695"]),

        ("0x9e30a82e98c17650b4e4ce6c45a9779349073b35", "getUnderlyingPrice", ["0x5e181bdde2fa8af7265cb3124735e9a13779c021"]),
        ("0x9e30a82e98c17650b4e4ce6c45a9779349073b35", "getUnderlyingPrice", ["0x7e4956688367fb28de3c0a62193f59b1526a00e7"]),
        ("0x9e30a82e98c17650b4e4ce6c45a9779349073b35", "getUnderlyingPrice", ["0xa80e737ded94e8d2483ec8d2e52892d9eb94cf1f"]),
    ],
    "CheeseBank_3": [
        ("0x833e440332caa07597a5116fbb6163f0e15f743d", "getUnderlyingPrice", ["0xa80e737ded94e8d2483ec8d2e52892d9eb94cf1f"]),
        ("0x833e440332caa07597a5116fbb6163f0e15f743d", "getUnderlyingPrice", ["0x7e4956688367fb28de3c0a62193f59b1526a00e7"]),
        ("0x833e440332caa07597a5116fbb6163f0e15f743d", "getUnderlyingPrice", ["0x5e181bdde2fa8af7265cb3124735e9a13779c021"]),
        ("0x833e440332caa07597a5116fbb6163f0e15f743d", "getUnderlyingPrice", ["0x4c2a8a820940003cfe4a16294b239c8c55f29695"]),

        ("0x9e30a82e98c17650b4e4ce6c45a9779349073b35", "getUnderlyingPrice", ["0x5e181bdde2fa8af7265cb3124735e9a13779c021"]),
        ("0x9e30a82e98c17650b4e4ce6c45a9779349073b35", "getUnderlyingPrice", ["0x7e4956688367fb28de3c0a62193f59b1526a00e7"]),
        ("0x9e30a82e98c17650b4e4ce6c45a9779349073b35", "getUnderlyingPrice", ["0xa80e737ded94e8d2483ec8d2e52892d9eb94cf1f"]),
    ],
    "InverseFi": [
        ("0xe8929afd47064efd36a7fb51da3f8c5eb40c4cb4", "getUnderlyingPrice", ["0x7fcb7dac61ee35b3d4a51117a7c58d53f0a8a670"]),
        ("0xe8929afd47064efd36a7fb51da3f8c5eb40c4cb4", "getUnderlyingPrice", ["0x1429a930ec3bcf5aa32ef298ccc5ab09836ef587"]),
        ("0xe8929afd47064efd36a7fb51da3f8c5eb40c4cb4", "getUnderlyingPrice", ["0x7fcb7dac61ee35b3d4a51117a7c58d53f0a8a670"]),
    ],
    "CreamFi2_1": [
        ("0x338eee1f7b89ce6272f302bdc4b952c13b221f1d", "getUnderlyingPrice", ["0xd06527d5e56a3495252a528c4987003b712860ee"]),
        ("0x338eee1f7b89ce6272f302bdc4b952c13b221f1d", "getUnderlyingPrice", ["0x4baa77013ccd6705ab0522853cb0e9d453579dd4"]),
        ("0x338eee1f7b89ce6272f302bdc4b952c13b221f1d", "getUnderlyingPrice", ["0xd06527d5e56a3495252a528c4987003b712860ee"]),
    ],
    "CreamFi2_2": [
        ("0x338eee1f7b89ce6272f302bdc4b952c13b221f1d", "getUnderlyingPrice", ["0xd06527d5e56a3495252a528c4987003b712860ee"]),
        ("0x338eee1f7b89ce6272f302bdc4b952c13b221f1d", "getUnderlyingPrice", ["0x4baa77013ccd6705ab0522853cb0e9d453579dd4"]),
        ("0x338eee1f7b89ce6272f302bdc4b952c13b221f1d", "getUnderlyingPrice", ["0xd06527d5e56a3495252a528c4987003b712860ee"]),
    ],
    "CreamFi2_3": [
        ("0x338eee1f7b89ce6272f302bdc4b952c13b221f1d", "getUnderlyingPrice", ["0xd06527d5e56a3495252a528c4987003b712860ee"]),
        ("0x338eee1f7b89ce6272f302bdc4b952c13b221f1d", "getUnderlyingPrice", ["0x4baa77013ccd6705ab0522853cb0e9d453579dd4"]),
        ("0x338eee1f7b89ce6272f302bdc4b952c13b221f1d", "getUnderlyingPrice", ["0xd06527d5e56a3495252a528c4987003b712860ee"]),
    ],
    "CreamFi2_4": [
        ("0x338eee1f7b89ce6272f302bdc4b952c13b221f1d", "getUnderlyingPrice", ["0xd06527d5e56a3495252a528c4987003b712860ee"]),
        ("0x338eee1f7b89ce6272f302bdc4b952c13b221f1d", "getUnderlyingPrice", ["0x4baa77013ccd6705ab0522853cb0e9d453579dd4"]),
        ("0x338eee1f7b89ce6272f302bdc4b952c13b221f1d", "getUnderlyingPrice", ["0xd06527d5e56a3495252a528c4987003b712860ee"]),
    ],
    "Harvest1_fUSDT": [
        ("0x45f783cce6b7ff23b2ab2d70e416cdb7d6055f51", "balances", [0]),
        ("0x45f783cce6b7ff23b2ab2d70e416cdb7d6055f51", "balances", [1]),
        ("0x45f783cce6b7ff23b2ab2d70e416cdb7d6055f51", "balances", [2]),
        ("0x45f783cce6b7ff23b2ab2d70e416cdb7d6055f51", "balances", [3]),
    ],
    "Harvest2_fUSDC": [
        ("0x45f783cce6b7ff23b2ab2d70e416cdb7d6055f51", "balances", [0]),
        ("0x45f783cce6b7ff23b2ab2d70e416cdb7d6055f51", "balances", [1]),
        ("0x45f783cce6b7ff23b2ab2d70e416cdb7d6055f51", "balances", [2]),
        ("0x45f783cce6b7ff23b2ab2d70e416cdb7d6055f51", "balances", [3]),
    ],
    "ValueDeFi": [
        ("0xba5d28f4ecee5586d616024c74e4d791e01adee7", "balanceOf", ["0x6c3f90f043a72fa612cbac8115ee7e52bde6e490", True]),
        ("0xba5d28f4ecee5586d616024c74e4d791e01adee7", "balanceOf", ["0x6c3f90f043a72fa612cbac8115ee7e52bde6e490", False])

    ]

}



replaceMap = {
    "0x9e30a82e98c17650b4e4ce6c45a9779349073b35+getUnderlyingPrice+['0xa80e737ded94e8d2483ec8d2e52892d9eb94cf1f']": 
        "0x833e440332caa07597a5116fbb6163f0e15f743d+getUnderlyingPrice+['0xa80e737ded94e8d2483ec8d2e52892d9eb94cf1f']",
    "0x9e30a82e98c17650b4e4ce6c45a9779349073b35+getUnderlyingPrice+['0x7e4956688367fb28de3c0a62193f59b1526a00e7']": 
        "0x833e440332caa07597a5116fbb6163f0e15f743d+getUnderlyingPrice+['0x7e4956688367fb28de3c0a62193f59b1526a00e7']",
    "0x9e30a82e98c17650b4e4ce6c45a9779349073b35+getUnderlyingPrice+['0x5e181bdde2fa8af7265cb3124735e9a13779c021']": 
        "0x833e440332caa07597a5116fbb6163f0e15f743d+getUnderlyingPrice+['0x5e181bdde2fa8af7265cb3124735e9a13779c021']",
}

replaceBackMap = {
    "0x833e440332caa07597a5116fbb6163f0e15f743d+getUnderlyingPrice+['0xa80e737ded94e8d2483ec8d2e52892d9eb94cf1f']":
        "0x9e30a82e98c17650b4e4ce6c45a9779349073b35+getUnderlyingPrice+['0xa80e737ded94e8d2483ec8d2e52892d9eb94cf1f']",
    "0x833e440332caa07597a5116fbb6163f0e15f743d+getUnderlyingPrice+['0x7e4956688367fb28de3c0a62193f59b1526a00e7']":
        "0x9e30a82e98c17650b4e4ce6c45a9779349073b35+getUnderlyingPrice+['0x7e4956688367fb28de3c0a62193f59b1526a00e7']",
    "0x833e440332caa07597a5116fbb6163f0e15f743d+getUnderlyingPrice+['0x5e181bdde2fa8af7265cb3124735e9a13779c021']":
        "0x9e30a82e98c17650b4e4ce6c45a9779349073b35+getUnderlyingPrice+['0x5e181bdde2fa8af7265cb3124735e9a13779c021']"
}

    
    


# check 2 invariants
# 1. upper bounds and lower bounds for oracle
# 2. oracle deviations  namely, x < (new oracle - old oracle) / new oracle < y

def inferOracleRange(benchmarks):
    crawlQuickNode = CrawlQuickNode()
    crawlEtherscan = CrawlEtherscan()
    isStart = False

    f = FilterTx()
    for benchmark in benchmarks:
        contract = Benchmark2Contract[benchmark]
        category = f.contract2Category(contract)
        txList, _ = categoryContract2Paths(category, contract)
        exploitTx = f.contract2ExploitTx(contract)

        if not os.path.exists(SCRIPT_DIR + "/../cache/" + contract + "_SplitedTraceTree"):
            print("does not exist: " + benchmark, contract)
            continue
        else:
            print("====== benchmark {}: ".format(benchmark))



        # stage 1: training
        oracleMap = {
            # oracle-value: (
            #                   [value0, value1, value2, ...], 
            #                   [tx0, tx1, tx2, ...]
            # ), 
        }

        oracleDeviation = {
            # oracle-value: (
            #                   [ratio1, ratio0, ratio3, ...],
            #                   [tx0, tx1, tx2, ...]
            # )
        }

        path = SCRIPT_DIR + "/cache/trainingSet/{}.pickle".format(benchmark)
        # temp = readDataSource(path)
        trainTxList = readDataSource(path)[0]
        path = SCRIPT_DIR + "/cache/testingSet/{}.pickle".format(benchmark)
        # temp =  readDataSource(path)
        testingTxList = readDataSource(path)[0]

        counter = -1
        funcNames = []
        for tx in txList:
            counter += 1
            tx = tx.lower()

            # precheck
            splitedTraceTree = readSplitedTraceTree(SCRIPT_DIR, contract, tx)
            if splitedTraceTree == [] or splitedTraceTree == [[]]:
                continue

            if tx not in trainTxList:
                break
            
            if len(splitedTraceTree) != 1:
                sys.exit("oracleControl: len(splitedTraceTree) != 1")

            totalOracleValues = parseTraceTree(benchmark, tx)
            # print(totalOracleValues)
            for key in totalOracleValues:
                # if key in replaceMap:
                #     new_key = replaceMap[key]
                #     totalOracleValues[new_key] = totalOracleValues[key]
                #     del totalOracleValues[key]
                #     key = new_key

                if key not in oracleMap:
                    oracleMap[key] = ([], [])
                    oracleDeviation[key] = ([], [])

                # if key == "0x9e30a82e98c17650b4e4ce6c45a9779349073b35+getUnderlyingPrice+['0x7e4956688367fb28de3c0a62193f59b1526a00e7']":
                #     print("now is the time")
                
                for typeValuePair in totalOracleValues[key]:
                    # print(typeValuePair)
                    types = typeValuePair[0]
                    if len(types) != 1:
                        sys.exit("Warning: oracle type is not uint256")
                    if types[0] != "uint256":
                        sys.exit("Warning: oracle type is not uint256")
                    values = typeValuePair[1]
                    if len(values) != 1:
                        sys.exit("Warning: oracle value is not 1")
                    
                    value = values[0]
                    oracleMap[key][0].append(value)
                    oracleMap[key][1].append(tx)

                    if len(oracleDeviation[key][0]) == 0:
                        oracleDeviation[key][0].append(0)
                        oracleDeviation[key][1].append(tx)
                    else:
                        oldOracle = oracleMap[key][0][-2]
                        newOracle = oracleMap[key][0][-1]
                        ratio = (newOracle - oldOracle) / newOracle
                        
                        oracleDeviation[key][0].append(ratio)
                        oracleDeviation[key][1].append(tx)

        
        # print(oracleMap)


        # stage 2: infer
        # invariantMap = {
        #     # oracle-value: (minValue, maxValue)
        #     # oracle-value-ratio: (minValue, maxValue)
        # }

        invariantMap = {}
        for oracle in oracleMap:
            maxValue = max(oracleMap[oracle][0])
            minValue = min(oracleMap[oracle][0])
            maxRatio = max(oracleDeviation[oracle][0])
            minRatio = min(oracleDeviation[oracle][0])

            if len( set(oracleMap[oracle][1]) ) >= 2:
                invariantMap[oracle] = (minValue, maxValue)
                invariantMap[oracle + "-ratio"] = (minRatio, maxRatio)

        print("==data map:")
        for oracle in oracleMap:
            print(oracle)
            print(oracleMap[oracle][0])
            # print(oracleMap[oracle][1])

        print("==invariant map: ")
        import pprint
        pp = pprint.PrettyPrinter(indent=2)
        pp.pprint(invariantMap)

        # for invariant in invariantMap:
        #     print(invariant)
        #     print("\t", invariantMap[invariant])

        # stage 3: validation
        FPMap = {
            "oracle": [],
            "oracle-ratio": []
        }

        oldOracleValues = {}
        for oracle in invariantMap:
            if "-ratio" not in oracle:
                oldOracleValues[oracle] = oracleMap[oracle][0][-1]

        for tx in txList[counter:]:
            tx = tx.lower()
            # precheck 
            splitedTraceTree = readSplitedTraceTree(SCRIPT_DIR, contract, tx)
            if splitedTraceTree == [] or splitedTraceTree == [[]]:
                continue            

            if len(splitedTraceTree) != 1:
                sys.exit("oracleControl: len(splitedTraceTree) != 1")

            
            if tx == exploitTx.lower():
                isFiltered = False
                totalOracleValues = parseTraceTree(benchmark, tx)
                for key in totalOracleValues:
                    key_original = key


                    if key in replaceMap:
                        key = replaceMap[key]

                    if key in invariantMap:
                        minValue, maxValue = invariantMap[key]
                        for typeValuePair in totalOracleValues[key_original]:
                            types = typeValuePair[0]
                            if len(types) != 1:
                                sys.exit("Warning: oracle type is not uint256")
                            if types[0] != "uint256":
                                sys.exit("Warning: oracle type is not uint256")
                            values = typeValuePair[1]
                            if len(values) != 1:
                                sys.exit("Warning: oracle value is not 1")
                            value = values[0]
                            if value < minValue or value > maxValue:
                                isFiltered = True
                                print("Successfully stops the exploit using oracle range")
                                if value < minValue:
                                    print("{} < {}".format(value, minValue))
                                elif value > maxValue:
                                    print("{} > {}".format(value, maxValue))
                            else:
                                print("The oracle is under tolerance: {} <= {} <= {}".format(minValue, value, maxValue))
                            
                            ratio = (value - oldOracleValues[key]) / value
                            oldOracleValues[key] = value
                            if ratio < invariantMap[key + "-ratio"][0] or ratio > invariantMap[key + "-ratio"][1]:
                                isFiltered = True
                                print("Successfully stops the exploit using oracle deviation")
                                if ratio < invariantMap[key + "-ratio"][0]:
                                    print("{} < {}".format(ratio, invariantMap[key + "-ratio"][0]))
                                elif ratio > invariantMap[key + "-ratio"][1]:
                                    print("{} > {}".format(ratio, invariantMap[key + "-ratio"][1]))
                                
                    else:
                        print("Warning: oracle {} is not in invariantMap".format(key_original))
                        for typeValuePair in totalOracleValues[key_original]:
                            values = typeValuePair[1]
                            value = values[0]
                            print("oracle value: {}".format(value))

                print("exploitTx: ", exploitTx)
                print("FPMap: ", end="")
                printFPMap(invariantMap, FPMap, benchmark)
                break

                                

            totalOracleValues = parseTraceTree(benchmark, tx)
            for key in totalOracleValues:
                key_original = key
                if key in replaceMap:
                    key = replaceMap[key]

                if key in invariantMap:
                    minValue, maxValue = invariantMap[key]
                    for typeValuePair in totalOracleValues[key_original]:
                        types = typeValuePair[0]
                        if len(types) != 1:
                            sys.exit("Warning: oracle type is not uint256")
                        if types[0] != "uint256":
                            sys.exit("Warning: oracle type is not uint256")
                        values = typeValuePair[1]
                        if len(values) != 1:
                            sys.exit("Warning: oracle value is not 1")
                        value = values[0]
                        if value < minValue or value > maxValue:
                            if tx not in FPMap["oracle"]:
                                if value < minValue:
                                    print("{} < {}".format(value, minValue))
                                elif value > maxValue:
                                    print("{} > {}".format(value, maxValue))
                                FPMap["oracle"].append(tx)
                        
                        # if key in replaceBackMap:
                        #     key = replaceBackMap[key]
                        ratio = (value - oldOracleValues[key]) / value
                        oldOracleValues[key] = value
                        if ratio < invariantMap[key + "-ratio"][0] or ratio > invariantMap[key + "-ratio"][1]:
                            if tx not in FPMap["oracle-ratio"]:
                                if ratio < invariantMap[key + "-ratio"][0]:
                                    print("{} < {}".format(ratio, invariantMap[key + "-ratio"][0]))
                                elif ratio > invariantMap[key + "-ratio"][1]:
                                    print("{} > {}".format(ratio, invariantMap[key + "-ratio"][1]))
                                FPMap["oracle-ratio"].append(tx)
                        








                                


class searcher:
    def __init__(self) -> None:
        self.oracleValues = {}

    def reset(self):
        self.oracleValues = {}

    def searchForOracle(self, traceTree, oracles):
        
        # if "name" in traceTree.info and traceTree.info["name"] == "getPricePerFullShare":
        #     print("now is the time")
    
        for oracleAddr, oracleFuncName, oracleArgs in oracles:
            if "addr" in traceTree.info and traceTree.info["addr"].lower() == oracleAddr.lower():
                if "name" in traceTree.info and traceTree.info["name"] == oracleFuncName:
                    if "Decoded calldata" in traceTree.info:
                        isMatch = len(traceTree.info["Decoded calldata"]) == len(oracleArgs)
                        if isMatch:
                            for ii in range(len(traceTree.info["Decoded calldata"])):
                                if traceTree.info["Decoded calldata"][ii] != oracleArgs[ii]:
                                    isMatch = False
                                    break
                        if isMatch:
                            returnValue = (traceTree.info["Decoded returnvalue types"], traceTree.info["Decoded returnvalue"])
                            oracleName = str(oracleAddr) + "+" + str(oracleFuncName) + "+" + str(oracleArgs)
                            if oracleName not in self.oracleValues:
                                self.oracleValues[oracleName] = [returnValue]
                            else:
                                self.oracleValues[oracleName].append(returnValue)
            
        for child in traceTree.internalCalls:
            self.searchForOracle(child, oracles)
                    

            


def parseTraceTree(benchmark, tx):
    contract = Benchmark2Contract[benchmark]
    oracles = benchmark2Oracle[benchmark]
    suspiciousFuncs = benchmark2suspiciousFuncs[benchmark]
    splitedTraceTree = readSplitedTraceTree(SCRIPT_DIR, contract, tx)
    traceTrees = splitedTraceTree[0]
    totalOracleValues = {}

    s = searcher()
    for traceTree in traceTrees:
        if "name" not in traceTree.info:
            print(tx)
        funcName = traceTree.info["name"]
        isSuspiciousFunc = funcName in suspiciousFuncs
        s.reset()
        s.searchForOracle(traceTree, oracles)
        oracleValues = s.oracleValues
        for key in oracleValues:
            
            if key not in totalOracleValues:
                if key in replaceMap:
                    new_key = replaceMap[key]
                    totalOracleValues[new_key] = oracleValues[key]
                else:
                    totalOracleValues[key] = oracleValues[key]
            else:
                if key in replaceMap:
                    new_key = replaceMap[key]
                    totalOracleValues[new_key] += oracleValues[key]
                else:
                    totalOracleValues[key] += oracleValues[key]
        
        # if isSuspiciousFunc and len(totalOracleValues.keys()) == 0:
        #     print("Warning: suspicious function {} does not call oracle".format(funcName))
        #     print("tx: {}".format(tx))
            
    return totalOracleValues


def main():
    f = FilterTx()

    benchmarks = ["bZx2", "Warp_interface", "CheeseBank_1", "CheeseBank_2", "CheeseBank_3", "InverseFi", \
                      "CreamFi2_1", "CreamFi2_2", "CreamFi2_3", "CreamFi2_4", "Harvest1_fUSDT", "Harvest2_fUSDC", \
                       "ValueDeFi"]

    # benchmarks = {"Harvest1_fUSDT", "Harvest2_fUSDC"}
    
    inferOracleRange(benchmarks)

    # inferOracleRange()

    # for benchmark in ["bZx2", "Warp_interface", "CheeseBank_1", "CheeseBank_2", "CheeseBank_3", "InverseFi", \
    #                   "CreamFi2_1", "CreamFi2_2", "CreamFi2_3", "CreamFi2_4", "Harvest1_fUSDT", "Harvest2_fUSDC", \
    #                    "ValueDeFi"]:
    #     print("====== benchmark {}: ".format(benchmark))
    #     contract = Benchmark2Contract[benchmark]
    #     exploitTx = f.contract2ExploitTx(contract)
    #     print(exploitTx)
    #     parseTraceTree(benchmark, exploitTx)




if __name__ == "__main__":

    main()

    # # bZx2
    # benchmark = "bZx2"
    # tx = "0x9bc9655cf18360866ea5e8272424cebdd8ce7ea010ef7cf7d3aafe2baad57343"
    # parseTraceTree(benchmark, tx)


# not ok:
# bZx2
# Warp
# CreamFi2_1
# CreamFi2_2
# CreamFi2_3
# CreamFi2_4



# ok: 
# CheeseBank_1
# CheeseBank_2
# CheeseBank_3
# InverseFi
# ValueDeFi
# Harvest1_fUSDT
# Harvest2_fUSDC
