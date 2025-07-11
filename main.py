import sys
import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

import cProfile

from fetchPackage.fetchTrace import *
from parserPackage.locator import *
from parserPackage.parserGlobal import *
from parserPackage.parser import *
from crawlPackage.crawl import Crawler
from constraintPackage.accessControlInfer import *
from constraintPackage.dataFlowInfer import *
from constraintPackage.gasControlInfer import *
from constraintPackage.moneyFlowInfer import *
from constraintPackage.oracleControl import *
from constraintPackage.reentrancyInfer import *
from constraintPackage.specialStorage   import *
from constraintPackage.timeLockInfer import *
from newBenchmarks.decodeTxList import decodeTxlistForBenchmark


def collectTransactionHistory(contractAddress, endBlock: int = -1):
    crawler = Crawler()
    txHashes = None
    if endBlock == -1:
        txHashes = crawler.Contract2TxHistory(contractAddress)
    else:
        txHashes = crawler.Contract2TxHistory(contractAddress, endBlock)
    return txHashes 

def storeATrace(txHash: str):
    fe = fetcher()
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    if not os.path.exists(SCRIPT_DIR + "/cache"):
        os.makedirs(SCRIPT_DIR + "/cache")
    path = SCRIPT_DIR + "/cache/" + txHash + ".json.gz"
    # check if the file exists
    if os.path.exists(path):
        return
    result_dict = fe.getTrace(txHash, FullTrace = False)
    writeCompressedJson(path, result_dict)

def readATrace(txHash: str):
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    path = SCRIPT_DIR + "/cache/" + txHash + ".json.gz"
    if not os.path.exists(path):
        return None
    readCompressed = readCompressedJson(path)
    return readCompressed

def parseATrace(txHash: str):
    # pa = VmtraceParserGlobal()
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    path = SCRIPT_DIR + "/cache/" + txHash + ".json.gz"
    temp =  analyzeOneTxGlobal(txHash, path)
    return temp

def analyzeOneTxHelper(contract, tx, path, depositLocator, investLocator, withdrawLocator):
    try:
        dataSourceMapList, accessList, splitedTraceTree = analyzeOneTx(contract, tx, path, depositLocator, investLocator, withdrawLocator)        
        writeDataSource(contract, tx, dataSourceMapList)
        writeAccessList(contract, tx, accessList)
        writeSplitedTraceTree(contract, tx, splitedTraceTree)
        return
    except Exception as e:
        print(e, file=sys.stderr)
        print("Some error happened when analyzing tx: {} path: {}".format(tx, path), file=sys.stderr)
        sys.exit("Some error happened when analyzing tx: {} path: {}".format(tx, path))

def writeDataSource(contract, tx, dataSourceMapList):
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    path = SCRIPT_DIR + "/cache/" + contract + "/{}.pickle".format(tx)
    # print("write", path)
    # print(dataSourceMapList)
    with open(path, 'wb') as f:
        pickle.dump(dataSourceMapList, f)

def readDataSource(contract, tx):
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    path = SCRIPT_DIR + "/cache/" + contract + "/{}.pickle".format(tx)
    objects = []
    # check if file exists
    if not os.path.exists(path):
        return objects
    with (open(path, "rb")) as openfile:
        while True:
            try:
                objects.append(pickle.load(openfile))
            except EOFError:
                break
    return objects

def writeAccessList(contract, tx, accessList):
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    path = SCRIPT_DIR + "/cache/" + contract + "_Access/{}.pickle".format(tx)
    # print("write", path)
    # print(dataSourceMapList)
    with open(path, 'wb') as f:
        pickle.dump(accessList, f)

def readAccessList(contract, tx):
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) 
    path = SCRIPT_DIR + "/cache/" + contract + "_Access/{}.pickle".format(tx)
    objects = []
    # check if file exists
    if not os.path.exists(path):
        return objects
    with (open(path, "rb")) as openfile:
        while True:
            try:
                objects.append(pickle.load(openfile))
            except EOFError:
                break
    return objects

def writeSplitedTraceTree(contract, tx, splitedTraceTree):
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    path = SCRIPT_DIR + "/cache/" + contract + "_SplitedTraceTree/{}.pickle".format(tx)
    # print("write", path)
    # print(dataSourceMapList)
    with open(path, 'wb') as f:
        pickle.dump(splitedTraceTree, f)

def readSplitedTraceTree(contract, tx):
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    path = SCRIPT_DIR + "/cache/" + contract + "_SplitedTraceTree/{}.pickle".format(tx)
    objects = []
    # check if file exists
    if not os.path.exists(path):
        return objects
    with (open(path, "rb")) as openfile:
        while True:
            try:
                objects.append(pickle.load(openfile))
            except EOFError:
                break
    return objects

def reformatExecutionTable(executionTable: list):
    # refactor improper formatted entry
    newExecutionTable = []
    for contract, executionList in executionTable:
        counter = 0
        new_executionList = []
        for ii in range(len(executionList)):
            execution = executionList[ii]
            if isinstance(execution[1], list):
                if len(execution[1]) == 1:
                    executionList[ii] = (execution[0], execution[1][0].to_dict())
                    new_executionList.append(  (execution[0], execution[1][0].to_dict() ) )
                else: # means one execution contains multiple target locations
                    executionList[ii] = [execution[0], []]
                    gasUsed = []
                    for jj in range(len(execution[1])):
                        gas = execution[1][jj].metaData['gas']
                        if gas not in gasUsed: # there is a possibility of duplicate counting
                            executionList[ii][1].append(  execution[1][jj].to_dict() )

                    if len( executionList[ii][1]) == 1:
                        executionList[ii][1] = executionList[ii][1][0].to_dict()
                    else:
                        if counter == 0:
                            print("{} has one function call with several transfers".format(contract))
                            counter = 1
                    for jj in range(len(executionList[ii][1])):
                        new_executionList.append( (executionList[ii][0], executionList[ii][1][jj] )  )
            else:
                sys.exit("not isinstance(execution[1], list)")
        newExecutionTable.append( (contract, new_executionList) )
    return newExecutionTable

def mainTestIndividual():
    # mainDoughFina2()
    # mainBlueberryProtocol1()
    mainUwULend1()

