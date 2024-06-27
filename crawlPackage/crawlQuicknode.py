import string
from web3 import Web3, HTTPProvider
import requests
from hexbytes import HexBytes
from typing import Dict, List, Tuple
import os
import sys
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))
from utilsPackage.compressor import *
import json
import pickle
import random



import toml
settings = toml.load("settings.toml")



def save_object(obj, filename):
    try:
        SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
        with open(SCRIPT_DIR + "/cache/" + "{}/{}.pickle".format(filename[0:3], filename), "wb") as f:
            pickle.dump(obj, f, protocol=pickle.HIGHEST_PROTOCOL)
    except Exception as ex:
        print("Error during pickling object (Possibly unsupported):", ex)
    finally:
        pass
 

def load_object(filename):
    try:
        SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
        with open(SCRIPT_DIR + "/cache/" + "{}/{}.pickle".format(filename[0:3], filename), "rb") as f:
            return pickle.load(f)
    except Exception as ex:
        return None
    finally:
        pass



def save_object_balance(obj, filename):
    try:
        SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
        with open(SCRIPT_DIR + "/cache/balances/" + "{}.pickle".format(filename), "wb") as f:
            pickle.dump(obj, f, protocol=pickle.HIGHEST_PROTOCOL)
    except Exception as ex:
        print("Error during pickling object (Possibly unsupported):", ex)
    finally:
        pass
 


def load_object_balance(filename):
    try:
        SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
        with open(SCRIPT_DIR + "/cache/balances/" + "{}.pickle".format(filename), "rb") as f:
            return pickle.load(f)
    except Exception as ex:
        return None
    finally:
        pass
    
    

    
def toDict(dictToParse):
    # convert any 'AttributeDict' type found to 'dict'
    parsedDict = dict(dictToParse)
    for key, val in parsedDict.items():
        if 'list' in str(type(val)):
            parsedDict[key] = [_parseValue(x) for x in val]
        else:
            parsedDict[key] = _parseValue(val)
    return parsedDict


def _parseValue(val):
    # check for nested dict structures to iterate through
    if 'dict' in str(type(val)).lower():
        return toDict(val)
    # convert 'HexBytes' type to 'str'
    elif 'HexBytes' in str(type(val)):
        return val.hex()
    else:
        return val



