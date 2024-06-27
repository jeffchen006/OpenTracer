import sys
import os
from parserPackage.locator import *
import copy
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





# check 2 invariants:
# 1. re-entrant locks only on one type of functions - enter or exit
# 2. re-entrant locks on both types of functions - enter and exit
#
# functions regarding token transfers cannot be re-entrant
# for some special cases



def inferReentrancy(accesslistTable, enterFunction, exitFunction):
    for contract, accessList in accesslistTable:
        tokenInFunctions = enterFunction
        tokenOutFunctions = exitFunction

        tokenMoveFunctions = tokenInFunctions + tokenOutFunctions
        tokenMoveFunctions = list(set(tokenMoveFunctions))
        

# check 1 invariant:
# 1. re-entrant locks on both types of functions - enter and exit

# functions regarding token transfers cannot be re-entrant
# for some special cases
        # stage 1: training

        lastTokenMove = (0, [])
        #   (transaction, [ (structLogsStart, structLogsEnd), ... ] )

        invariantMap = {
            "NonReentrantLocks": len(tokenInFunctions) >  0 or len(tokenOutFunctions) > 0,
        }

        counter = -1
        analyzer = Analyzer()
        for tx, funcCallList in accessList:
            counter += 1
            if len(funcCallList) != 1:
                print(funcCallList)
                sys.exit("access control infer: not one function call in a transaction")

            for funcCall in funcCallList[0]:
                name = ""
                if "name" in funcCall:
                    if funcCall["name"] == "fallback" and funcCall["Selector"] != "0x":
                        # get real funcName from selector and contract
                        funcSigMap = analyzer.contract2funcSigMap(contract)
                        funcCall["name"] = funcSigMap[funcCall["Selector"].lower()][0]

                    name += funcCall["name"]
                    if funcCall["name"] not in tokenMoveFunctions:
                        continue

                structLogsStart = funcCall["structLogsStart"]
                structLogsEnd = funcCall["structLogsEnd"]

                if name in tokenMoveFunctions:
                    if tx == lastTokenMove[0]:
                        for oldStructLogsStart, oldStructLogsEnd, oldName in lastTokenMove[1]:
                            if (structLogsStart > oldStructLogsStart and structLogsEnd < oldStructLogsEnd) or \
                                (oldStructLogsStart > structLogsStart and oldStructLogsEnd < structLogsEnd):
                                # find one re-entrancy
                                invariantMap["NonReentrantLocks"] = False
                            
                            if structLogsStart == oldStructLogsStart and structLogsEnd == oldStructLogsEnd and name == oldName:
                                # find one re-entrancy
                                print("now is the time")
                        lastTokenMove[1].append((structLogsStart, structLogsEnd, name))
                    else:
                        lastTokenMove = (tx, [ (structLogsStart, structLogsEnd, name) ])


        # stage 2: infer
        # functions regarding token transfers cannot be re-entrant
        # for some special cases
        print("==invariant list: ")
        print(invariantMap)

        print("Interpretation of the above invariant map: ")
        if invariantMap["NonReentrantLocks"] == False:
            print("re-entrancy guard cannot be applied")
        else:
            print("re-entrancy guard can be applied")

    