def mainDoughFina1():
    benchmark = "DoughFina"
    contract = "0x9f54e8eaa9658316bb8006e03fff1cb191aafbe6"
    l1 = []
    l2 = []
    l3 = []
    enterFunction = []
    exitFunction = []
    exploitTx = "0x92cdcc732eebf47200ea56123716e337f6ef7d5ad714a2295794fdc6031ebb2e"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)
    # SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))    
    # path = SCRIPT_DIR + "/newBenchmarks/" + benchmark + "/Txs/" + exploitTx + ".json.gz"
    # DataSourceMapList, accessList, splitedTraceTree = analyzeOneTx(contract, exploitTx, path, l1, l2, l3)        
    # print(DataSourceMapList)
    # print(accessList)
    # print(splitedTraceTree)

def mainDoughFina2():
    benchmark = "DoughFina"
    contract = "0x534a3bb1ecb886ce9e7632e33d97bf22f838d085"
    l1 = []
    l2 = []
    l3 = [
        locator("executeOperation", FUNCTION, funcAddress = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", \
            name="transferFrom", position=2),
    ]
    enterFunction = []
    exitFunction = []
    exploitTx = "0x92cdcc732eebf47200ea56123716e337f6ef7d5ad714a2295794fdc6031ebb2e"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)
    # SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))    
    # path = SCRIPT_DIR + "/newBenchmarks/" + benchmark + "/Txs/" + exploitTx + ".json.gz"
    # DataSourceMapList, accessList, splitedTraceTree = analyzeOneTx(contract, exploitTx, path, l1, l2, l3)        
    # print(DataSourceMapList)
    # print(accessList)
    # print(splitedTraceTree)

def mainBedrock_DeFi1():
    benchmark = "Bedrock_DeFi"
    contract = "0x004e9c3ef86bc1ca1f0bb5c7662861ee93350568"
    l1 = []
    l2 = []
    l3 = []
    enterFunction = []
    exitFunction = []
    exploitTx = "0x725f0d65340c859e0f64e72ca8260220c526c3e0ccde530004160809f6177940"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)

def mainBedrock_DeFi2():
    benchmark = "Bedrock_DeFi"
    contract = "0x047d41f2544b7f63a8e991af2068a363d210d6da"
    l1 = [ locator("mint", SELFCALLVALUE)]
    l2 = []
    l3 = [ locator("mint", FUNCTION, funcAddress = "0x004e9c3ef86bc1ca1f0bb5c7662861ee93350568", \
                name="mint", position=1)]
    enterFunction = []
    exitFunction = []
    exploitTx = "0x725f0d65340c859e0f64e72ca8260220c526c3e0ccde530004160809f6177940"
    # exploitTx = "0x23cd0fba79d4dfa88113c2ded6183c5030813b48fcb90810f7cf9989d658a6d7"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)
    # SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))    
    # path = SCRIPT_DIR + "/newBenchmarks/" + benchmark + "/Txs/" + exploitTx + ".json.gz"
    # DataSourceMapList, accessList, splitedTraceTree = analyzeOneTx(contract, exploitTx, path, l1, l2, l3)        
    # print(DataSourceMapList)
    # print(accessList)
    # print(splitedTraceTree)

def mainGFOX1():
    benchmark = "GFOX"  # close source!
    contract = "0x11a4a5733237082a6c08772927ce0a2b5f8a86b6"
    l1 = []
    l2 = []
    l3 = [
        locator("claim", FUNCTION, fromAddr= "0x8f1cece048cade6b8a05dfa2f90ee4025f4f2662", \
            name="transfer", position=1),
    ]
    enterFunction = []
    exitFunction = ["claim"]
    exploitTx = "0x12fe79f1de8aed0ba947cec4dce5d33368d649903cb45a5d3e915cc459e751fc"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)
    # SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))    
    # path = SCRIPT_DIR + "/newBenchmarks/" + benchmark + "/Txs/" + exploitTx + ".json.gz"
    # DataSourceMapList, accessList, splitedTraceTree = analyzeOneTx(contract, exploitTx, path, l1, l2, l3)        
    # print(DataSourceMapList)
    # print(accessList)
    # print(splitedTraceTree)

def mainGFOX2():
    benchmark = "GFOX"
    contract = "0x8f1cece048cade6b8a05dfa2f90ee4025f4f2662"
    l1 = []
    l2 = []
    l3 = []
    enterFunction = []
    exitFunction = []
    exploitTx = "0x12fe79f1de8aed0ba947cec4dce5d33368d649903cb45a5d3e915cc459e751fc"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)

def mainBlueberryProtocol1():
    benchmark = "BlueberryProtocol"
    contract = "0xffadb0bba4379dfabfb20ca6823f6ec439429ec2"
    l1 = []
    l2 = []
    l3 = []
    enterFunction = []
    exitFunction = []
    exploitTx = "0xf0464b01d962f714eee9d4392b2494524d0e10ce3eb3723873afd1346b8b06e4"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)
    
def mainBlueberryProtocol2():
    benchmark = "BlueberryProtocol"
    contract = "0x643d448cea0d3616f0b32e3718f563b164e7edd2"
    l1 = [
        locator("mint", FUNCTION, fromAddr="0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", \
                name="transferFrom", position=2),
    ]
    l2 = []
    l3 = []
    enterFunction = ["mint"]
    exitFunction = []
    exploitTx = "0xf0464b01d962f714eee9d4392b2494524d0e10ce3eb3723873afd1346b8b06e4"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)

def mainBlueberryProtocol3():
    benchmark = "BlueberryProtocol"
    contract = "0x08830038a6097c10f4a814274d5a68e64648d91c"
    l1 = []
    l2 = []
    l3 = [
        locator("borrow", FUNCTION, fromAddr="0x64aa3364f17a4d01c6f1751fd97c2bd3d7e7f1d5", \
                name="transfer", position=1),
    ]
    enterFunction = []
    exitFunction = ["borrow"]
    exploitTx = "0xf0464b01d962f714eee9d4392b2494524d0e10ce3eb3723873afd1346b8b06e4"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)

def mainBlueberryProtocol4():
    benchmark = "BlueberryProtocol"
    contract = "0x649127d0800a8c68290129f091564ad2f1d62de1"
    l1 = []
    l2 = []
    l3 = [
        locator("borrow", FUNCTION, fromAddr="0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48", \
                name="transfer", position=1),
    ]
    enterFunction = []
    exitFunction = ["borrow"]
    exploitTx = "0xf0464b01d962f714eee9d4392b2494524d0e10ce3eb3723873afd1346b8b06e4"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)