class CrawlQuickNode:
    def __init__(self):
        self.urls = settings["settings"]["ethArchives"]
        self.w3s = [Web3(HTTPProvider(url)) for url in self.urls]

        self.counter = random.randint(0, len(self.urls))
        self.cacheReceipt = {}
        self.cacheBalanceMapName = None
        self.cacheBalanceMap = None
    
    def get_url(self):
        self.counter += 1
        numOfAPIkeys = len(self.urls)
        return self.urls[self.counter % numOfAPIkeys]

    def get_w3(self):
        self.counter += 1
        numOfAPIkeys = len(self.urls)
        url = self.urls[self.counter % numOfAPIkeys]
        # print(url)
        return self.w3s[self.counter % numOfAPIkeys]

    def Tx2Receipt(self, Tx: str) -> dict:
        """Given a Tx hash, return its Tx Receipt"""
        # if Tx in self.cacheReceipt:
        #     return self.cacheReceipt[Tx]
        # filename = "{}_Receipt".format(Tx)
        # receiptJson = load_object(filename)
        # if receiptJson is not None and receiptJson != "Max rate limit reached":
        #     self.cacheReceipt[Tx] = receiptJson
        #     return receiptJson
        receipt = self.get_w3().eth.get_transaction_receipt(Tx)
        # receiptJson = Web3.toJSON(receipt)
        # receiptJson = json.loads(receiptJson)
        receiptJson = toDict(receipt)
        # save_object(receiptJson, filename)
        return receiptJson

    

    def Tx2Details(self, Tx: str) -> dict:
        receipt = self.Tx2Receipt(Tx)
        if isinstance(receipt, str):
            # print(receipt)
            receipt = json.loads(receipt)
            
            # sys.exit("string")
            # return {"contractAddress": "unknown", "from": "unknown", "to": "unknown", "status": "unknown"}
        # print("receipt: ", receipt)

        fromAddress = receipt['from'] 
        toAddress = None if 'to' not in receipt else receipt['to']
        contractAddress = None if 'contractAddress' not in receipt else receipt['contractAddress']
        # status = receipt['status']
        status = receipt['type']
        gasUsed = receipt['gasUsed']
        # status: 0 => failed, 1 => success
        # to: Address of the receiver or null in a contract creation transaction.
        ret = {"contractAddress": contractAddress, "from": fromAddress, "to": toAddress, \
               "status": status, "gasUsed": gasUsed}
        return ret


    def ContractTx2Block(self, contract: str, Tx: str) -> int:
        """Given a Tx hash, return its block number"""
        receipt = self.Tx2Receipt(Tx)
        # hex to dec
        if isinstance(receipt['blockNumber'], str):
            return int(receipt['blockNumber'], 16)
        else:
            return receipt['blockNumber']
        

    def Tx2Block(self, Tx: str) -> int:
        """Given a Tx hash, return its block number"""
        receipt = self.Tx2Receipt(Tx)
        # hex to dec
        if isinstance(receipt['blockNumber'], str):
            return int(receipt['blockNumber'], 16)
        else:
            return receipt['blockNumber']

    def Tx2BlockIndex(self, Tx: str) -> int:
        """Given a Tx hash, return its block index"""
        receipt = self.Tx2Receipt(Tx)
        # print(receipt)
        if isinstance(receipt['transactionIndex'], HexBytes):
            return int(receipt['transactionIndex'], 16)
        elif isinstance(receipt['transactionIndex'], int):
            return receipt['transactionIndex']

    def BlockIndex2TxGasUsed(self, block: int, blockIndex: int) -> int:
        """Given a block number and a block index, return the pair (tx hash, gasUsed)"""
        # block_hex = Web3.toHex(block)
        block_hex = hex(block)
        output = self.get_w3().eth.get_transaction_by_block(block_hex, blockIndex)
        hexstring = output["hash"].hex()
        gasUsed = output["gas"]
        return (hexstring, gasUsed)

    def batchRequests(self, calls: List[Tuple[str, List]]):
        payload = [
            {"method": method, "params": params, "id": None, "jsonrpc": "2.0"}
            for method, params in calls
        ]
        url = self.get_url()
        print(url)
        batch_repsonse = requests.post(url, json=payload).json()
        for response in batch_repsonse:
            if "error" in response:
                raise ValueError(response["error"]["message"])
            yield response["result"]

    def batch_BlockIndex2Tx(self, BlockIndexPairs: list) -> list:
        """Given a list of block numbers and a list of block indexes, return a list of tx hashes"""
        newBlockIndexPairs = [(hex(BlockIndexPair[0]), hex(BlockIndexPair[1])) for BlockIndexPair in BlockIndexPairs]
        # newBlockIndexPairs = newBlockIndexPairs[-100:]
        values = self.batchRequests(
            [
                (
                    "eth_getTransactionByBlockNumberAndIndex", 
                    [BlockIndexPair[0], BlockIndexPair[1]]
                ) for BlockIndexPair in newBlockIndexPairs
            ])
        txHashes = [value['hash'] for value in values]
        return txHashes

    def batch_Blocks2Receipts(self, blocks: list) -> list:
        """Given a list of blocks, return a list of receipts"""
        values = self.batchRequests([("eth_getBlockByNumber", [Web3.toHex(block), True]) for block in blocks])
        return values
        
    def BlockIndex2Tx(self, block: int, blockIndex: int) -> str:
        """Given a block number and a block index, return the tx hash"""
        hexstring, _ = self.BlockIndex2TxGasUsed(block, blockIndex)
        return hexstring

    def Tx2GasUsed(self, Tx: str) -> int:
        """Given a Tx hash, return its gas used"""
        receipt = self.Tx2Receipt(Tx)
        return receipt['cumulativeGasUsed']

    def Txs2GasUsed(self, Txs: list) -> list:
        """Given a list of Tx hashes, return a list of gas used"""
        gasUsed = []
        for Tx in Txs:
            gasUsed.append(self.Tx2GasUsed(Tx))
        return gasUsed

    def Block2Receipt(self, block: str) -> dict:
        """Given a block number, return its Tx Receipt"""
        filename = "blocks/{}_Receipt".format(block)
        blockstatsJson = load_object(filename)
        if blockstatsJson is not None:
            return blockstatsJson
        block_hex = Web3.toHex(block)
        receipt = self.get_w3().eth.get_block(block_hex)
        receiptJson = Web3.toJSON(receipt)
        receiptJson = json.loads(receiptJson)
        save_object(receiptJson, filename)
        return receiptJson

    def Blocks2ReceiptsPrepare(self, blocks: list) -> list:
        """Given a list of blocks, return a list of receipts"""
        BlocksNeededFetch = []
        for block in blocks:
            filename = "blocks/{}_Receipt".format(block)
            blockstatsJson = load_object(filename)
            if blockstatsJson is None:
                BlocksNeededFetch.append(block)
        batchSize = 500
        batches = [BlocksNeededFetch[i:i + batchSize] for i in range(0, len(BlocksNeededFetch), batchSize)]
        for batch in batches:
            print("fetch batch of {} blocks".format(len(batch)))
            receipts = self.batch_Blocks2Receipts(batch) 
            for block, receipt in zip(batch, receipts):
                filename = "blocks/{}_Receipt".format(block)
                receiptJson = Web3.toJSON(receipt)
                receiptJson = json.loads(receiptJson)
                save_object(receiptJson, filename)      

    def Block2Txs(self, block: int) -> list:
        """Given a block number, return a list of tx hashes"""
        blockReceipt = self.Block2Receipt(block)
        txs = blockReceipt['transactions']
        if isinstance(txs, str):
            txs = json.loads(txs)
        if isinstance(txs[0], str):
            return txs
        hashes = [tx['hash'] for tx in txs]
        return hashes

    def TxPair2TxsInBetween(self, startTx: str, endTx: str, BlockIndexes: list) -> list:
        """Given a Tx pair <startTx, endTx>, find all the TxHashes happened in between them, given a list of BlockIndexes (block number, block index)"""
        
        startBlock = self.Tx2Block(startTx)
        startBlockIndex = self.Tx2BlockIndex(startTx)
        endBlock = self.Tx2Block(endTx)
        endBlockIndex = self.Tx2BlockIndex(endTx)

        uniqueBlockList = []
        blockArray = [] # a list of (block, index1, index2, index3, ...)
        for block, blockIndex in BlockIndexes:
            if block not in uniqueBlockList and block >= startBlock and block <= endBlock:
                uniqueBlockList.append(block)
                blockArray.append([block, blockIndex])
            elif block == blockArray[-1][0]:
                blockArray[-1].append(blockIndex)
        self.Blocks2ReceiptsPrepare(uniqueBlockList)
        
        TxsInBetween = []
        for blockArrayEntry in blockArray:
            block = blockArrayEntry[0]
            Txs = self.Block2Txs(block)
            for blockIndex in blockArrayEntry[1:]:
                Tx = Txs[blockIndex]
                if block == startBlock and blockIndex == startBlockIndex and \
                    startTx != Txs[startBlockIndex]:
                        sys.exit("startTx not match, \n startTx: {} \n Txs[startBlockIndex]: {}".format(startTx, Txs[startBlockIndex]))
                elif block == endBlock and blockIndex == endBlockIndex and \
                    endTx != Txs[endBlockIndex]:
                        sys.exit("endTx not match, \n endTx: {} \n Txs[endBlockIndex]: {}".format(endTx, Txs[endBlockIndex]))
                if block == startBlock and blockIndex < startBlockIndex:
                    continue
                if block == endBlock and blockIndex > endBlockIndex:
                    continue
                TxsInBetween.append(Tx)
        return TxsInBetween
    
    def ETHBalanceOf(self, address: str, block: int):
        url = self.get_url()
        block_hex = Web3.toHex(block)
        payload = json.dumps(
        {
            "method": "eth_getBalance",
            "params": [
                address,
                block_hex
            ],
            "id": 1,
            "jsonrpc": "2.0"
            }
        )
        headers = {
        'Content-Type': 'application/json'
        }

        response = requests.request("POST", url, headers=headers, data=payload)

        return int(response.json()['result'], 16)

    def ERC20TokenBalanceOf(self, erc20: str, contract: str, block: int):
        # use eth_call to get the balance of the contract'
        erc20 = erc20.lower()
        url = self.get_url()
        block_hex = Web3.toHex(block)
        # 0x70a08231: balanceOf function signature

        data = "0x70a08231" +   Web3.toHex(Web3.toBytes(hexstr=contract)) .lstrip("0x").rjust(64, "0")
        payload = json.dumps({
        "method": "eth_call",
        "params": [
                {
                "from": None,
                "to": erc20,
                "data": data
                },      
                str(block_hex)
            ],
            "id": 1,
            "jsonrpc": "2.0",
        })
        headers = {
            'Content-Type': 'application/json'
        }
        print(payload)
        response = requests.request("POST", url, headers=headers, data=payload)
        print(response.json()['result'])
        return int(response.json()['result'], 16)
    
    def TokenBalanceOf(self, address: str, contract: str, block: int):
        filename = "{}_{}".format(address, contract)
        block2balanceMap = None
        if self.cacheBalanceMapName == filename:
            block2balanceMap = self.cacheBalanceMap
        else:
            block2balanceMap = load_object_balance(filename)
            self.cacheBalanceMapName = filename
            self.cacheBalanceMap = block2balanceMap
            print(filename)
            print("load balance map from file")
            # for key in block2balanceMap:
            #     print(key)

        if block2balanceMap is not None and block in block2balanceMap:
            return block2balanceMap[block]
        else:
            balance = None
            print("querying rpc once")
            if address == "ether" or address.lower() == "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2":
                balance0 = self.ETHBalanceOf(contract, block)
                balance1 = self.ERC20TokenBalanceOf("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", contract, block)
                balance = balance0 + balance1
            else:
                balance = self.ERC20TokenBalanceOf(address, contract, block)
            
            if balance is None: 
                sys.exit("crawlQuickNode: balance is None")
            
            if block2balanceMap is None:
                block2balanceMap = {block: balance}
            else:
                block2balanceMap[block] = balance
            # print("saved once")
            # save_object_balance(block2balanceMap, filename)
            return balance
        

    def BatchTokenBalanceOfHelper(self, address: str, contract: str, blocks: list):
        filename = "{}_{}".format(address, contract)
        block2balanceMap = load_object_balance(filename)
        if block2balanceMap is None:
            block2balanceMap = {}

        balances = []
        # if len(blocks) > 1000 do it in batches of size 1000
        for i in range(0, len(blocks), 1000):
            print("batch {} of {}".format(i, len(blocks)))
            blocksBatch = blocks[i:i+1000]
            balancesBatch = None
            while True:
                try: 
                    balancesBatch = self.BatchTokenBalanceOf(address, contract, blocksBatch)
                    balances += balancesBatch
                    break
                except Exception as ex:
                    print(ex)
                    pass

        for block, balance in zip(blocks, balances):
            if block not in block2balanceMap:
                block2balanceMap[block] = balance
            elif block2balanceMap[block] != balance:
                sys.exit("balance not match")
        
        save_object_balance(block2balanceMap, filename)
        
        
    def BatchTokenBalanceOf(self, address: str, contract: str, blocks: list):
        '''Given an erc20 address, a contract address, and a list of blocks, return a list of balances  '''
        balances = []
        if address == "ether" or address.lower() == "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2":
            values = self.batchRequests(
                [ 
                    (
                        "eth_getBalance", 
                        [contract, Web3.toHex(block) ]
                    ) for block in blocks
                ]
            )
            balances0 = [int(value, 16) for value in values]

            paramsDict = {
                            "from": None,
                            "to": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                            "data": "0x70a08231" +   Web3.toHex(Web3.toBytes(hexstr=contract)) .lstrip("0x").rjust(64, "0")
                        }

            values1 = self.batchRequests(
                [
                    (
                        "eth_call",
                        [
                            paramsDict, 
                            str(Web3.toHex(block))
                        ]
                    ) for block in blocks
                ]
            )
            balances1 = [int(value, 16) for value in values1]
            if len(balances0) != len(balances1):
                sys.exit("length not match")   
            balances = [balance0 + balance1 for balance0, balance1 in zip(balances0, balances1)]
            return balances
        else:
            paramsDict = {
                            "from": None,
                            "to": address.lower(),
                            "data": "0x70a08231" +   Web3.toHex(Web3.toBytes(hexstr=contract)) .lstrip("0x").rjust(64, "0")
                        }
            
            values = self.batchRequests(
                [
                    (
                        "eth_call",
                        [
                            paramsDict, 
                            str(Web3.toHex(block))
                        ]
                    ) for block in blocks
                ]
            )

            balances = [int(value, 16) for value in values]
            return balances






