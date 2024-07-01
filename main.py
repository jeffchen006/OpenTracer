import sys
import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

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

from TxSpectorTranslator.translator import TxSpectorTranslator


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







def mainTestTime():
    # Punk_1
    # hackTx = "0x597d11c05563611cb4ad4ed4c57ca53bbe3b7d3fefc37d1ef0724ad58904742b"
    contract = "0x3BC6aA2D25313ad794b2D67f83f21D341cc3f5fb"
    endBlock = 12995895

    start = time.time()
    # Step 1: Collect transactions
    # Step 1.1: Collect transaction history using TrueBlocks
    txHashes = collectTransactionHistory(contract, endBlock)

    end = time.time()
    print("Time elapsed for collecting transaction history: ", end - start, "s")
    

    # Step 1.2: Download history transaction traces from QuickNode
    start = time.time()
    for tx in txHashes:
        storeATrace(tx)    
    pathList = []
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    for tx in txHashes:
        path = SCRIPT_DIR + "/cache/" + tx + ".json.gz"
        pathList.append(path)

    end = time.time()
    print("Time elapsed for downloading transaction traces: ", end - start, "s")


    changeLoggingUpperBound(1000)
    time.sleep(1)

    # Step 1: Fetch a transaction trace
    start = time.time()
    for txHash in txHashes:
        temp = readATrace(txHash)
        # Step 2: Parse the transaction trace
        SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
        path = SCRIPT_DIR + "/cache/" + txHash + ".json.gz"
        metaTraceTree =  analyzeOneTxGlobal(txHash, path)
        metaTraceTree.hideUnnecessaryInfo()

    end = time.time()
    print("Time elapsed for parsing transaction traces: ", end - start, "s")





    # Step 2: Parse the transactions and Collect Invariant Related Data
    start = time.time()
    # Suppose target contract is A
    # LoggingUpperBound set to x means
    # starting from A's depth a, all functions calls of depth a+x will be logged
    changeLoggingUpperBound(8) 

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
    # The following code extracts invariant-related data from the transactions
    for ii in range(len(txHashes)):
        # if readAccessList(contract, txHashes[ii]) != []:
        #     continue
        start = time.time()
        dataSourceMapList, accessList, splitedTraceTree = analyzeOneTx(contract, txHashes[ii], pathList[ii], l1, l2, l3)        
        writeDataSource(contract, txHashes[ii], dataSourceMapList)
        writeAccessList(contract, txHashes[ii], accessList)
        writeSplitedTraceTree(contract, txHashes[ii], splitedTraceTree)
        end = time.time() - start
        print("Time elapsed for analyzing tx: ", txHashes[ii], " ", end, "s")
    
    accesslistTable = []
    accesslistList = []

    executionListTable = []
    executionListList = []
    
    # Here we use 70% of the data as training data, same as in Trace2Inv Paper
    trainingSetSize = int(0.7 * len(txHashes))

    # read the data source map list
    for ii in range( len(txHashes) ):
        accessList = readAccessList(contract, txHashes[ii])
        if len(accessList) > 0:
            accesslistList.append( (txHashes[ii], accessList) )
        
        if len(accessList) == 1 and len(accessList[0]) == 0:
            print("no access for tx: ", txHashes[ii]) 
        

    accesslistTable.append( (contract, accesslistList) )


    # read the data source map list
    for ii in range( trainingSetSize ):
        executionList = readDataSource(contract, txHashes[ii])
        if len(executionList) > 0 and len(executionList[0]) > 0:
            for execution in executionList[0]:
                executionListList.append( (txHashes[ii], execution) )

    executionListTable.append( (contract, executionListList) )

    end = time.time() - start
    print("Time elapsed for extracting invariant-related data: ", end, "s")


    
    start = time.time()
    # Invariant Category 1: Access Control
    print("=====================================================")
    print("=============== Access Control ======================")
    print("=====================================================")
    inferAccessControl(accesslistTable)

    # Invariant Category 2: Time Locks
    print("=====================================================")
    print("=================== Time Locks ======================")
    print("=====================================================")

    # enterFuncs represent the functions that a user can deposit their funds into
    enterFuncs = []
    # exitFuncs represent the functions that a user can withdraw their funds from
    exitFuncs = ['withdrawAllToForge', 'withdrawTo', 'withdrawToForge']
    inferTimeLocks(accesslistTable, enterFuncs, exitFuncs)

    # Invariant Category 3: Gas Control
    print("=====================================================")
    print("=================== Gas Control =====================")
    print("=====================================================")
    inferGasControl(accesslistTable)

    # Invariant Category 4: Re-entrancy
    print("=====================================================")
    print("=================== Re-entrancy =====================")
    print("=====================================================")
    enterFuncs = []
    exitFuncs = ['withdrawAllToForge', 'withdrawTo', 'withdrawToForge']
    inferReentrancy(accesslistTable, enterFuncs, exitFuncs)

    # Invariant Category 5: Special Storage
    print("=====================================================")
    print("================ Special Storage ====================")
    print("=====================================================")
    inferSpecialStorage(accesslistTable)

    # Invariant Category 6: Oracle Control
    # Only the following benchmarks use an oracle
    # Punk_1 does not use an oracle, but the code is still here for reference
    # # benchmarks = ["bZx2", "Warp_interface", "CheeseBank_1", "CheeseBank_2", "CheeseBank_3", "InverseFi", \
    # #                 "CreamFi2_1", "CreamFi2_2", "CreamFi2_3", "CreamFi2_4", "Harvest1_fUSDT", "Harvest2_fUSDC", \
    # #                 "ValueDeFi"]
    # inferOracleRange(benchmarks)

    executionListTable = reformatExecutionTable(executionListTable)
    # Invariant Category 7: DataFlow
    print("=====================================================")
    print("=================== DataFlow ========================")
    print("=====================================================")
    enterFuncs = []
    exitFuncs = ['withdrawAllToForge', 'withdrawTo', 'withdrawToForge']
    inferDataFlows(executionListTable, enterFuncs, exitFuncs)

    # Invariant Category 8: MoneyFlow
    print("=====================================================")
    print("=================== MoneyFlow =======================")
    print("=====================================================")
    # transferToken is the token that is being transferred, which we try to restrict
    transferToken = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
    inferMoneyFlows(executionListTable, contract, transferToken) 

    end = time.time() - start
    print("Time elapsed for inferring invariants: ", end, "s")




    start = time.time()

    for txHash in txHashes:
        # step 2: read the trace and translate it to TxSpector desired format
        trace = readATrace(txHash)
        translated = TxSpectorTranslator().parseLogs(trace)

    end = time.time() - start
    print("Time elapsed for translating logs: ", end, "s")