def mainBlueberryProtocol5():
    benchmark = "BlueberryProtocol"
    contract = "0xe61ad5b0e40c856e6c193120bd3fa28a432911b6"
    l1 = []
    l2 = []
    l3 = [
        locator("borrow", FUNCTION, fromAddr="0x2260fac5e5542a773aa44fbcfedf7c193bc2c599", \
                name="transfer", position=1),
    ]
    enterFunction = []
    exitFunction = ["borrow"]
    exploitTx = "0xf0464b01d962f714eee9d4392b2494524d0e10ce3eb3723873afd1346b8b06e4"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)

def mainUwULend1():
    benchmark = "UwULend"
    contract = "0x2409af0251dcb89ee3dee572629291f9b087c668"
    l1 = [
        locator("deposit", FUNCTION, fromAddr="0x2260fac5e5542a773aa44fbcfedf7c193bc2c599", \
                name="transferFrom", position=2),
        locator("deposit", FUNCTION, fromAddr="0x6b175474e89094c44da98b954eedeac495271d0f", \
                name="transferFrom", position=2),
        locator("deposit", FUNCTION, fromAddr="0x9d39a5de30e57443bff2a8307a4256c8797a3497", \
                name="transferFrom", position=2),
        locator("deposit", FUNCTION, fromAddr="0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", \
                name="transferFrom", position=2),
        locator("deposit", FUNCTION, fromAddr="0xf1293141fc6ab23b2a0143acc196e3429e0b67a6", \
                name="transferFrom", position=2),
    ]
    l2 = []
    l3 = [
        locator("borrow", FUNCTION, fromAddr="0xf1293141fc6ab23b2a0143acc196e3429e0b67a6", \
                name="transferUnderlyingTo", position=1),
        locator("borrow", FUNCTION, fromAddr="0x67fadbd9bf8899d7c578db22d7af5e2e500e13e5", \
                name="transferUnderlyingTo", position=1),
        locator("withdraw", FUNCTION, fromAddr="0x67fadbd9bf8899d7c578db22d7af5e2e500e13e5", \
                name="burn", position=2),
        locator("withdraw", FUNCTION, fromAddr="0xf1293141fc6ab23b2a0143acc196e3429e0b67a6", \
                name="burn", position=2),        
    ]
    enterFunction = ["deposit"]
    exitFunction = ["borrow", "withdraw"]
    exploitTx = "0x242a0fb4fde9de0dc2fd42e8db743cbc197ffa2bf6a036ba0bba303df296408b"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)
    # SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))    
    # path = SCRIPT_DIR + "/newBenchmarks/" + benchmark + "/Txs/" + exploitTx + ".json.gz"
    # DataSourceMapList, accessList, splitedTraceTree = analyzeOneTx(contract, exploitTx, path, l1, l2, l3)        
    # print(DataSourceMapList)
    # print(accessList)
    # print(splitedTraceTree)

def mainPrismaFi1():
    benchmark = "PrismaFi"
    contract = "0x4591dbff62656e7859afe5e45f6f47d3669fbb28"
    l1 = []
    l2 = []
    l3 = []
    enterFunction = []
    exitFunction = []
    exploitTx = "0x00c503b595946bccaea3d58025b5f9b3726177bbdc9674e634244135282116c7"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)

def mainPrismaFi2():
    benchmark = "PrismaFi"
    contract = "0xcc7218100da61441905e0c327749972e3cbee9ee"
    l1 = []
    l2 = []
    l3 = []
    enterFunction = []
    exitFunction = []
    exploitTx = "0x00c503b595946bccaea3d58025b5f9b3726177bbdc9674e634244135282116c7"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)

def mainPrismaFi3():
    benchmark = "PrismaFi"
    contract = "0x72c590349535ad52e6953744cb2a36b409542719"
    l1 = [
        locator("openTrove", FUNCTION, fromAddr="0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0", \
                name="transferFrom", position=2),
    ]
    l2 = []
    l3 = [
        locator("closeTrove", FUNCTION, fromAddr="0x1cc79f3f47bfc060b6f761fcd1afc6d399a968b6", \
                name="closeTrove", position=2),
    ]
    enterFunction = ["openTrove"]
    exitFunction = ["closeTrove"]
    exploitTx = "0x00c503b595946bccaea3d58025b5f9b3726177bbdc9674e634244135282116c7"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)

def mainPikeFinance():
    benchmark = "PikeFinance"
    contract = "0xfc7599cffea9de127a9f9c748ccb451a34d2f063"
    l1 = []
    l2 = []
    l3 = []
    enterFunction = []
    exitFunction = []
    exploitTx = "0xe2912b8bf34d561983f2ae95f34e33ecc7792a2905a3e317fcc98052bce66431"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)

def mainOnyxDAO1():
    benchmark = "OnyxDAO"
    contract = "0x2ccb7d00a9e10d0c3408b5eefb67011abfacb075"
    l1 = [
        locator("mint", SELFCALLVALUE),
    ]
    l2 = []
    l3 = [
        locator("borrow", FALLBACK),
    ]
    enterFunction = []
    exitFunction = []
    exploitTx = "0x46567c731c4f4f7e27c4ce591f0aebdeb2d9ae1038237a0134de7b13e63d8729"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)

def mainOnyxDAO2():
    benchmark = "OnyxDAO"
    contract = "0xcc53f8ff403824a350885a345ed4da649e060369"
    l1 = []
    l2 = []
    l3 = []
    enterFunction = []
    exitFunction = []
    exploitTx = "0x46567c731c4f4f7e27c4ce591f0aebdeb2d9ae1038237a0134de7b13e63d8729"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)

def mainOnyxDAO3():
    benchmark = "OnyxDAO"
    contract = "0xa2cd3d43c775978a96bdbf12d733d5a1ed94fb18"
    l1 = []
    l2 = []
    l3 = []
    enterFunction = []
    exitFunction = []
    exploitTx = "0x46567c731c4f4f7e27c4ce591f0aebdeb2d9ae1038237a0134de7b13e63d8729"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)

def mainOnyxDAO4():
    benchmark = "OnyxDAO"
    contract = "0xf3354d3e288ce599988e23f9ad814ec1b004d74a"
    l1 = []
    l2 = []
    l3 = [
        locator("borrow", FUNCTION, fromAddr="0x6b175474e89094c44da98b954eedeac495271d0f", \
                name="transfer", position=1),
    ]
    enterFunction = []
    exitFunction = ["borrow"]
    exploitTx = "0x46567c731c4f4f7e27c4ce591f0aebdeb2d9ae1038237a0134de7b13e63d8729"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)