def main():

    cq = CrawlQuickNode()
    # EminenceHackTx = "0x3503253131644dd9f52802d071de74e456570374d586ddd640159cf6fb9b8ad8"
    SimpleDAItransferTx = "0xeeb70054c1a08dd366570184d2da9457b08a620e2ffbbf5954bed5d8ec630943"
    # SimpleDAItransferTx2 = "0x164839b9cbf25f6050df6abc61b823baae736eef9af03fac60a9a0c87c642b63"
    # SimpleDAItransferTx3 = "0xd63b4308a9dafc426f468e568ab52d1c4738de0e66b5acbc3947709d15265227"
    # SimpleSwapTx = "0x05aa7b633e1ef83118e7b3719c3214aa3d1af962be927822cb893014836290cf"

    # # # test ERC20TokenBalanceOf
    # erc20 = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
    # contract = "0x44fbebd2f576670a6c33f6fc0b00aa8c5753b322"
    # balance = cq.ERC20TokenBalanceOf(erc20, contract, 10907920)
    # print(balance)

    addr = "0xd0ea0f40c4d893a06882f4c2049109f57db16629"
    # block = 18027698
    # balance = cq.ETHBalanceOf(addr, block)
    # print("{} ether at block {}".format(balance, block) )

    balances = cq.BatchTokenBalanceOf("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", addr, [18027698, 16027699])


    for value in balances:
        print(value)


    # test BlockIndex2Tx
    # qq = cq.BlockIndex2Tx(12911679, 3)
    # print(qq)
    # qq = cq.BlockIndex2Tx(12911679, 4)
    # print(qq)

    # # test Tx2Receipt
    # receipt = cq.Tx2Receipt(SimpleSwapTx)
    # import json
    # receipt = json.dumps(receipt, indent=2)
    # print(receipt)
    
    # test BlockIndexes2Txs
    # BlockIndexPairs = [(12911679, 3), (12911679, 4)]
    # Txs = cq.batch_BlockIndex2Tx(BlockIndexPairs)
    # print(Txs)

    # # test Tx2Receipt
    # receipt = cq.Tx2Receipt(SimpleDAItransferTx)
    # # parsed = json.loads(receipt)
    # print(receipt)

    # # dump into json
    # with open('temp.json', 'w') as f:
    #     json.dump(parsed, f, indent=2)
    

    # test Block2Txs
    # Txs = cq.Block2Txs(11687459)
    # print(Txs)

    # with open('temp.json', 'w') as f:
    #     json.dump(Txs, f, indent=2)

    # # test TxPair2TxsInBetween
    # # Yearn contract first interacts with Curve Fi 3Pool contract
    # startTx = "0x49d62533adb1131d476ff0a4f67d5a41ba1e65c2ceeb1de54eb8ad9d4f87bf8e"
    # # Yearn Hack:
    # endTx = "0x59faab5a1911618064f1ffa1e4649d85c99cfd9f0d64dcebbc1af7d7630da98b"
 
    # blockBlockIndexList = readCompressedJson('3PoolBlockIndexList.pickle')
    # print(len(blockBlockIndexList))
    # # start
    # blockList = []
    # ii = 0
    # for jj in range(len(blockBlockIndexList)):
    #     block, blockIndex = blockBlockIndexList[jj]
    #     if jj >= len(blockBlockIndexList) - 5 :
    #         print(block, blockIndex)
    #     if block not in blockList:
    #         blockList.append(block)
    # print(len(blockList))
    # cq.Blocks2ReceiptsPrepare(blockList)
    # Txs = cq.TxPair2TxsInBetween(startTx, endTx, blockBlockIndexList)
    # print(len(Txs))
    # with open('3PoolTxInBetween.txt', 'w') as f:
    #     for tx in Txs:
    #         f.write(tx + '\n')


    # # test 
    # from web3 import Web3, HTTPProvider
    # w3 = cq.get_w3()
    # receipt = w3.eth.get_logs({'topics': ['0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef']})
    # import pprint
    # pp = pprint.PrettyPrinter(indent=4)
    # pp.pprint(receipt)




if __name__ == '__main__':
    main()