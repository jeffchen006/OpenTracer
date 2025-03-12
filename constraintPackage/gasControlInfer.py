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
proportion = settings["experiment"]["trainingSetRatio"] # how much transactions used as traning set



        




# check 3 invariants:
# 1. msg.sender != tx.origin
# 2. is msg.sender/tx.origin owner?
# 3. is msg.sender/tx.origin manager?

def printFPMap(invariantMap, FPMap, benchmarkName, txCount):
    generatedInvariants = []
    for func in invariantMap:
        for invariant in invariantMap[func]:
            if invariant not in generatedInvariants:
                generatedInvariants.append(invariant)
    newFPMap = {}
    for invariant in generatedInvariants:
        newFPMap[invariant] = "{}/{}".format( len(FPMap[invariant]), int(txCount * (1 - proportion) - 1) )
    # print(newFPMap)

    invariants = ['require(gasStart <= constant)', 'require(gasStart - gasEnd <= constant)']

    print(invariants)
    for invariant in invariants:
        if invariant in newFPMap:
            print("{}\t".format(len(FPMap[invariant]) ), end ="" )
        else:
            print("N/A\t", end = "")
    print("")

    for invariant in invariants:
        if invariant in FPMap:
            print("5 sampled FPs for {}".format(invariant))
            sampledFPs = sample_five_elements(FPMap[invariant])
            for fp in sampledFPs:
                print(fp)
        