def mainOnyxDAO5():
    benchmark = "OnyxDAO"
    contract = "0x7a89e16cc48432917c948437ac1441b78d133a16"
    l1 = []
    l2 = []
    l3 = [
        locator("borrow", FUNCTION, fromAddr="0x2260fac5e5542a773aa44fbcfedf7c193bc2c599", \
                name="transfer", position=1),
    ]
    enterFunction = []
    exitFunction = ["borrow"]
    exploitTx = "0x46567c731c4f4f7e27c4ce591f0aebdeb2d9ae1038237a0134de7b13e63d8729"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)

def mainOnyxDAO6():
    benchmark = "OnyxDAO"
    contract = "0x2c6650126b6e0749f977d280c98415ed05894711"
    l1 = []
    l2 = []
    l3 = [
        locator("borrow", FUNCTION, fromAddr="0xdac17f958d2ee523a2206206994597c13d831ec7", \
                name="transfer", position=1),
    ]
    enterFunction = []
    exitFunction = ["borrow"]
    exploitTx = "0x46567c731c4f4f7e27c4ce591f0aebdeb2d9ae1038237a0134de7b13e63d8729"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)

def mainOnyxDAO7():
    benchmark = "OnyxDAO"
    contract = "0xee894c051c402301bc19be46c231d2a8e38b0451"
    l1 = []
    l2 = []
    l3 = [
        locator("borrow", FUNCTION, fromAddr="0xee894c051c402301bc19be46c231d2a8e38b0451", \
                name="transfer", position=1),
    ]
    enterFunction = []
    exitFunction = ["borrow"]
    exploitTx = "0x46567c731c4f4f7e27c4ce591f0aebdeb2d9ae1038237a0134de7b13e63d8729"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)




def mainAuctus():
    benchmark = "Auctus"
    contract = "0xe7597f774fd0a15a617894dc39d45a28b97afa4f"
    l1 = [
        locator("write", FUNCTION, fromAddr="0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48", \
                name="transferFrom", position=2),
    ]
    l2 = []
    l3 = []
    enterFunction = []
    exitFunction = []
    exploitTx = "0x2e7d7e7a6eb157b98974c8687fbd848d0158d37edc1302ea08ee5ddb376befea"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)
    # SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))    
    # path = SCRIPT_DIR + "/newBenchmarks/" + benchmark + "/Txs/" + exploitTx + ".json.gz"
    # DataSourceMapList, accessList, splitedTraceTree = analyzeOneTx(contract, exploitTx, path, l1, l2, l3)        
    # print(DataSourceMapList)
    # print(accessList)
    # print(splitedTraceTree)

def mainAudius1():
    benchmark = "Audius"
    contract = "0x4deca517d6817b6510798b7328f2314d3003abac"
    # 0x35dd16dfa4ea1522c29ddd087e8f076cad0ae5e8
    l1 = []
    l2 = []
    l3 = []
    enterFunction = []
    exitFunction = []
    exploitTx = "0xfefd829e246002a8fd061eede7501bccb6e244a9aacea0ebceaecef5d877a984"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)
    # SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))    
    # path = SCRIPT_DIR + "/newBenchmarks/" + benchmark + "/Txs/" + exploitTx + ".json.gz"
    # DataSourceMapList, accessList, splitedTraceTree = analyzeOneTx(contract, exploitTx, path, l1, l2, l3)        
    # print(DataSourceMapList)
    # print(accessList)
    # print(splitedTraceTree)


def mainAudius2():
    benchmark = "Audius"
    contract = "0xe6d97b2099f142513be7a2a068be040656ae4591"
    # 0xea10fd3536fce6a5d40d55c790b96df33b26702f
    l1 = []
    l2 = []
    l3 = []
    enterFunction = []
    exitFunction = []
    exploitTx = "0xfefd829e246002a8fd061eede7501bccb6e244a9aacea0ebceaecef5d877a984"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)
    # SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))    
    # path = SCRIPT_DIR + "/newBenchmarks/" + benchmark + "/Txs/" + exploitTx + ".json.gz"
    # DataSourceMapList, accessList, splitedTraceTree = analyzeOneTx(contract, exploitTx, path, l1, l2, l3)        
    # print(DataSourceMapList)
    # print(accessList)
    # print(splitedTraceTree)


def mainAudius3():
    benchmark = "Audius"
    contract = "0x4d7968ebfd390d5e7926cb3587c39eff2f9fb225"
    # 0xf24aeab628493f82742db68596b532ab8a141057
    l1 = []
    l2 = []
    l3 = []
    enterFunction = []
    exitFunction = []
    exploitTx = "0xfefd829e246002a8fd061eede7501bccb6e244a9aacea0ebceaecef5d877a984"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)
    # SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))    
    # path = SCRIPT_DIR + "/newBenchmarks/" + benchmark + "/Txs/" + exploitTx + ".json.gz"
    # DataSourceMapList, accessList, splitedTraceTree = analyzeOneTx(contract, exploitTx, path, l1, l2, l3)        
    # print(DataSourceMapList)
    # print(accessList)
    # print(splitedTraceTree)


def mainBaconProtocol():
    benchmark = "BaconProtocol"
    contract = "0xb8919522331c59f5c16bdfaa6a121a6e03a91f62"
    l1 = [
        locator("lend", FUNCTION, fromAddr="0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48", \
                name="transferFrom", position=2),
    ]
    l2 = []
    l3 = [
        locator("redeem", FUNCTION, fromAddr="0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48", \
                name="transfer", position=1),
    ]
    enterFunction = []
    exitFunction = []
    exploitTx = "0x7d2296bcb936aa5e2397ddf8ccba59f54a178c3901666b49291d880369dbcf31"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)
    # SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))    
    # path = SCRIPT_DIR + "/newBenchmarks/" + benchmark + "/Txs/" + exploitTx + ".json.gz"
    # DataSourceMapList, accessList, splitedTraceTree = analyzeOneTx(contract, exploitTx, path, l1, l2, l3)        
    # print(DataSourceMapList)
    # print(accessList)
    # print(splitedTraceTree)