def main():
    # Feature 0: Given a transaction hash, fetch and parse the transaction trace
    #feature0()

    # Feature 1: Given a target contract, collect all transactions related to the contract.
    # Collect all snippets of the transactions related to the target contract, collect invariant-related data, generate invariants
    # feature1()

  ##  feature3()
    collectTraceAndInvariants(contract="0xe952bda8c06481506e4731c4f54ced2d4ab81659", endBlock=14465357, l1=[], l2=[], l3=[])








def feature0():
    # ==========================================================================
    # Feature 0: Given a transaction hash, fetch and parse the transaction trace
    # ==========================================================================
    changeLoggingUpperBound(1000)
    # time.sleep(1)
    # Step 1: Fetch a transaction trace
    txHash = "0xed2e82bb59e2ea39bfdc7d08ae2f7fcad7200e00163f6e3440b9a5d72fc3ef5d"
    storeATrace(txHash)
    temp = readATrace(txHash)
    for ii in range(0, 10):
        print(temp['structLogs'][ii])

    # Step 2: Parse the transaction trace
    print("=================== Trace Tree =====================")
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    path = SCRIPT_DIR + "/cache/" + txHash + ".json.gz"
    metaTraceTree = analyzeOneTxGlobal(txHash, path)
    print(metaTraceTree.visualizeASE())

    # Step 3: Decode function ABI and Storage Accesses (dynamically track SHA3)
    print("=================== Decoded Trace Tree =====================")
    metaTraceTree.decodeABIStorage(temp['structLogs'])
    print(metaTraceTree.visualizeASE_decoded())

