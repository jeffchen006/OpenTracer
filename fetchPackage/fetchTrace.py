from re import L
from web3 import Web3, HTTPProvider
import sys
import os
import toml
settings = toml.load("settings.toml")
import json
from typing import Dict, List, Tuple
import requests
import multiprocessing
import time
import pickle
import gzip
import gc
import random

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))
from fetchPackage.StackCarpenter import stackCarpener
from parserPackage.functions import *
from utilsPackage.compressor import writeCompressedJson, readCompressedJson


class fetcher:
    def __init__(self):
        self.urls = settings["settings"]["rpcProviders"]

        self.w3s = []
        for url in self.urls:
            self.w3s.append(Web3(HTTPProvider(url, request_kwargs={'timeout': 60})))        
        self.counter = random.randint(0, len(self.urls))
        self.stackCarpenter = stackCarpener()
        self.debug_traceTransactionSettings = {
            'enableMemory': True,
            "disableMemory": False,
            'disableStack': False,
            'disableStorage': True,
            'enableReturnData': False,
        }
        self.results = []

    def get_url(self):
        self.counter += 1
        numOfUrls = len(self.urls)
        return self.urls[self.counter % numOfUrls]

    def get_w3(self):
        self.counter += 1
        numOfUrls = len(self.urls)
        return self.w3s[self.counter % numOfUrls]

    def pruneStructLog(self, structLog: dict, lastOpcode: str = None, FullTrace: bool = False):
        structLog_copy = structLog.copy()
        prune1 = True 
        prune2 = True # still need it, otherwise exceed 100MB file size limit
        if FullTrace:
            prune1 = False
            prune2 = False

        # Prune 1: remove pc, and gasCost
        if prune1:
            # del structLog_copy["pc"]
            # del structLog_copy["gas"]
            # del structLog_copy["depth"]
            del structLog_copy["gasCost"]

        # Prune 2: remove unnessary stack (won't be used by opcode)
        if prune2:
            len1 = self.stackCarpenter.opcode2InputStackLength(structLog_copy["op"])
            len2 = 0
            if lastOpcode != None:
                len2 = self.stackCarpenter.opcode2OutputStackLength(lastOpcode)
            necessaryStackLen = max(len1, len2)
            del structLog_copy["stack"][:-necessaryStackLen]
            for ii in range(len(structLog_copy["stack"])):
                # if structLog["stack"] contains a list of string of integers, convert them to string of hex integers
                structLog_copy["stack"][ii] = str(hex(int(structLog_copy["stack"][ii])))


        if "error" in structLog_copy:
            error_dict = dict(structLog_copy["error"]).copy()
            structLog_copy["error"] = error_dict

        # Prune 3: remove unnessary memory (won't be used by opcode)
        if structLog_copy["op"] == "RETURN" \
            or structLog_copy["op"] == "REVERT" \
            or structLog_copy["op"] == "KECCAK256" \
            or structLog_copy["op"] == "CODECOPY" \
            or structLog_copy["op"] == "EXTCODECOPY" \
            or structLog_copy["op"] == "RETURNDATACOPY" \
            or structLog_copy["op"] == "SHA3" :
            pass
        elif structLog_copy["op"] == "CREATE" or structLog_copy["op"] == "CREATE2" or \
            structLog_copy["op"] == "CALL" or structLog_copy["op"] == "CALLCODE" or \
            structLog_copy["op"] == "STATICCALL" or structLog_copy["op"] == "DELEGATECALL":
            pass
        elif structLog_copy["op"] == "RETURN" or structLog_copy["op"] == "REVERT" or \
            structLog_copy["op"] == "STOP" or structLog_copy["op"] == "SELFDESTRUCT" or \
            structLog_copy["op"] == "INVALID":
            pass
        elif lastOpcode == "CALLDATACOPY" or lastOpcode == "CODECOPY" or lastOpcode == "EXTCODECOPY" or \
                lastOpcode == "RETURNDATACOPY":
            pass
        elif lastOpcode == "CALL" or lastOpcode == "CALLCODE" or lastOpcode == "STATICCALL" or lastOpcode == "DELEGATECALL":
            pass
    
        else:
            if "memory" in structLog_copy:
                del structLog_copy["memory"]

        return structLog_copy

    def prettyPrintTrace(self, trace: dict):
        """Pretty print the trace data (returned by getTrace)"""
        print("structLogs:")
        for structLog in trace["structLogs"]:
            print(structLog)
        print("gas:", trace["gas"])
        print("failed:", trace["failed"])
        print("returnValue:", trace["returnValue"])

    def batchRequests(self, calls: List[Tuple[str, List]]):
        payload = [
            {"method": method, "params": params, "id": None, "jsonrpc": "2.0"}
            for method, params in calls
        ]
        batch_repsonse = requests.post(self.get_url(), json=payload).json()
        for response in batch_repsonse:
            if "error" in response:
                raise ValueError(response["error"]["message"])
            yield response["result"]

    def cookStoreTrace(self, result, FullTrace: bool, category: str, contract: str, TxHash: str):
        result_dict = self.cookResult(result, FullTrace=FullTrace)
        path = getPathFromCategoryTxHash(category, contract, TxHash)
        writeCompressedJson(path, result_dict)

    def cookStoreTrace2(self, index: str, FullTrace: bool, category: str, contract: str, TxHash: str):
        result_dict = self.cookResult(self.results[index], FullTrace=FullTrace)
        path = getPathFromCategoryTxHash(category, contract, TxHash)
        writeCompressedJson(path, result_dict)

    def cookStoreTraces(self, indexes: str, FullTrace: bool, category: str, contract: str, TxHashes: str):
        for i in range(len(indexes)):
            result_dict = self.cookResult(self.results[indexes[i]], FullTrace)
            path = getPathFromCategoryTxHash(category, contract, TxHashes[i])
            writeCompressedJson(path, result_dict)

    def batch_storeTrace3(self, category: str, contract: str, Txs: list, FullTrace: bool = False):
        """Given a list of tx hashes, store the trace data"""
        start = time.time()
        calls = [('debug_traceTransaction', [Tx, self.debug_traceTransactionSettings]) for Tx in Txs]
        results = self.batchRequests(calls)
        end = time.time() - start
        print("batch_getTrace time:", end)
        self.results = list(results)
        processNum = 25
        all_jobs = []
        all_Txs = []
        for i in range(processNum):
            all_jobs.append([])
            all_Txs.append([])
        for i in range(len(Txs)):
            all_jobs[i % processNum].append(i)
            all_Txs[i % processNum].append(Txs[i])
        all_processes = []
        for i in range(processNum):
            p = multiprocessing.Process(target=self.cookStoreTraces, args=(all_jobs[i], FullTrace, category, contract, all_Txs[i]))
            all_processes.append(p)
            p.start()
        for p in all_processes:
            p.join()
        all_processes = []
        end2 = time.time() - (end + start)
        print("batch_storeTrace time:", end2)
        self.results = []
        gc.collect()
        
    def batch_storeTrace2(self, category: str, contract: str, Txs: list, FullTrace: bool = False):
        """Given a list of tx hashes, store the trace data"""
        start = time.time()
        calls = [('debug_traceTransaction', [Tx, self.debug_traceTransactionSettings]) for Tx in Txs]
        results = self.batchRequests(calls)
        end = time.time() - start
        print("batch_getTrace time:", end)
        self.results = list(results)
        processNum = 20
        all_processes = []
        for i in range(len(Txs)):
            process = multiprocessing.Process(target=self.cookStoreTrace2, args=(i, \
                    FullTrace, category, contract, Txs[i]))
            process.start()
            all_processes.append(process)
            if i != 0 and (i % processNum == 0 or i == len(Txs) - 1):
                for process in all_processes:
                    process.join()
                all_processes = []
        end2 = time.time() - (end + start)
        print("batch_storeTrace time:", end2)
        self.results = []
        gc.collect()

    def batch_storeTrace(self, category: str, contract: str, Txs: list, FullTrace: bool = False):
        """Given a list of tx hashes, store the trace data"""
        start = time.time()
        calls = [('debug_traceTransaction', [Tx, self.debug_traceTransactionSettings]) for Tx in Txs]
        results = self.batchRequests(calls)
        end = time.time() - start
        print("batch_getTrace time:", end)
        processNum = 10
        all_processes = []
        i = -1
        for result in results:
            i += 1
            process = multiprocessing.Process(target=self.cookStoreTrace, args=(result, \
                    FullTrace, category, contract, Txs[i]))
            process.start()
            all_processes.append(process)

            if i != 0 and (i % processNum == 0 or i == len(Txs) - 1):
                for process in all_processes:
                    process.join()
                all_processes = []
        end2 = time.time() - (end + start)
        print("batch_storeTrace time:", end2)
            
    def batch_getTrace(self, Txs: list, FullTrace: bool = False):
        """Given a list of tx hashes, return a list of trace data"""
        calls = [('debug_traceTransaction', [Tx, self.debug_traceTransactionSettings]) for Tx in Txs]
        results = self.batchRequests(calls)
        result_dicts = [self.cookResult(result, FullTrace=FullTrace) for result in results]
        return result_dicts

    def getTrace(self, Tx: str, FullTrace: bool = False):
        """Given a tx hash, return the trace data"""
        web3 = self.get_w3()
        start = time.time()
        gc.collect()
        print(Tx)
        result = None
        try: 
            result = web3.manager.request_blocking('debug_traceTransaction', [Tx, self.debug_traceTransactionSettings])
        except MemoryError:
            print("MemoryError when collecting trace data " + Tx, file=sys.stderr)

        end = time.time() - start
        print("Tx {} fetch trace costs {} s".format(Tx[0:4], end))
        
        result_dict = self.cookResult(result, FullTrace=FullTrace)
        print("Tx {} cooking trace costs {} s".format(Tx[0:4], time.time() - start - end))
        return result_dict
        
    def cookResult(self, result, FullTrace: bool = False):
        result_dict = dict(result)
        lastOpcode = {} # last opcode of the same depth
        for ii in range(len(result_dict['structLogs'])):
            structLog = result_dict['structLogs'][ii]
            structLog_dict = dict(structLog)
            depth = structLog_dict['depth']
            if depth not in lastOpcode:
                structLog_dict_copy = self.pruneStructLog(structLog_dict, FullTrace=FullTrace)
            else:
                structLog_dict_copy = self.pruneStructLog(structLog_dict, lastOpcode[depth], FullTrace=FullTrace)
            result_dict['structLogs'][ii] = structLog_dict_copy
            lastOpcode[depth] = structLog_dict_copy["op"]
        return result_dict

    def storeTrace(self, txHash: str, FullTrace: bool = False):
        """Given a tx hash, store the trace data"""
        result_dict = self.getTrace(txHash, FullTrace=FullTrace)
        SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
        path = SCRIPT_DIR + '/../Benchmarks_Traces' + '/Txs/{}.json.gz'.format(txHash)
        writeCompressedJson(path, result_dict)



def main():
    fe = fetcher()
    # HackTx = "0x395675b56370a9f5fe8b32badfa80043f5291443bd6c8273900476880fb5221e"
    # fe.storeTrace("DeFiHackLabs", "0x051ebd717311350f1684f89335bed4abd083a2b6", HackTx, True )
    pass




if __name__ == "__main__":
    main()