def mainMetaSwap1():
    benchmark = "MetaSwap"
    contract = "0x824dcd7b044d60df2e89b1bb888e66d8bcf41491"
    # 0x88cc4aa0dd6cf126b00c012dda9f6f4fd9388b17
    l1 = [
        locator("swap", FUNCTION, fromAddr="0x57ab1ec28d129707052df4df418d58a2d46d5f51", \
                name="transferFrom,", position=1),
        locator("swap", FUNCTION, fromAddr="0x5f86558387293b6009d7896a61fcc86c17808d62", \
                name="transferFrom,", position=1),
        locator("swap", FUNCTION, fromAddr="", \
                name="transferFrom,", position=1),
        locator("swap", FUNCTION, fromAddr="", \
                name="transferFrom,", position=1),     
    ]
    l2 = []
    l3 = [
        locator("swap", FUNCTION, fromAddr="0x5f86558387293b6009d7896a61fcc86c17808d62", \
                name="transfer", position=1),
        locator("swap", FUNCTION, fromAddr="0x57ab1ec28d129707052df4df418d58a2d46d5f51", \
                name="transfer", position=1),
        locator("swap", FUNCTION, fromAddr="", \
                name="transfer", position=1),
    ]
    enterFunction = []
    exitFunction = []
    exploitTx = "0x2b023d65485c4bb68d781960c2196588d03b871dc9eb1c054f596b7ca6f7da56"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)
    # SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))    
    # path = SCRIPT_DIR + "/newBenchmarks/" + benchmark + "/Txs/" + exploitTx + ".json.gz"
    # DataSourceMapList, accessList, splitedTraceTree = analyzeOneTx(contract, exploitTx, path, l1, l2, l3)        
    # print(DataSourceMapList)
    # print(accessList)
    # print(splitedTraceTree)



def mainMetaSwap2():
    benchmark = "MetaSwap"
    contract = "0xacb83e0633d6605c5001e2ab59ef3c745547c8c7"
    # 0xc68bf77e33f1df59d8247dd564da4c8c81519db6
    l1 = [
        locator("removeLiquidity", FUNCTION, fromAddr="0x5f86558387293b6009d7896a61fcc86c17808d62", \
                name="burnFrom", position=1),
    ]
    l2 = []
    l3 = [
        locator("removeLiquidity", FUNCTION, fromAddr="0x6b175474e89094c44da98b954eedeac495271d0f", \
                name="transfer", position=1),
        locator("removeLiquidity", FUNCTION, fromAddr="0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48", \
                name="transfer", position=1),
        locator("removeLiquidity", FUNCTION, fromAddr="0xdac17f958d2ee523a2206206994597c13d831ec7", \
                name="transfer", position=1),
    ]
    enterFunction = []
    exitFunction = []
    exploitTx = "0x2b023d65485c4bb68d781960c2196588d03b871dc9eb1c054f596b7ca6f7da56"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)
    # SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))    
    # path = SCRIPT_DIR + "/newBenchmarks/" + benchmark + "/Txs/" + exploitTx + ".json.gz"
    # DataSourceMapList, accessList, splitedTraceTree = analyzeOneTx(contract, exploitTx, path, l1, l2, l3)        
    # print(DataSourceMapList)
    # print(accessList)
    # print(splitedTraceTree)


def mainMetaSwap3():
    benchmark = "MetaSwap"
    contract = "0x5f86558387293b6009d7896A61fcc86C17808D62"
    # 0x59f5a371df7d2a01863cbb011a5a1ed45326710c
    l1 = []
    l2 = []
    l3 = []
    enterFunction = []
    exitFunction = []
    exploitTx = "0x2b023d65485c4bb68d781960c2196588d03b871dc9eb1c054f596b7ca6f7da56"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)
    # SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))    
    # path = SCRIPT_DIR + "/newBenchmarks/" + benchmark + "/Txs/" + exploitTx + ".json.gz"
    # DataSourceMapList, accessList, splitedTraceTree = analyzeOneTx(contract, exploitTx, path, l1, l2, l3)        
    # print(DataSourceMapList)
    # print(accessList)
    # print(splitedTraceTree)



def mainMonoXFi1():
    benchmark = "MonoXFi"
    contract = "0x2920f7d6134f4669343e70122ca9b8f19ef8fa5d"
    l1 = []
    l2 = []
    l3 = []
    enterFunction = []
    exitFunction = []
    exploitTx = "0x9f14d093a2349de08f02fc0fb018dadb449351d0cdb7d0738ff69cc6fef5f299"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)
    # SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))    
    # path = SCRIPT_DIR + "/newBenchmarks/" + benchmark + "/Txs/" + exploitTx + ".json.gz"
    # DataSourceMapList, accessList, splitedTraceTree = analyzeOneTx(contract, exploitTx, path, l1, l2, l3)        
    # print(DataSourceMapList)
    # print(accessList)
    # print(splitedTraceTree)



def mainMonoXFi2():
    benchmark = "MonoXFi"
    contract = "0xc36a7887786389405ea8da0b87602ae3902b88a1"
    # 0x66e7d7839333f502df355f5bd87aea24bac2ee63
    l1 = [
        locator("swapExactTokenForToken", FUNCTION, fromAddr="0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", \
                name="transferFrom", position=2),
        locator("addLiquidity", FUNCTION, fromAddr="0x2920f7d6134f4669343e70122ca9b8f19ef8fa5d", \
                name="transferFrom", position=2),
    ]
    l2 = []
    l3 = [
        locator("swapExactTokenForToken", FUNCTION, fromAddr="0x59653e37f8c491c3be36e5dd4d503ca32b5ab2f4", \
                name="safeTransferERC20Token", position=2),
        locator("removeLiquidity", FUNCTION, fromAddr="0x59653e37f8c491c3be36e5dd4d503ca32b5ab2f4", \
                name="safeTransferERC20Token", position=2),
    ]
    enterFunction = []
    exitFunction = []
    exploitTx = "0x9f14d093a2349de08f02fc0fb018dadb449351d0cdb7d0738ff69cc6fef5f299"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)
    # SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))    
    # path = SCRIPT_DIR + "/newBenchmarks/" + benchmark + "/Txs/" + exploitTx + ".json.gz"
    # DataSourceMapList, accessList, splitedTraceTree = analyzeOneTx(contract, exploitTx, path, l1, l2, l3)        
    # print(DataSourceMapList)
    # print(accessList)
    # print(splitedTraceTree)

