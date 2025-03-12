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
        newFPMap[invariant] = "{}/{}".format( len(FPMap[invariant]), int(txCount * 0.3) )
    # print(newFPMap)

    invariants = ['require(origin==sender)', 'isSenderOwner', 'isSenderManager', 'isOriginOwner', 'isOriginManager']
    invariants = ['require(origin==sender)']
    
    print(invariants)
    for invariant in invariants:
        if invariant in newFPMap:
            print("{}\t".format(len(FPMap[invariant])), end ="" )
        else:
            print("N/A\t", end = "")

    trainingSet = int(txCount * proportion)
    testingSet = txCount - trainingSet
    
    print("\t{}\t{}".format( trainingSet, testingSet ))

    for invariant in invariants:
        if invariant in FPMap:
            print("5 sampled FPs for {}".format(invariant))
            sampledFPs = sample_five_elements(FPMap[invariant])
            for fp in sampledFPs:
                print(fp)





def inferAccessControl(accesslistTable, txCount):    
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
        
        # if benchmarkName != "Harvest2_fUSDC":
        #     continue


        # stage 1: training
        accessControlMap = {}
        # { "func": 
        #             {
        #                 "origin!=sender": 0, 
        #                 "sender": { 
        #                             addr: times,
        #                            }
        #                 "origin": { 
        #                             addr: times,
        #                            }
        #             }
        # }
        invariantMap = {}
        # { "func":
        #             { 
        #                   "require(origin==sender)": true, 
        #                   "isSenderOwner": addr,
        #                   "isSenderManager": a list of addr,
        #                   "isOriginOwner": addr,
        #                   "isOriginManager": a list of addr,
        #               }
        # }
        counter = -1

        txList = []
        txList3 = []
        for tx, funcCallList in accessList:
            counter += 1
            if tx not in txList:
                txList.append(tx)

            if tx not in txList3:
                txList3.append(tx)

            origin = crawlEtherscan.Tx2Details(tx)["from"].lower()
            if len(funcCallList) != 1:
                print(funcCallList)
                sys.exit("access control infer: not one function call in a transaction")

            for funcCall in funcCallList[0]:
                sender = funcCall["msg.sender"].lower()
                name = ""
                if "type" in funcCall and funcCall["type"] == "staticcall":
                    continue
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
                        
                if name == "":
                    if "structLogsStart" in funcCall and "structLogsEnd" in funcCall and \
                        funcCall["structLogsEnd"] - funcCall["structLogsStart"] <= 20 and \
                        "type" in funcCall and funcCall["type"] == "delegatecall":
                        continue
                    else:
                        # print(tx)
                        # sys.exit("access control infer: name is empty")
                        pass

                if "Selector" in funcCall:
                    name += funcCall["Selector"]

                if name not in accessControlMap:
                    c = int(origin != sender)
                    accessControlMap[name] = {
                        "origin!=sender": c, 
                        "sender": {sender: 1}, 
                        "origin": {origin: 1}
                    } 
                else:
                    if origin != sender:
                        accessControlMap[name]["origin!=sender"] += 1
                        # print("func", name, "origin", origin, "sender", sender)

                    if sender not in accessControlMap[name]["sender"]:
                        accessControlMap[name]["sender"][sender] = 1
                    else:
                        accessControlMap[name]["sender"][sender] += 1

                    if origin not in accessControlMap[name]["origin"]:
                        accessControlMap[name]["origin"][origin] = 1
                    else:
                        accessControlMap[name]["origin"][origin] += 1
            cutoff = txCount * proportion
            now = len(txList)
            if len(txList) > txCount * proportion:
                counter += 1
                break
        

        # stage 2: infer
        for func in accessControlMap:
            invariantMap[func] = {}
            # invariant 1: origin != sender
            if accessControlMap[func]["origin!=sender"] == 0:
                invariantMap[func]["require(origin==sender)"] = True
            else:
                invariantMap[func]["require(origin==sender)"] = False

            # invariant 2: sender is owner or manager, origin is owner or manager
            if len(accessControlMap[func]["sender"].keys()) == 1:
                invariantMap[func]["isSenderOwner"] = list(accessControlMap[func]["sender"].keys())[0]
            if len(accessControlMap[func]["sender"].keys()) >= 5:
                print("func {} has more than 5 senders".format(func))
            elif len(accessControlMap[func]["sender"].keys()) == 1:
                print("func {} has only 1 sender".format(func))
            else:
                invariantMap[func]["isSenderManager"] = list(accessControlMap[func]["sender"].keys())

            if len(accessControlMap[func]["origin"].keys()) == 1:
                invariantMap[func]["isOriginOwner"] = list(accessControlMap[func]["origin"].keys())[0]
            if len(accessControlMap[func]["origin"].keys()) >= 5:
                print("func {} has more than 5 origins".format(func))
            elif len(accessControlMap[func]["origin"].keys()) == 1:
                print("func {} has only 1 origin".format(func))
            else:
                invariantMap[func]["isOriginManager"] = list(accessControlMap[func]["origin"].keys())

        
        print("==invariant map: ")
        import pprint
        pp = pprint.PrettyPrinter(indent=2)
        pp.pprint(invariantMap)

        
        isHavingEOA = False
        for func in invariantMap:
            if "require(origin==sender)" in invariantMap[func] and invariantMap[func]["require(origin==sender)"]:
                isHavingEOA = True
                break



        # stage 3: validation
        FPMap = {
            "require(origin==sender)": [],
            "isSenderOwner": [],
            "isSenderManager": [],
            "isOriginOwner": [],
            "isOriginManager": [],
        }


        txList2 = []
        isFiltered = False
        isFilteredByEOA = False
        
        gasUsedMap = {}
        gasEOAOverHeadMap = {}

        for ii, (tx, funcCallList) in enumerate(accessList[counter:]):
            currentIndex = ii + counter
            if tx not in txList2:
                txList2.append(tx)
            if tx not in txList3:
                txList3.append(tx)
            testingSetSize = len(txList2)

            details = crawlEtherscan.Tx2Details(tx)
            origin = details["from"].lower()
            gasUsed = details["gasUsed"]
            if not isinstance(gasUsed, int):
                gasUsed = int(gasUsed, 16)

            if tx == exploitTx:
                # store testing set for each benchmark
                for funcCall in funcCallList[0]:
                    sender = funcCall["msg.sender"].lower()

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
                    if "require(origin==sender)" in invariantMap[name] and invariantMap[name]["require(origin==sender)"]:
                        if origin != sender:
                            isFiltered = True
                            isFilteredByEOA = True
                            print("Successfully stops the exploit using require(origin==sender)")

                    if ("isSenderOwner" in invariantMap[name] and sender != invariantMap[name]["isSenderOwner"]):
                        isFiltered = True
                        print("Successfully stops the exploit using isSenderOwner")
                    
                    if ("isSenderManager" in invariantMap[name] and sender not in invariantMap[name]["isSenderManager"]):
                        isFiltered = True
                        print("Successfully stops the exploit using isSenderManager")

                    if ("isOriginOwner" in invariantMap[name] and origin != invariantMap[name]["isOriginOwner"]):
                        isFiltered = True
                        print("Successfully stops the exploit using isOriginOwner")

                    if ("isOriginManager" in invariantMap[name] and origin not in invariantMap[name]["isOriginManager"]):
                        isFiltered = True
                        print("Successfully stops the exploit using isOriginManager")


                if len(accessList) == currentIndex + 1 or accessList[currentIndex + 1][0] != exploitTx:
                    print("exploitTx: ", exploitTx)
                    print("FPMap: ", end="")
                    printFPMap(invariantMap, FPMap, benchmarkName, txCount)
                    if exploitTx not in txList3:
                        txList3.append(exploitTx)
                    print("len(txList3): ", len(txList3))

                    newList = copy.deepcopy(FPMap["require(origin==sender)"])
                    newList.insert(0, 'exploitTx: {}'.format(exploitTx))


                    if isFilteredByEOA:
                        newList.append(exploitTx)

                        
                    # if benchmarkName in gasBenchmarks:
                    #     gasPath = SCRIPT_DIR + "/cache/gas/{}.json".format(benchmarkName)
                    #     gasOverheadPath = SCRIPT_DIR + "/cache/gas/{}_EOA.json".format(benchmarkName)
                    #     writeJson(gasPath, gasUsedMap)
                    #     writeJson(gasOverheadPath, gasEOAOverHeadMap)

                    
            else:
                for funcCall in funcCallList[0]:
                    sender = funcCall["msg.sender"].lower()
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
                        
                    if "require(origin==sender)" in invariantMap[name] and invariantMap[name]["require(origin==sender)"]:
                        if origin != sender and tx not in FPMap["require(origin==sender)"]:
                            # print("func: ", name, "origin: ", origin, "sender: ", sender)
                            FPMap["require(origin==sender)"].append(tx)
                            

                    if "isSenderOwner" in invariantMap[name] and sender != invariantMap[name]["isSenderOwner"] and \
                        tx not in FPMap["isSenderOwner"]:
                        FPMap["isSenderOwner"].append(tx)
                    if "isOriginOwner" in invariantMap[name] and origin != invariantMap[name]["isOriginOwner"] and \
                        tx not in FPMap["isOriginOwner"]:
                        FPMap["isOriginOwner"].append(tx)
                    if "isSenderManager" in invariantMap[name] and sender not in invariantMap[name]["isSenderManager"] and \
                        tx not in FPMap["isSenderManager"]:
                        FPMap["isSenderManager"].append(tx)
                    if "isOriginManager" in invariantMap[name] and origin not in invariantMap[name]["isOriginManager"] and \
                        tx not in FPMap["isOriginManager"]:
                        FPMap["isOriginManager"].append(tx)
                    