def feature1():
 # ==========================================================================
    # Feature 1: Given a target contract, collect all transactions related to the contract.
    #            Collect all snippets of the transactions related to the target contract and collect invariant-related data.
    # ==========================================================================
    # Punk_1
    # hackTx = "0x597d11c05563611cb4ad4ed4c57ca53bbe3b7d3fefc37d1ef0724ad58904742b"
    contract = "0x3BC6aA2D25313ad794b2D67f83f21D341cc3f5fb"
    endBlock = 12995895

    # Step 1: Collect transactions
    # Step 1.1: Collect transaction history using TrueBlocks
    txHashes = collectTransactionHistory(contract, endBlock)

    print("total transactions: ", len(txHashes))

    # Step 1.2: Download history transaction traces from QuickNode
    for tx in txHashes:
        storeATrace(tx)    
    pathList = []

    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    for tx in txHashes:
        path = SCRIPT_DIR + "/cache/" + tx + ".json.gz"
        pathList.append(path)


    # Step 2: Parse the transactions and Collect Invariant Related Data

    # Suppose target contract is A
    # LoggingUpperBound set to x means
    # starting from A's depth a, all functions calls of depth a+x will be logged
    changeLoggingUpperBound(8) 

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


    # create folders for storing cached invariant-related data
    path1 = SCRIPT_DIR + "/cache/" + contract
    path2 = SCRIPT_DIR + "/cache/" + contract + "_Access"
    path3 = SCRIPT_DIR + "/cache/" + contract + "_SplitedTraceTree"
    for path in [path1, path2, path3]:
        if not os.path.exists(path):
            os.makedirs(path)
    
    # The following code extracts invariant-related data from the transactions
    for ii in range(len(txHashes)):
        # if readAccessList(contract, txHashes[ii]) != []:
        #     continue
        dataSourceMapList, accessList, splitedTraceTree = analyzeOneTx(contract, txHashes[ii], pathList[ii], l1, l2, l3)        
        writeDataSource(contract, txHashes[ii], dataSourceMapList)
        writeAccessList(contract, txHashes[ii], accessList)
        writeSplitedTraceTree(contract, txHashes[ii], splitedTraceTree)
    
    accesslistTable = []
    accesslistList = []

    executionListTable = []
    executionListList = []
    
    # Here we use 70% of the data as training data, same as in Trace2Inv Paper
    trainingSetSize = int(0.7 * len(txHashes))

    # read the data source map list
    for ii in range( len(txHashes) ):
        accessList = readAccessList(contract, txHashes[ii])
        if len(accessList) > 0:
            accesslistList.append( (txHashes[ii], accessList) )
        
        if len(accessList) == 1 and len(accessList[0]) == 0:
            print("no access for tx: ", txHashes[ii]) 
        

    accesslistTable.append( (contract, accesslistList) )


    # read the data source map list
    for ii in range( trainingSetSize ):
        executionList = readDataSource(contract, txHashes[ii])
        if len(executionList) > 0 and len(executionList[0]) > 0:
            for execution in executionList[0]:
                executionListList.append( (txHashes[ii], execution) )

    executionListTable.append( (contract, executionListList) )


    
    # Invariant Category 1: Access Control
    print("=====================================================")
    print("=============== Access Control ======================")
    print("=====================================================")
    inferAccessControl(accesslistTable)

    # Invariant Category 2: Time Locks
    print("=====================================================")
    print("=================== Time Locks ======================")
    print("=====================================================")

    # enterFuncs represent the functions that a user can deposit their funds into
    enterFuncs = []
    # exitFuncs represent the functions that a user can withdraw their funds from
    exitFuncs = ['withdrawAllToForge', 'withdrawTo', 'withdrawToForge']
    inferTimeLocks(accesslistTable, enterFuncs, exitFuncs)

    # Invariant Category 3: Gas Control
    print("=====================================================")
    print("=================== Gas Control =====================")
    print("=====================================================")
    inferGasControl(accesslistTable)

    # Invariant Category 4: Re-entrancy
    print("=====================================================")
    print("=================== Re-entrancy =====================")
    print("=====================================================")
    enterFuncs = []
    exitFuncs = ['withdrawAllToForge', 'withdrawTo', 'withdrawToForge']
    inferReentrancy(accesslistTable, enterFuncs, exitFuncs)

    # Invariant Category 5: Special Storage
    print("=====================================================")
    print("================ Special Storage ====================")
    print("=====================================================")
    inferSpecialStorage(accesslistTable)

    # Invariant Category 6: Oracle Control
    # Only the following benchmarks use an oracle
    # Punk_1 does not use an oracle, but the code is still here for reference
    # # benchmarks = ["bZx2", "Warp_interface", "CheeseBank_1", "CheeseBank_2", "CheeseBank_3", "InverseFi", \
    # #                 "CreamFi2_1", "CreamFi2_2", "CreamFi2_3", "CreamFi2_4", "Harvest1_fUSDT", "Harvest2_fUSDC", \
    # #                 "ValueDeFi"]
    # inferOracleRange(benchmarks)

    executionListTable = reformatExecutionTable(executionListTable)
    # Invariant Category 7: DataFlow
    print("=====================================================")
    print("=================== DataFlow ========================")
    print("=====================================================")
    enterFuncs = []
    exitFuncs = ['withdrawAllToForge', 'withdrawTo', 'withdrawToForge']
    inferDataFlows(executionListTable, enterFuncs, exitFuncs)

    # Invariant Category 8: MoneyFlow
    print("=====================================================")
    print("=================== MoneyFlow =======================")
    print("=====================================================")
    # transferToken is the token that is being transferred, which we try to restrict
    transferToken = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
    inferMoneyFlows(executionListTable, contract, transferToken) 