def mainMonoXFi3():
    benchmark = "MonoXFi"
    contract = "0x59653e37f8c491c3be36e5dd4d503ca32b5ab2f4"
    # 0x7164be9fd69f2e1de9b6b75b17e1b86268f18b45
    l1 = []
    l2 = []
    l3 = []
    enterFunction = []
    exitFunction = []
    exploitTx = "0x9f14d093a2349de08f02fc0fb018dadb449351d0cdb7d0738ff69cc6fef5f299"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)
    # SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))    
    # path = SCRIPT_DIR + "/newBenchmarks/" + benchmark + "/Txs/" + exploitTx + ".json.gz"
    # DataSourceMapList, accessList, splitedTraceTree = analyzeOneTx(contract, exploitTx, path, l1, l2, l3)        
    # print(DataSourceMapList)
    # print(accessList)
    # print(splitedTraceTree)



def mainMonoXFi4():
    benchmark = "MonoXFi"
    contract = "0x532d7ebe4556216490c9d03460214b58e4933454"
    l1 = []
    l2 = []
    l3 = []
    enterFunction = []
    exitFunction = []
    exploitTx = "0x9f14d093a2349de08f02fc0fb018dadb449351d0cdb7d0738ff69cc6fef5f299"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)
    # SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))    
    # path = SCRIPT_DIR + "/newBenchmarks/" + benchmark + "/Txs/" + exploitTx + ".json.gz"
    # DataSourceMapList, accessList, splitedTraceTree = analyzeOneTx(contract, exploitTx, path, l1, l2, l3)        
    # print(DataSourceMapList)
    # print(accessList)
    # print(splitedTraceTree)



def mainNowSwap():
    benchmark = "NowSwap"
    contract = "0x9536a78440f72f5e9612949f1848fe5e9d4934cc"
    l1 = []
    l2 = []
    l3 = [
        locator("swap", FUNCTION, fromAddr="0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", \
                name="transfer", position=1),
        locator("swap", FUNCTION, fromAddr="0xdac17f958d2ee523a2206206994597c13d831ec7", \
                name="transfer", position=1),

    ]
    enterFunction = []
    exitFunction = []
    exploitTx = "0xf3158a7ea59586c5570f5532c22e2582ee9adba2408eabe61622595197c50713"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)
    # SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))    
    # path = SCRIPT_DIR + "/newBenchmarks/" + benchmark + "/Txs/" + exploitTx + ".json.gz"
    # DataSourceMapList, accessList, splitedTraceTree = analyzeOneTx(contract, exploitTx, path, l1, l2, l3)        
    # print(DataSourceMapList)
    # print(accessList)
    # print(splitedTraceTree)



def mainOmniNFT1():
    benchmark = "OmniNFT"
    contract = "0x218615c78104e16b5f17764d35b905b638fe4a92"
    # 0x4e21f48add00e579b774cdad1656c6625c280381
    l1 = []
    l2 = []
    l3 = []
    enterFunction = []
    exitFunction = []
    exploitTx = "0x264e16f4862d182a6a0b74977df28a85747b6f237b5e229c9a5bbacdf499ccb4"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)
    # SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))    
    # path = SCRIPT_DIR + "/newBenchmarks/" + benchmark + "/Txs/" + exploitTx + ".json.gz"
    # DataSourceMapList, accessList, splitedTraceTree = analyzeOneTx(contract, exploitTx, path, l1, l2, l3)        
    # print(DataSourceMapList)
    # print(accessList)
    # print(splitedTraceTree)



def mainOmniNFT2():
    benchmark = "OmniNFT"
    contract = "0xebe72cdafebc1abf26517dd64b28762df77912a9"
    # 0x50c7a557d408a5f5a7fdbe1091831728ae7eba45
    l1 = []
    l2 = []
    l3 = []
    enterFunction = []
    exitFunction = []
    exploitTx = "0x264e16f4862d182a6a0b74977df28a85747b6f237b5e229c9a5bbacdf499ccb4"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)
    # SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))    
    # path = SCRIPT_DIR + "/newBenchmarks/" + benchmark + "/Txs/" + exploitTx + ".json.gz"
    # DataSourceMapList, accessList, splitedTraceTree = analyzeOneTx(contract, exploitTx, path, l1, l2, l3)        
    # print(DataSourceMapList)
    # print(accessList)
    # print(splitedTraceTree)


def mainPopsicleFi1():
    benchmark = "PopsicleFi"
    contract = "0xc4ff55a4329f84f9bf0f5619998ab570481ebb48"
    l1 = [

    ]
    l2 = []
    l3 = [
        locator("withdraw", FUNCTION, fromAddr="0x4e68ccd3e89f51c3074ca5072bbac773960dfa36", \
                name="collect", position=3),
    ]
    enterFunction = []
    exitFunction = []
    exploitTx = "0xcd7dae143a4c0223349c16237ce4cd7696b1638d116a72755231ede872ab70fc"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)
    # SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))    
    # path = SCRIPT_DIR + "/newBenchmarks/" + benchmark + "/Txs/" + exploitTx + ".json.gz"
    # DataSourceMapList, accessList, splitedTraceTree = analyzeOneTx(contract, exploitTx, path, l1, l2, l3)        
    # print(DataSourceMapList)
    # print(accessList)
    # print(splitedTraceTree)


def mainPopsicleFi2():
    benchmark = "PopsicleFi"
    contract = "0xd63b340f6e9cccf0c997c83c8d036fa53b113546"
    l1 = []
    l2 = []
    l3 = []
    enterFunction = []
    exitFunction = []
    exploitTx = "0xcd7dae143a4c0223349c16237ce4cd7696b1638d116a72755231ede872ab70fc"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)
    # SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))    
    # path = SCRIPT_DIR + "/newBenchmarks/" + benchmark + "/Txs/" + exploitTx + ".json.gz"
    # DataSourceMapList, accessList, splitedTraceTree = analyzeOneTx(contract, exploitTx, path, l1, l2, l3)        
    # print(DataSourceMapList)
    # print(accessList)
    # print(splitedTraceTree)


def mainPopsicleFi3():
    benchmark = "PopsicleFi"
    contract = "0xb53dc33bb39efe6e9db36d7ef290d6679facbec7"
    l1 = []
    l2 = []
    l3 = []
    enterFunction = []
    exitFunction = []
    exploitTx = "0xcd7dae143a4c0223349c16237ce4cd7696b1638d116a72755231ede872ab70fc"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)
    # SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))    
    # path = SCRIPT_DIR + "/newBenchmarks/" + benchmark + "/Txs/" + exploitTx + ".json.gz"
    # DataSourceMapList, accessList, splitedTraceTree = analyzeOneTx(contract, exploitTx, path, l1, l2, l3)        
    # print(DataSourceMapList)
    # print(accessList)
    # print(splitedTraceTree)





