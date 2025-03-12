import sys
import os
from parserPackage.locator import *
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






def printFPMap(invariantMap, FPMap, benchmarkName, txCount):
    invariants = ['checkSameSenderBlock', 'checkSameOriginBlock', 'SameFuncGap']
    invariants = ['checkSameOriginBlock']

    print(invariants)
    if invariantMap["checkSameSenderBlock"] is False:
        print("N/A\t", end = "")
    else:
        print("{}\t".format(len(FPMap["checkSameSenderBlock"]) ), end ="" )
    
    if invariantMap["checkSameOriginBlock"] is False:
        print("N/A\t", end = "")
    else:
        print("{}\t".format(len(FPMap["checkSameOriginBlock"]) ), end ="" )

    if len(invariantMap.keys()) <= 2:
        print("N/A\t", end = "")
    else:
        print("{}\t".format(len(FPMap["SameFuncGap"]) ), end ="" )


    print("")
        
    for invariant in FPMap:
        print("5 sampled FPs for {}".format(invariant))
        sampledFPs = sample_five_elements(FPMap[invariant])
        for fp in sampledFPs:
            print(fp)



def inferTimeLocks(accesslistTable, enterFuncs, exitFuncs, txCount):
    
    crawlQuickNode = CrawlQuickNode()
    crawlEtherscan = CrawlEtherscan()
    
    
    for benchmarkName, contract, accessList, exploitTx in accesslistTable:
        print("====== benchmark {}: ".format(benchmarkName))

        if any(i in enterFuncs for i in exitFuncs):
            sys.exit("timeLockInfer: enterFuncs and exitFuncs overlap")
        # if benchmarkName not in verboseBenchmarks:
        #     continue

        # build read-only functions
        ABI = crawlEtherscan.Contract2ABI(contract)
        readOnlyFunctions = ["fallback"]
        for function in ABI:
            if function["type"] == "function" and function["stateMutability"] == "view":
                readOnlyFunctions.append(function["name"])

# check 2 invariants:
# 1. the same origin/sender cannot enters and exits the protocol in the same block
#     _lastCallerBlock = keccak256(abi.encodePacked(tx.origin, block.number));
#    require(keccak256(abi.encodePacked(tx.origin, block.number)) != _lastCallerBlock, "8");