def collectTraceAndInvariants(contract, endBlock, l1 ,l2, l3):
    changeLoggingUpperBound(8)
     # ==========================================================================
    # Feature 1: Given a target contract, collect all transactions related to the contract.
    #            Collect all snippets of the transactions related to the target contract and collect invariant-related data.
    # ==========================================================================
    # Punk_1


    # Step 1: Collect transactions
    # Step 1.1: Collect transaction history using TrueBlocks
    txHashes = collectTransactionHistory(contract, endBlock)

    print("total transactions: ", len(txHashes))

    # Step 1.2: Download history transaction traces from QuickNode
    for tx in txHashes:
        storeATrace(tx)    
    pathList = []

    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    for tx in txHashes:
        path = SCRIPT_DIR + "/cache/" + tx + ".json.gz"
        pathList.append(path)


    # Step 2: Parse the transactions and Collect Invariant Related Data

    # Suppose target contract is A
    # LoggingUpperBound set to x means
    # starting from A's depth a, all functions calls of depth a+x will be logged
    changeLoggingUpperBound(8) 

    # The followings are a list of locators for locating the external call functions inside the target contract that are related to deposit, invest, and withdraw
    # This is used for dataFlow invariant inference of Trace2Inv
    # a locator is used to define where a transfer happens
    # l1: deposit locator - when a user deposits their funds into the contract
    # l2: invest locator - when the contract invests the funds to another DeFi protocol
    # l3: withdraw locator - when a user withdraws their funds from the contract
 

    # create folders for storing cached invariant-related data
    setUpDirectories(script_dir=SCRIPT_DIR, contract=contract)
   
    
    # The following code extracts invariant-related data from the transactions
    for ii in range(len(txHashes)):
        # if readAccessList(contract, txHashes[ii]) != []:
        #     continue
        dataSourceMapList, accessList, splitedTraceTree = analyzeOneTx(contract, txHashes[ii], pathList[ii], l1, l2, l3)        
        writeDataSource(contract, txHashes[ii], dataSourceMapList)
        writeAccessList(contract, txHashes[ii], accessList)
        writeSplitedTraceTree(contract, txHashes[ii], splitedTraceTree)
    
    accesslistTable = []
    accesslistList = []

    executionListTable = []
    executionListList = []
    
    # Here we use 70% of the data as training data, same as in Trace2Inv Paper
    trainingSetSize = int(0.7 * len(txHashes))

    # read the data source map list
    for ii in range( len(txHashes) ):
        accessList = readAccessList(contract, txHashes[ii])
        if len(accessList) > 0:
            accesslistList.append( (txHashes[ii], accessList) )
        
        if len(accessList) == 1 and len(accessList[0]) == 0:
            print("no access for tx: ", txHashes[ii]) 
        

    accesslistTable.append( (contract, accesslistList) )


    # read the data source map list
    for ii in range( trainingSetSize ):
        executionList = readDataSource(contract, txHashes[ii])
        if len(executionList) > 0 and len(executionList[0]) > 0:
            for execution in executionList[0]:
                executionListList.append( (txHashes[ii], execution) )

    executionListTable.append( (contract, executionListList) )


    
    # Invariant Category 1: Access Control
    print("=====================================================")
    print("=============== Access Control ======================")
    print("=====================================================")
    inferAccessControl(accesslistTable)

    # Invariant Category 2: Time Locks
    print("=====================================================")
    print("=================== Time Locks ======================")
    print("=====================================================")

    # enterFuncs represent the functions that a user can deposit their funds into
    enterFuncs = []
    # exitFuncs represent the functions that a user can withdraw their funds from
    exitFuncs = ['withdrawAllToForge', 'withdrawTo', 'withdrawToForge']
    inferTimeLocks(accesslistTable, enterFuncs, exitFuncs)

    # Invariant Category 3: Gas Control
    print("=====================================================")
    print("=================== Gas Control =====================")
    print("=====================================================")
    inferGasControl(accesslistTable)

    # Invariant Category 4: Re-entrancy
    print("=====================================================")
    print("=================== Re-entrancy =====================")
    print("=====================================================")
    enterFuncs = []
    exitFuncs = ['withdrawAllToForge', 'withdrawTo', 'withdrawToForge']
    inferReentrancy(accesslistTable, enterFuncs, exitFuncs)

    # Invariant Category 5: Special Storage
    print("=====================================================")
    print("================ Special Storage ====================")
    print("=====================================================")
    inferSpecialStorage(accesslistTable)

    # Invariant Category 6: Oracle Control
    # Only the following benchmarks use an oracle
    # Punk_1 does not use an oracle, but the code is still here for reference
    # # benchmarks = ["bZx2", "Warp_interface", "CheeseBank_1", "CheeseBank_2", "CheeseBank_3", "InverseFi", \
    # #                 "CreamFi2_1", "CreamFi2_2", "CreamFi2_3", "CreamFi2_4", "Harvest1_fUSDT", "Harvest2_fUSDC", \
    # #                 "ValueDeFi"]
    # inferOracleRange(benchmarks)

    executionListTable = reformatExecutionTable(executionListTable)
    # Invariant Category 7: DataFlow
    print("=====================================================")
    print("=================== DataFlow ========================")
    print("=====================================================")
    enterFuncs = []
    exitFuncs = ['withdrawAllToForge', 'withdrawTo', 'withdrawToForge']
    inferDataFlows(executionListTable, enterFuncs, exitFuncs)

    # # Invariant Category 8: MoneyFlow
    # print("=====================================================")
    # print("=================== MoneyFlow =======================")
    # print("=====================================================")
    # # transferToken is the token that is being transferred, which we try to restrict
    # transferToken = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
    # inferMoneyFlows(executionListTable, contract, transferToken) 






