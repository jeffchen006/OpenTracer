import sys
import os
from parserPackage.locator import *
from trackerPackage.dataSource import *
from fetchPackage.fetchTrace import fetcher 
from crawlPackage.crawlQuicknode import CrawlQuickNode
from crawlPackage.crawlEtherscan import CrawlEtherscan
from utilsPackage.compressor import *
from staticAnalyzer.analyzer import Analyzer

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

import toml
settings = toml.load("settings.toml")





def inferTimeLocks(accesslistTable, enterFuncs, exitFuncs):
    
    crawlQuickNode = CrawlQuickNode()
    crawlEtherscan = CrawlEtherscan()


    for contract, accessList in accesslistTable:
        if any(i in enterFuncs for i in exitFuncs):
            sys.exit("timeLockInfer: enterFuncs and exitFuncs overlap")

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
        # { 
        #   "func": (shortest_block_gap, lastCallBlock) 
        #   "checkSameSenderBlock": True/False
        #   "checkSameOriginBlock": True/False
        # }


        counter = -1

        analyzer = Analyzer()
        for tx, funcCallList in accessList:
            counter += 1

            origin = crawlQuickNode.Tx2Details(tx)["from"].lower()
            block = crawlQuickNode.Tx2Block(tx)

            if len(funcCallList) != 1:
                print(funcCallList)
                sys.exit("access control infer: not one function call in a transaction")

            for funcCall in funcCallList[0]:
                sender = funcCall["msg.sender"].lower()
                name = ""
                if "name" in funcCall:
                    if funcCall["name"] == "fallback" and funcCall["Selector"] != "0x":
                        # get real funcName from selector and contract
                        funcSigMap = analyzer.contract2funcSigMap(contract)
                        funcCall["name"] = funcSigMap[funcCall["Selector"].lower()][0]
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
        # print(timeLocksMap)
        pp.pprint(invariantMap)

        print("Interpretation of the above invariant map: ")
        for func in invariantMap:
            if func == "checkSameOriginBlock" or func == "checkSameSenderBlock":
                print("is the invariant {} satisfied? {}".format(func, invariantMap[func]))
            else:
                print("For the function {}, the shortest block gap is {} and the last call block is {}".format(func, invariantMap[func][0], invariantMap[func][1]))
