import os
import sys
from crawlPackage.crawlEtherscan import CrawlEtherscan
from crawlPackage.crawlQuicknode import CrawlQuickNode
from crawlPackage.crawlTrueBlocks import CrawlTrueBlocks
import subprocess
import json 
import time
import random
import multiprocessing
from multiprocessing import Process, Manager
import copy

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))


class Crawler:
    def __init__(self) -> None:
        self.crawlEtherscan = CrawlEtherscan()
        self.crawlQuicknode = CrawlQuickNode()
        self.crawlTrueBlocks = CrawlTrueBlocks()

    def Contract2TxHistoryBlockIndex(self, contractAddress: str, endBlock: int = 999999999999999, maxTxs: int = None) -> list:
        """Given a contract address and an end block, return a list of (block, blockIndex) tuples"""
        ContractTxHistoryBlockIndex = CrawlTrueBlocks().Contract2TxHistoryBlockIndex(contractAddress)
        # find number of elements before endBlock
        num = 0
        for i in range(len(ContractTxHistoryBlockIndex)):
            num += 1
            if ContractTxHistoryBlockIndex[i][0] > endBlock:
                break
        index = 0
        for ii in range(len(ContractTxHistoryBlockIndex)):
            block, _ = ContractTxHistoryBlockIndex[ii]
            if block <= endBlock:
                index = ii
        end = index + 1
        if maxTxs != None:
            end = min(index + 1, maxTxs)
        return ContractTxHistoryBlockIndex[0: end]
    

    def BlockIndex2TxHelper(self, aa, bb, index, managerList):
        Tx = self.BlockIndex2Tx(aa, bb)
        managerList[index] = Tx

    def Contract2TxHistory(self, contractAddress: str, endBlock: int = 999999999999999, maxTxs: int = None) -> list:
        """Given a contract address and an end block, return a list of tx hashes from deploy block to end block"""
        HistoryBlockIndex = self.Contract2TxHistoryBlockIndex(contractAddress, endBlock, maxTxs)
        # remove duplicates in HistoryBlockIndex
        new_HistoryBlockIndex = []
        for HistoryBlock in HistoryBlockIndex:
            if HistoryBlock not in new_HistoryBlockIndex:
                new_HistoryBlockIndex.append(HistoryBlock)
        HistoryBlockIndex = new_HistoryBlockIndex

        txHashes = []
        index = 0
        batchSize = 1000
        timegap = 1
        while True:
            start = index * batchSize
            end = min( (index + 1) * batchSize, len(HistoryBlockIndex) )
            Txs = None
            while Txs == None:
                try:
                    Txs = self.crawlQuicknode.batch_BlockIndex2Tx(HistoryBlockIndex[start: end])
                except Exception as e:
                    pass
            txHashes += Txs
            if end == len(HistoryBlockIndex):
                break
            index += 1
            print("start: " + str(start) + " end: " + str(end))
        txHashes = self.blockIndexes2Txs(HistoryBlockIndex)
        return txHashes
    
    

    def blockIndexes2Txs(self, HistoryBlockIndex):
        # if len(HistoryBlockIndex) > 100000:
        #     print("but we only crawl the last 100000 txs")
        #     HistoryBlockIndex = copy.deepcopy(HistoryBlockIndex[-100000:])
        
        # if len(HistoryBlockIndex) > 100000:
        #     print("temporally skip crawling tx history")
        #     return

        
        txHashes = []
        index = 0
        batchSize = 1000
        timegap = 1
        while True:
            start = index * batchSize
            end = min( (index + 1) * batchSize, len(HistoryBlockIndex) )
            Txs = None
            while Txs == None:
                try:
                    Txs = self.crawlQuicknode.batch_BlockIndex2Tx(HistoryBlockIndex[start: end])
                    # print("HistoryBlockIndex", HistoryBlockIndex[start: end])
                    # print("Txs", Txs)
                except Exception as e:
                    # time.sleep(timegap)
                    # timegap += 2
                    pass
            txHashes += Txs
            if end == len(HistoryBlockIndex):
                break
            index += 1
            print("start: " + str(start) + " end: " + str(end))
        return txHashes



    
    def Contract2TxHistoryRankedbyGasUsed(self, contractAddress: str, endBlock: int = 999999999999999) -> list:
        """Given a contract address and an end block, return a list of tx hashes from deploy block to end block, ranked by gas used"""
        ContractTxHistoryBlockIndex = self.crawlTrueBlocks.Contract2TxHistoryBlockIndex(contractAddress)
        txHashes = []
        # find number of elements before endBlock
        num = 0
        for i in range(len(ContractTxHistoryBlockIndex)):
            num += 1
            if ContractTxHistoryBlockIndex[i][0] > endBlock:
                break

        for ii in range(len(ContractTxHistoryBlockIndex)):
            (block, blockIndex) = ContractTxHistoryBlockIndex[ii]
            if block <= endBlock:
                txHash, gasUsed = self.BlockIndex2TxGasUsed(block, blockIndex)
                txHashes.append((txHash, gasUsed))
                if ii % 100 == 0:
                    print("working on {} out of {} txs".format(ii, num))
            else:
                break
        
        txHashes.sort(key=lambda x: x[1], reverse=True)

        return txHashes

    def Tx2Block(self, Tx: str) -> int:
        """Given a tx hash, return its block number"""
        return self.crawlQuicknode.Tx2Block(Tx)
    
    def Tx2BlockIndex(self, Tx: str) -> int:
        """Given a tx hash, return its block index"""
        return self.crawlQuicknode.Tx2BlockIndex(Tx)
    
    def BlockIndex2Tx(self, block: int, blockIndex: int) -> str:
        """Given a block number and a block index, return the tx hash"""
        return self.crawlQuicknode.BlockIndex2Tx(block, blockIndex)

    def BlockIndex2TxGasUsed(self, block: int, blockIndex: int) -> int:
        """Given a block number and a block index, return the tx gas used"""
        return self.crawlQuicknode.BlockIndex2TxGasUsed(block, blockIndex)





def main():
    crawler = Crawler()
    # test Contract2TxHistory
    contractAddress = '0xcc13fc627effd6e35d2d2706ea3c4d7396c610ea'

    contractAddress = "0x11111254369792b2Ca5d084aB5eEA397cA8fa48B" # 1inch exchange 2

    start_time = time.time() 

    txHashes = crawler.Contract2TxHistory(contractAddress)
    print(txHashes)
    end_time = time.time() - start_time
    print("In total, it takes {} seconds".format(end_time))


    # test Contract2TxHistoryRankedbyGasUsed
    # start_time = time.time()
    # txHistory = crawler.Contract2TxHistoryRankedbyGasUsed(contractAddress,  4925047 + 10000)
    # end_time = time.time() - start_time
    # print("In total, it takes {} seconds to get Contract2TxHistoryRankedbyGasUsed".format(end_time))

    # print("The first 10 txs are:")
    # for i in range(10):
    #     print(txHistory[i])
    
    # start_time = time.time()
    # txHistoryRankedByGasUsed = crawler.TxHistory2RankedByGasUsed(txHistory)
    # end_time = time.time() - start_time
    # print("In total, it takes {} seconds to get txHistoryRankedByGasUsed".format(end_time))




if __name__ == '__main__':
    main()
