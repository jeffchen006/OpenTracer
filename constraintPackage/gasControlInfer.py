import sys
import os
from parserPackage.locator import *
from parserPackage.parser import proxyMap
import copy
from trackerPackage.dataSource import *
from crawlPackage.crawlEtherscan import CrawlEtherscan
from utilsPackage.compressor import *
from staticAnalyzer.analyzer import Analyzer


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))
import toml



def inferGasControl(accesslistTable):    
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
        gasControlMap = {}
        # { "func": 
        #             {
        #                 gasStart: [gasStart1, gasStart2, ...], 
        #                 gasEnd: [gasEnd1, gasEnd2, ...],
        # }

        counter = -1
        analyzer = Analyzer()
        for tx, funcCallList in accessList:
            counter += 1
            if len(funcCallList) != 1:
                print(funcCallList)
                sys.exit("gas control infer: not one function call in a transaction")

            for funcCall in funcCallList[0]:
                name = ""
                if "name" in funcCall:
                    if funcCall["name"] == "fallback" and funcCall["Selector"] != "0x":
                        # get real funcName from selector and contract
                        funcSigMap = analyzer.contract2funcSigMap(contract)
                        funcCall["name"] = funcSigMap[funcCall["Selector"].lower()][0]

                    name += funcCall["name"]
                    if funcCall["name"] not in nonReadOnlyFunctions:
                        continue

                if "Selector" in funcCall:
                    name += funcCall["Selector"]

                if "gas" not in funcCall:
                    print("no gas")
                    print(tx)
                    continue
                gasStart = funcCall["gas"]
                if "gasEnd" not in funcCall:
                    print("no gasEnd")
                    print(tx)
                    continue
                gasEnd = funcCall["gasEnd"]

                if name not in gasControlMap:
                    gasControlMap[name] = {
                        "gasStart": [gasStart], 
                        "gasEnd": [gasEnd],
                    } 
                else:
                    gasControlMap[name]["gasStart"].append(gasStart)
                    gasControlMap[name]["gasEnd"].append(gasEnd)



        # stage 2: infer
        invariantMap = {}
        # { "func":
        #             { 
        #                   "require(gasStart <= constant)": b, 
        #                   "require(gasStart - gasEnd <= constant)": b,
        #               }
        # }
        for func in gasControlMap:
            invariantMap[func] = {}
            # invariant 1: require gasStart < constant
            maxValue = max(gasControlMap[func]["gasStart"])
            minValue = min(gasControlMap[func]["gasStart"])

            if len(gasControlMap[func]["gasStart"]) >= 2 and maxValue != minValue:
                invariantMap[func]["require(gasStart <= constant)"] = maxValue
                
            # invariant 2: require gasStart - gasEnd < constant
            # and invariant 3: require gasStart - gasEnd > constant
            result = [a - b for a, b in zip(gasControlMap[func]["gasStart"], gasControlMap[func]["gasEnd"])]

            maxGapValue = max( result )
            minGapValue = min( result )

            if len(gasControlMap[func]["gasEnd"]) >= 2 and maxGapValue != minGapValue:
                invariantMap[func]["require(gasStart - gasEnd <= constant)"] = maxGapValue


        isHavingGasConsumed = False
        print("==invariant map: ")
        import pprint
        pp = pprint.PrettyPrinter(indent=2)
        pp.pprint(invariantMap)
        
        print("Interpretation of the above invariant map: ")
        for func in invariantMap:
            if "require(gasStart <= constant)" in invariantMap[func]:
                print("\tfunction {} requires gasStart <= {}".format(func, invariantMap[func]["require(gasStart <= constant)"]))
            if "require(gasStart - gasEnd <= constant)" in invariantMap[func]:
                print("\tfunction {} requires gasStart - gasEnd <= {}".format(func, invariantMap[func]["require(gasStart - gasEnd <= constant)"]))