# 2. the same function cannot be called within a gap of N blocks
#    block - lastUpdate > constant

        # stage 1: training
        timeLocksMap = {}
        # { 
        #    "func":  [block1, block2, ...], 
        # }
        senderBlockPair = (0, 0)
        #            (sender, block)
        originBlockPair = (0, 0)
        #            (origin, block)

        invariantMap = {
            "checkSameSenderBlock": len(enterFuncs) > 0 and len(exitFuncs) > 0,
            "checkSameOriginBlock": len(enterFuncs) > 0 and len(exitFuncs) > 0,
        }

        print("enterFuncs: ", enterFuncs)
        print("exitFuncs: ", exitFuncs)
        print("len(enterFuncs) + len(exitFuncs) = ", len(enterFuncs) + len(exitFuncs))
        # { 
        #   "func": (shortest_block_gap, lastCallBlock) 
        #   "checkSameSenderBlock": True/False
        #   "checkSameOriginBlock": True/False
        # }



        counter = -1

        txList = []
        for tx, funcCallList in accessList:
            counter += 1
            if tx not in txList:
                txList.append(tx)
                
            origin = crawlQuickNode.Tx2Details(tx)["from"].lower()
            block = crawlQuickNode.Tx2Block(tx)

            if len(funcCallList) != 1:
                print(funcCallList)
                sys.exit("access control infer: not one function call in a transaction")

            for funcCall in funcCallList[0]:
                sender = funcCall["msg.sender"].lower()
                name = ""
                if "name" in funcCall:
                    name += funcCall["name"]
                    if funcCall["name"] in readOnlyFunctions:
                        continue
                    # if funcCall["name"] not in enterFuncs + exitFuncs:
                    #     continue
                # if "Selector" in funcCall:
                #     name += funcCall["Selector"]
                if name not in timeLocksMap:
                    timeLocksMap[name] = [block]
                else:
                    timeLocksMap[name].append(block)


                if name in enterFuncs:
                    originBlockPair = (origin, block)
                    senderBlockPair = (sender, block)
                if name in exitFuncs:
                    if origin == originBlockPair[0] and block == originBlockPair[1]: 
                        invariantMap["checkSameOriginBlock"] = False
                    if sender == senderBlockPair[0] and block == originBlockPair[1]:
                        invariantMap["checkSameSenderBlock"] = False

            if len(txList) > txCount * proportion:
                counter += 1
                break
        
        # stage 2: infer
        # invariant 1:  the same origin/sender cannot enters and exits the protocol in the same block
        pass 
        # i) checkSameSenderBlock  
        # ii) checkSameOriginBlock
        
        # invariantMap = { 
        #   "func": (shortest_block_gap, lastCallBlock) 
        #   "checkSameSenderBlock": True/False
        #   "checkSameOriginBlock": True/False
        # }

        
        # invariant 2: the same function cannot be called within a gap of N blocks
        for func in timeLocksMap:
            if len(timeLocksMap[func]) >= 2:
                shortestGap = 99999999999
                for i in range(len(timeLocksMap[func])-1):
                    thisCall = timeLocksMap[func][i]
                    nextCall = timeLocksMap[func][i+1]
                    gap = nextCall - thisCall
                    if gap < shortestGap:
                        shortestGap = gap
                # print("shortestGap: {} for func {}".format(shortestGap, func), end = "")
                if shortestGap != 0:
                    if func in invariantMap:
                        sys.exit("invariantMap[func] already exists")
                    else:
                        invariantMap[func] = (shortestGap, timeLocksMap[func][-1])

        
        print("==invariant map: ")
        import pprint
        pp = pprint.PrettyPrinter(indent=2)
        print(timeLocksMap)
        pp.pprint(invariantMap)
        

        
        # stage 3: validation
        FPMap = {
            "checkSameSenderBlock": [],
            "checkSameOriginBlock": [],
            "SameFuncGap": [],
        }

        txList2 = []
        isFiltered = False
        isFilteredBycheckSameOriginBlock = False

        gasOBOverHeadMap = {}
        
        for ii, (tx, funcCallList) in enumerate(accessList[counter:]):
            currentIndex = ii + counter
            if tx not in txList2:
                txList2.append(tx)

            # if tx == "0xa2eebfe1ceda00253bf073f47c7d2f9189093a17ebd23439c70a4c48b5a0d2d5":
            #     print("now is the time")
            
            details = crawlQuickNode.Tx2Details(tx)
            origin = details["from"].lower()

                
            block = crawlQuickNode.Tx2Block(tx)

            if tx == exploitTx:
                for funcCall in funcCallList[0]:
                    sender = funcCall["msg.sender"].lower()
                    name = ""
                    if "name" in funcCall:
                        name += funcCall["name"]
                        if funcCall["name"] in readOnlyFunctions:
                            continue
                    # key = tx + "_" + str(funcCall["gas"])
                    # if key not in gasOBOverHeadMap:
                    #     gasOBOverHeadMap[key] = gasUsed

                    # if "Selector" in funcCall:
                    #     name += funcCall["Selector"]
                    if invariantMap["checkSameSenderBlock"] and name in exitFuncs and \
                        sender == senderBlockPair[0] and senderBlockPair[1] == block:
                        isFiltered = True
                        print("Successfully stops the exploit using same sender block")
                    
                    if invariantMap["checkSameOriginBlock"] and name in exitFuncs:
                        if origin == originBlockPair[0] and originBlockPair[1] == block:
                            isFiltered = True
                            isFilteredBycheckSameOriginBlock = True
                            print("Successfully stops the exploit using same origin block")

                    if name in invariantMap:
                        if block - invariantMap[name][1] < invariantMap[name][0]:
                            isFiltered = True
                            print("Successfully stops the exploit using enforced short same function gap")
                            print("shortestGap: {} for func {} but current gap = {}".format(invariantMap[name][0], name, block - invariantMap[name][1]))

                        invariantMap[name] = (invariantMap[name][0], block)

                    if name in enterFuncs:        
                        originBlockPair = (origin, block)
                        senderBlockPair = (sender, block)

                if len(accessList) == currentIndex + 1 or accessList[currentIndex + 1][0] != exploitTx:
                    print("exploitTx: ", exploitTx)
                    print("FPMap: ", end="")
                    printFPMap(invariantMap, FPMap, benchmarkName, txCount)


                    newList = copy.deepcopy(FPMap["checkSameOriginBlock"])
                    newList.insert(0, 'exploitTx: {}'.format(exploitTx))

                    if isFilteredBycheckSameOriginBlock:
                        newList.append(exploitTx)
                    
                    # if benchmarkName in gasBenchmarks:
                    #     gasOverheadPath = SCRIPT_DIR + "/cache/gas/{}_OB.json".format(benchmarkName)
                    #     writeJson(gasOverheadPath, gasOBOverHeadMap)
                    break

            
            else:
                for funcCall in funcCallList[0]:
                    sender = funcCall["msg.sender"].lower()
                    name = ""
                    if "name" in funcCall:
                        name += funcCall["name"]
                    # if "Selector" in funcCall:
                    #     name += funcCall["Selector"]

                    # key = tx + "_" + str(funcCall["gas"])
                    # if key not in gasOBOverHeadMap:
                    #     gasOBOverHeadMap[key] = gasUsed
                    
                    if name not in invariantMap and invariantMap["checkSameSenderBlock"] is False and invariantMap["checkSameOriginBlock"] is False:
                        continue

                    if name in enterFuncs:
                        originBlockPair = (origin, block)
                        senderBlockPair = (sender, block)

                    
                    if invariantMap["checkSameOriginBlock"] and name in exitFuncs:
                        if origin == originBlockPair[0] and block == originBlockPair[1]:
                            if tx not in FPMap["checkSameOriginBlock"]:
                                FPMap["checkSameOriginBlock"].append(tx + "=" + name + "=" + funcCall["gas"] + "-" + funcCall["gasEnd"])
                    
                    if invariantMap["checkSameSenderBlock"] and name in exitFuncs and sender == senderBlockPair[0] and \
                        block == senderBlockPair[1]:
                        if tx not in FPMap["checkSameSenderBlock"]:
                            FPMap["checkSameSenderBlock"].append(tx)

                    if name in invariantMap:
                        if block - invariantMap[name][1] < invariantMap[name][0]:
                            if tx not in FPMap["SameFuncGap"]:
                                FPMap["SameFuncGap"].append(tx)

                        invariantMap[name] = (invariantMap[name][0], block)