if __name__ == '__main__':
    main()
    # mainTestTime()

















def feature2():
    # ==========================================================================
    # Feature 2: Given a transaction, collect logs from debug_traceTransaction RPC call,
    #           translate the logs into other logs required by other tools. 
    #           aims to replace the modified Geth part in other tools
    # ==========================================================================

    # this is the example transaction used as a demo in TxSpector repository https://github.com/OSUSecLab/TxSpector
    txHash = "0x37085f336b5d3e588e37674544678f8cb0fc092a6de5d83bd647e20e5232897b"
    # step 1: fetch the trace
    storeATrace(txHash)
    # step 2: read the trace and translate it to TxSpector desired format
    trace = readATrace(txHash)
    translated = TxSpectorTranslator().parseLogs(trace)
    with open ("TxSpectorTranslator/Trace2InvTranslated.txt", "w") as f:
        f.write(translated)
    # step 3: compare translated result with ground truth, which is the demo input of TxSpector
    #         placed in TxSpectorTranslator/0x37085f336b5d3e588e37674544678f8cb0fc092a6de5d83bd647e20e5232897b.txt
    #         original file at https://github.com/OSUSecLab/TxSpector/blob/master/example/0x37085f336b5d3e588e37674544678f8cb0fc092a6de5d83bd647e20e5232897b.txt
    groundTruth = None
    with open ("TxSpectorTranslator/0x37085f336b5d3e588e37674544678f8cb0fc092a6de5d83bd647e20e5232897b.txt", "r") as f:
        groundTruth = f.read()
    if translated == groundTruth + "\n":
        print("The translated result of Trace2Inv is the same as the input required by TxSpector")
    else:
        print("The translated result of Trace2Inv is different from the input required by TxSpector")
