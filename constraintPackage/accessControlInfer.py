import sys
import os
from parserPackage.locator import *
from parserPackage.parser import proxyMap
from trackerPackage.dataSource import *
from crawlPackage.crawlQuicknode import CrawlQuickNode
from crawlPackage.crawlEtherscan import CrawlEtherscan
from utilsPackage.compressor import *
from staticAnalyzer.analyzer import Analyzer


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

import toml
settings = toml.load("settings.toml")


# check 3 invariants:
# 1. msg.sender != tx.origin
# 2. is msg.sender/tx.origin owner?
# 3. is msg.sender/tx.origin manager?
def inferAccessControl(accesslistTable):    
    crawlQuickNode = CrawlQuickNode()
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
        analyzer = Analyzer()
        for tx, funcCallList in accessList:
            counter += 1
            origin = crawlQuickNode.Tx2Details(tx)["from"].lower()
            if len(funcCallList) != 1:
                print(funcCallList)
                sys.exit("access control infer: not one function call in a transaction")

            for funcCall in funcCallList[0]:
                sender = funcCall["msg.sender"].lower()
                name = ""
                if "type" in funcCall and funcCall["type"] == "staticcall":
                    continue
                
                if "name" in funcCall:
                    if funcCall["name"] == "fallback" and funcCall["Selector"] != "0x":
                        # get real funcName from selector and contract
                        funcSigMap = analyzer.contract2funcSigMap(contract)
                        funcCall["name"] = funcSigMap[funcCall["Selector"].lower()][0]
                    name += funcCall["name"]
                    if funcCall["name"] not in nonReadOnlyFunctions:
                        continue

                if name == "":
                    if "structLogsStart" in funcCall and "structLogsEnd" in funcCall and \
                        funcCall["structLogsEnd"] - funcCall["structLogsStart"] <= 20 and \
                        "type" in funcCall and funcCall["type"] == "delegatecall":
                        continue
                    else:
                        print(tx)
                        sys.exit("access control infer: name is empty")
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


        print("Interpretation of the above invariant map: ")

        for func in invariantMap:
            print("For the function {}:".format(func))
            for key in invariantMap[func]:
                if key == "isSenderManager" or key == "isOriginManager":
                    print("\tthe invariant {} has parameters {}".format(key, invariantMap[func][key]))
                else:
                    print("\tis the invariant {} satisfied? {}".format(key, invariantMap[func][key])) 
