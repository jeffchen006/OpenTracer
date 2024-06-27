import subprocess
import json
import sys, os
from utilsPackage.compressor import *

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

class CrawlTrueBlocks:
    def __init__(self):
        pass

    def Block2Txs(self, block: int) -> list:
        """Given a block number, return a list of tx hashes in that block"""
        output = subprocess.getoutput("chifra blocks -e " + str(block))
        output_json = json.loads(output)
        txHashes = output_json['data'][0]['tx_hashes']
        return txHashes

    def BlockIndex2TxHash(self, block: int, blockIndex: int) -> str:
        """Given a block number and a block index, return the tx hash"""
        txHashes = self.Block2TxHashes(block)
        return txHashes[blockIndex]

    def Contract2TxHistoryBlockIndex(self, contractAddress: str) -> list:
        """Given a contract address, return a list of (block, blockIndex) tuples"""
        self.Contract2TxHistoryWarmUp(contractAddress)
        output = subprocess.getoutput("chifra list --fmt json " + contractAddress)
        output_json = json.loads(output)
        ContractTxHistoryBlockIndex = []
        for data in output_json['data']:
            block = int(data['blockNumber'])
            blockIndex = int(data['transactionIndex'])
            ContractTxHistoryBlockIndex.append((block, blockIndex))
        return ContractTxHistoryBlockIndex


    def Contract2TxHistoryWarmUp(self, contractAddress: str) -> None:
        """Given a contract address, warm up the cache"""
        subprocess.getoutput("chifra list --fmt json " + contractAddress)





def main():
    tb = CrawlTrueBlocks()
    # test Tx2GasUsed
    # txs = '0x04b713fdbbf14d4712df5ccc7bb3dfb102ac28b99872506a363c0dcc0ce4343c'
    # gasUsed = tb.Tx2GasUsed(txs)
    # print(gasUsed)

    # test Contract2TxHistoryBlockIndex
    # contractAddress = '0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7'
    # ContractTxHistoryBlockIndex = tb.Contract2TxHistoryBlockIndex(contractAddress)

    # blockBlockIndexList = []

    # for block, blockIndex in ContractTxHistoryBlockIndex:
    #     if block >= 11687459 and block <= 11792184:
    #         blockBlockIndexList.append((block, blockIndex))
    # writeCompressedJson('3PoolBlockIndexList.pickle', blockBlockIndexList)
    # blockBlockIndexList = readCompressedJson('3PoolBlockIndexList.pickle')
    # print(len(blockBlockIndexList))


    contract = "0x72AFAECF99C9d9C8215fF44C77B94B99C28741e8" # Chainlink Oracle
    LIST = tb.Contract2TxHistoryBlockIndex(contract)
    print(LIST)



if __name__ == '__main__':
    main()