def mainPopsicleFi4():
    benchmark = "PopsicleFi"
    contract = "0x6f3f35a268b3af45331471eabf3f9881b601f5aa"
    l1 = []
    l2 = []
    l3 = []
    enterFunction = []
    exitFunction = []
    exploitTx = "0xcd7dae143a4c0223349c16237ce4cd7696b1638d116a72755231ede872ab70fc"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)
    # SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))    
    # path = SCRIPT_DIR + "/newBenchmarks/" + benchmark + "/Txs/" + exploitTx + ".json.gz"
    # DataSourceMapList, accessList, splitedTraceTree = analyzeOneTx(contract, exploitTx, path, l1, l2, l3)        
    # print(DataSourceMapList)
    # print(accessList)
    # print(splitedTraceTree)



def mainPopsicleFi5():
    benchmark = "PopsicleFi"
    contract = "0xdd90112eaf865e4e0030000803ebbb4d84f14617"
    l1 = []
    l2 = []
    l3 = []
    enterFunction = []
    exitFunction = []
    exploitTx = "0xcd7dae143a4c0223349c16237ce4cd7696b1638d116a72755231ede872ab70fc"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)
    # SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))    
    # path = SCRIPT_DIR + "/newBenchmarks/" + benchmark + "/Txs/" + exploitTx + ".json.gz"
    # DataSourceMapList, accessList, splitedTraceTree = analyzeOneTx(contract, exploitTx, path, l1, l2, l3)        
    # print(DataSourceMapList)
    # print(accessList)
    # print(splitedTraceTree)



def mainPopsicleFi6():
    benchmark = "PopsicleFi"
    contract = "0xe22eacac57a1adfa38dca1100ef17654e91efd35"
    l1 = []
    l2 = []
    l3 = []
    enterFunction = []
    exitFunction = []
    exploitTx = "0xcd7dae143a4c0223349c16237ce4cd7696b1638d116a72755231ede872ab70fc"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)
    # SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))    
    # path = SCRIPT_DIR + "/newBenchmarks/" + benchmark + "/Txs/" + exploitTx + ".json.gz"
    # DataSourceMapList, accessList, splitedTraceTree = analyzeOneTx(contract, exploitTx, path, l1, l2, l3)        
    # print(DataSourceMapList)
    # print(accessList)
    # print(splitedTraceTree)








# For invariant OB, we need to mark enter function and exit function, 
# For invariant DFU, don't need to do any thing