def inferGasControl(accesslistTable, txCount):    
    crawlQuickNode = CrawlQuickNode()
    crawlEtherscan = CrawlEtherscan()

    for benchmarkName, contract, accessList, exploitTx in accesslistTable:
        print("====== benchmark {}: ".format(benchmarkName))
        if benchmarkName == "VisorFi":
            exploitTx = "0x69272d8c84d67d1da2f6425b339192fa472898dce936f24818fda415c1c1ff3f"

        originalContract = contract

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

        txList = []
        txList3 = []
        for tx, funcCallList in accessList:
            counter += 1
            if tx not in txList:
                txList.append(tx)

            if len(funcCallList) != 1:
                print(funcCallList)
                sys.exit("gas control infer: not one function call in a transaction")

            for funcCall in funcCallList[0]:


                # build name
                name = ""
                if "name" in funcCall:
                    if funcCall["name"] == "fallback" or funcCall["name"] == "constructor":
                        if "Selector" in funcCall:
                            pass
                        else:
                            name += funcCall["name"]
                    else:
                        name += funcCall["name"]
                        if funcCall["name"] not in nonReadOnlyFunctions:
                            continue
                if "Selector" in funcCall:
                    name += funcCall["Selector"]

                if tx not in txList3:
                    txList3.append(tx)


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

            cutoff = txCount * proportion
            now = len(txList)
            if len(txList) > txCount * proportion:
                counter += 1
                break

        # # store training set for each benchmark
        # path = SCRIPT_DIR + "/cache/trainingSet/{}.pickle".format(benchmarkName)
        # writeList(path, txList)



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
        
        for func in invariantMap:
            if "require(gasStart - gasEnd <= constant)" in invariantMap[func]:
                isHavingGasConsumed = True
                break


        positivePath = SCRIPT_DIR + "/cache/positives/gasConsumed/{}.txt".format(benchmarkName)

        
        # stage 3: validation
        FPMap = {
            "require(gasStart <= constant)": [],
            "require(gasStart - gasEnd <= constant)": [],
        }


        txList2 = []
        isFiltered = False
        isFilteredByGasConsumed = False

        gasGCOverHeadMap = {}
        
        for ii, (tx, funcCallList) in enumerate(accessList[counter:]):
            currentIndex = ii + counter
            if tx not in txList2:
                txList2.append(tx)

            if tx == exploitTx:
                #  # store testing set for each benchmark
                # path = SCRIPT_DIR + "/cache/testingSet/{}.pickle".format(benchmarkName)
                # writeList(path, txList2)


                for funcCall in funcCallList[0]:
                    # build name
                    name = ""
                    if "name" in funcCall:
                        if funcCall["name"] == "fallback" or funcCall["name"] == "constructor":
                            if "Selector" in funcCall:
                                pass
                            else:
                                name += funcCall["name"]
                        else:
                            name += funcCall["name"]
                            if funcCall["name"] not in nonReadOnlyFunctions:
                                continue
                    if "Selector" in funcCall:
                        name += funcCall["Selector"]
                        
                    
                    if name not in invariantMap:
                        continue
                    
                    if "gas" not in funcCall:
                        print("no gas")
                        print(tx)
                        continue
                    
                    if "gasEnd" not in funcCall:
                        print("no gasEnd")
                        print(tx)
                        continue

                    gasStart = funcCall["gas"]
                    gasEnd = funcCall["gasEnd"]
                    if "require(gasStart <= constant)" in invariantMap[name] and \
                        gasStart > invariantMap[name]["require(gasStart <= constant)"]:
                        isFiltered = True
                        print("Successfully stops the exploit using require(gasStart <= constant)")


                    if "require(gasStart - gasEnd <= constant)" in invariantMap[name]:     
                        print("For the func {}, gas {} - {} = {}".format(name, gasStart, gasEnd, gasStart - gasEnd))

                        if gasStart - gasEnd > invariantMap[name]["require(gasStart - gasEnd <= constant)"]:
                            isFiltered = True
                            isFilteredByGasConsumed = True
                            print("Successfully stops the exploit using require(gasStart - gasEnd <= constant)")
                            print("{} - {} = {} > {}".format(gasStart, gasEnd, gasStart - gasEnd, invariantMap[name]["require(gasStart - gasEnd <= constant)"]) )
                            

                if len(accessList) == currentIndex + 1 or accessList[currentIndex + 1][0] != exploitTx:
                    print("exploitTx: ", exploitTx)
                    print("FPMap: ", end="")
                    printFPMap(invariantMap, FPMap, benchmarkName, txCount)
                    if exploitTx not in txList3:
                        txList3.append(exploitTx)

                    print("len(txList3): ", len(txList3))

                    newList = copy.deepcopy(FPMap["require(gasStart - gasEnd <= constant)"])
                    newList.insert(0, 'exploitTx: {}'.format(exploitTx))

                    if isFilteredByGasConsumed:
                        newList.append(exploitTx)


                    # if benchmarkName in gasGCOverhead:
                    #     gasOverheadPath = SCRIPT_DIR + "/cache/gas/{}_GC.json".format(benchmarkName)
                    #     writeJson(gasOverheadPath, gasGCOverHeadMap)
                    break

            else: 
                for funcCall in funcCallList[0]:
                    # build name
                    name = ""
                    if "name" in funcCall:
                        if funcCall["name"] == "fallback" or funcCall["name"] == "constructor":
                            if "Selector" in funcCall:
                                pass
                            else:
                                name += funcCall["name"]
                        else:
                            name += funcCall["name"]
                            if funcCall["name"] not in nonReadOnlyFunctions:
                                continue
                    if "Selector" in funcCall:
                        name += funcCall["Selector"]



                    
                    if name not in invariantMap:
                        continue
                        
                    if tx not in txList3:
                        txList3.append(tx)

                    if "gas" not in funcCall:
                        print("no gas")
                        print(tx)
                        continue
                    
                    if "gasEnd" not in funcCall:
                        print("no gasEnd")
                        print(tx)
                        continue

                    if "require(gasStart <= constant)" in invariantMap[name] and \
                        funcCall["gas"] > invariantMap[name]["require(gasStart <= constant)"] and \
                        tx not in FPMap["require(gasStart <= constant)"]:

                        FPMap["require(gasStart <= constant)"].append(tx)

                    if "require(gasStart - gasEnd <= constant)" in invariantMap[name]:
                        
                        if funcCall["gas"] - funcCall["gasEnd"] > invariantMap[name]["require(gasStart - gasEnd <= constant)"] and \
                            tx not in FPMap["require(gasStart - gasEnd <= constant)"]:

                            FPMap["require(gasStart - gasEnd <= constant)"].append(tx)