def mainTest():
    benchmark = "Punk_1"
    contract = "0x3BC6aA2D25313ad794b2D67f83f21D341cc3f5fb"
    # The followings are a list of locators for locating the external call functions inside the target contract that are related to deposit, invest, and withdraw
    # This is used for dataFlow invariant inference of Trace2Inv
    # a locator is used to define where a transfer happens
    # l1: deposit locator - when a user deposits their funds into the contract
    # l2: invest locator - when the contract invests the funds to another DeFi protocol
    # l3: withdraw locator - when a user withdraws their funds from the contract
    l1 = []
    l2 = []
    l3 = [
        locator("withdrawTo", FUNCTION, fromAddr = "0x3bc6aa2d25313ad794b2d67f83f21d341cc3f5fb", funcAddress = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48", \
            name="transfer", position=1),
        locator("withdrawToForge", FUNCTION, fromAddr = "0x3bc6aa2d25313ad794b2d67f83f21d341cc3f5fb", funcAddress = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48", \
            name="transfer", position=1),
    ]
    enterFunction = []
    exitFunction = ['withdrawAllToForge', 'withdrawTo', 'withdrawToForge']
    exploitTx = "0x597d11c05563611cb4ad4ed4c57ca53bbe3b7d3fefc37d1ef0724ad58904742b"
    mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFunction, exitFunction)


#  0x9d373e78a0ad96b50cb8c51b44cc76406c06f467c321c3fc8136e444c8d1a1f2
# recollect 
def mainContract(benchmark, contract, l1, l2, l3, exploitTx, enterFuncs, exitFuncs, useCache = False, reCollect = True):
    print("now works on benchmark: ", benchmark, " contract: ", contract)
    
    # Step 1: Collect transactions
    # Step 1.1: Collect transaction history using TrueBlocks
    contract2txHashes = decodeTxlistForBenchmark(benchmark)
    if contract not in contract2txHashes:
        sys.exit("contract not in contract2txHashes")
    txHashes = contract2txHashes[contract]

    print("total transactions: ", len(txHashes))

    # Step 1.2: Download history transaction traces from QuickNode
    # for tx in txHashes:
    #     storeATrace(tx)    
    pathList = []
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    for ii, tx in enumerate(txHashes):
        path = SCRIPT_DIR + "/newBenchmarks/" + benchmark + "/Txs/" + tx + ".json.gz"
        if os.path.exists(path):
            pathList.append(path)
        else:
            txHashes[ii] = None
            pathList.append(None)

    executionListTable = None
    accesslistTable = None

    if useCache:
        with open("cache/{}-{}/executionListTable.pkl".format(benchmark, contract), "rb") as f:
            executionListTable = pickle.load(f)
        with open("cache/{}-{}/accesslistTable.pkl".format(benchmark, contract), "rb") as f:
            accesslistTable = pickle.load(f)

    else:    
        # Step 2: Parse the transactions and Collect Invariant Related Data
        # Suppose target contract is A
        # LoggingUpperBound set to x means
        # starting from A's depth a, all functions calls of depth a+x will be logged
        # changeLoggingUpperBound(8) 
        # create folders for storing cached invariant-related data
        path1 = SCRIPT_DIR + "/cache/" + contract
        path2 = SCRIPT_DIR + "/cache/" + contract + "_Access"
        path3 = SCRIPT_DIR + "/cache/" + contract + "_SplitedTraceTree"
        for path in [path1, path2, path3]:
            if not os.path.exists(path):
                os.makedirs(path)
        
        print("total: ", len(txHashes))
        # The following code extracts invariant-related data from the transactions
        for ii in range(len(txHashes)):
            if readAccessList(contract, txHashes[ii]) != []:
                continue
            # print("now finish: ", ii, " total: ", len(txHashes))
            if txHashes[ii] is None:
                continue
            
            if reCollect:
                if txHashes[ii] == "0x9d373e78a0ad96b50cb8c51b44cc76406c06f467c321c3fc8136e444c8d1a1f2" or \
                    txHashes[ii] == "0x28492fdcffa1882462d7e670cbee6e33b7f65ad45fbc0b81906bc2d31674c8a8" or \
                    txHashes[ii] == "0xb648fb50749a32b293d8cd8dad7ec52b1e3df889643c84a69e53413899c4a0de" or \
                    txHashes[ii] == "0x64a134c3255212609482a294223501365b6e643ff321b895f0eb15fd32c6ad2e" or \
                    txHashes[ii] == "0xc05619a3ea4de1d8bd7f98dc24b3e44b24242aab09dec21996ff8cadae932eb6" or \
                    txHashes[ii] == "0x4a4862539fa57f1b55760bd69c5d48dd331093959307547a8d63fb85a56e99b7" or \
                    txHashes[ii] == "0x893b6746027bd7270bd9b858fe3b55221fcd8610d9086641330e789146e80b5d":
                    continue 
                    
                print("now finish: ", ii, " total: ", len(txHashes), " tx: ", txHashes[ii])
                
                try:
                    dataSourceMapList, accessList, splitedTraceTree = analyzeOneTx(contract, txHashes[ii], pathList[ii], l1, l2, l3)        
                    writeDataSource(contract, txHashes[ii], dataSourceMapList)
                    writeAccessList(contract, txHashes[ii], accessList)
                    writeSplitedTraceTree(contract, txHashes[ii], splitedTraceTree)
                except Exception as e:
                    print(e, file=sys.stderr)
                    print("Some error happened when analyzing tx: {} path: {}".format(txHashes[ii], pathList[ii]), file=sys.stderr)

            # if ii > 1170:
            #     return
        
        accesslistTable = []
        accesslistList = []

        executionListTable = []
        executionListList = []
        
        # read the data source map list
        for ii in range( len(txHashes) ):
            if txHashes[ii] is None:
                continue
            accessList = readAccessList(contract, txHashes[ii])
            if len(accessList) > 0:
                accesslistList.append( (txHashes[ii], accessList) )
            if len(accessList) == 1 and len(accessList[0]) == 0:
                print("no access for tx: ", txHashes[ii]) 

            executionList = readDataSource(contract, txHashes[ii])
            if len(executionList) > 0 and len(executionList[0]) > 0:
                for execution in executionList[0]:
                    executionListList.append( (txHashes[ii], execution) )

        accesslistTable.append( (benchmark, contract, accesslistList, exploitTx) )
        executionListTable.append( (contract, executionListList) )

        if not os.path.exists("cache/{}-{}".format(benchmark, contract)):
            os.makedirs("cache/{}-{}".format(benchmark, contract))

        # store executionTable and accesslistTable
        with open("cache/{}-{}/executionListTable.pkl".format(benchmark, contract), "wb") as f:
            pickle.dump(executionListTable, f)
        with open("cache/{}-{}/accesslistTable.pkl".format(benchmark, contract), "wb") as f:
            pickle.dump(accesslistTable, f)


    # Invariant Category 1: Access Control
    print("=====================================================")
    print("=============== Access Control ======================")
    print("=====================================================")
    inferAccessControl(accesslistTable, len(txHashes))


    # Invariant Category 2: Time Locks
    print("=====================================================")
    print("=================== Time Locks ======================")
    print("=====================================================")
    # enterFuncs represent the functions that a user can deposit their funds into
    # exitFuncs represent the functions that a user can withdraw their funds from
    if len(enterFuncs) == 0 or len(exitFuncs) == 0:
        print("enterFuncs or exitFuncs is empty, so OB does not apply")
    else:
        inferTimeLocks(accesslistTable, enterFuncs, exitFuncs, len(txHashes))


    # Invariant Category 3: Gas Control
    print("=====================================================")
    print("=================== Gas Control =====================")
    print("=====================================================")
    inferGasControl(accesslistTable, len(txHashes))


    executionListTable = reformatExecutionTable(executionListTable)
    # Invariant Category 7: DataFlow
    print("=====================================================")
    print("=================== DataFlow ========================")
    print("=====================================================")
    trainTxList = txHashes[:int(0.7 * len(txHashes))]
    inferDataFlows(executionListTable, enterFuncs, exitFuncs, len(txHashes), trainTxList, benchmark, exploitTx)





if __name__ == '__main__':
    # mainTestIndividual()
    # mainPrismaFi1()
    # mainPrismaFi2()
    # mainPrismaFi3()

    # mainPrismaFi1()
    # mainOnyxDAO3()
    # mainPrismaFi3()


    # # # read an argument from command line to specify the benchmark
    # if len(sys.argv) != 2:
    #    sys.exit("Usage: python3 main.py <benchmark>")
    # benchmark = sys.argv[1]
    # print("benchmark: ", benchmark) 
    # # execute function "main" + benchmark + "()"
    # eval("main" + benchmark + "()")

    # mainDoughFina1()
    # mainDoughFina2()  # does not support implementation of implementation of a proxy

    # mainBedrock_DeFi1()
    # mainBedrock_DeFi2()

    # mainGFOX1()
    # mainGFOX2()

    # mainBlueberryProtocol1()
    # mainBlueberryProtocol2()
    # mainBlueberryProtocol3()
    # mainBlueberryProtocol4()
    # mainBlueberryProtocol5()

    # mainUwULend1()

    # mainPrismaFi1()
    # mainPrismaFi2()
    # mainPrismaFi3()

    # # cProfile.run('mainPikeFinance()', sort='cumtime')

    # mainPikeFinance()

    # mainOnyxDAO1()
    # mainOnyxDAO2()
    # mainOnyxDAO4()
    # mainOnyxDAO5()
    # mainOnyxDAO6()
    # mainOnyxDAO7()

    
    # # mainTest()
    # # mainTestTime()

    # For major revision
    # mainAuctus()
    # mainAudius1()
    # mainAudius2()
    # mainAudius3()
    # mainBaconProtocol()
    # mainMetaSwap1()
    # mainMetaSwap2()
    # mainMetaSwap3()
    # mainMonoXFi1()
    mainMonoXFi2() # has some problems. 
    mainMonoXFi3()
    mainMonoXFi4()
    mainNowSwap()
    mainOmniNFT1()
    mainOmniNFT2()
    mainPopsicleFi1()
    mainPopsicleFi2()
    mainPopsicleFi3()
    mainPopsicleFi4()
    mainPopsicleFi5()   














