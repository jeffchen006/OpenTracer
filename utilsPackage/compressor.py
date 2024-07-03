import sys
import os
import gzip
import time
import json
import pickle


def writeDataSource(SCRIPT_DIR, contract, tx, dataSourceMapList):
    path = SCRIPT_DIR + "/../cache/" + contract + "/{}.pickle".format(tx)
    # print("write", path)
    # print(dataSourceMapList)
    with open(path, 'wb') as f:
        pickle.dump(dataSourceMapList, f)


def readDataSource(SCRIPT_DIR, contract = None, tx = None):
    path = None
    if contract is None and tx is None:
        path = SCRIPT_DIR
    else:
        path = SCRIPT_DIR + "/../cache/" + contract + "/{}.pickle".format(tx)
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


def writeAccessList(SCRIPT_DIR, contract, tx, accessList):
    path = SCRIPT_DIR + "/../cache/" + contract + "_Access/{}.pickle".format(tx)
    # print("write", path)
    # print(dataSourceMapList)
    with open(path, 'wb') as f:
        pickle.dump(accessList, f)

def readAccessList(SCRIPT_DIR, contract, tx):
    path = SCRIPT_DIR + "/../cache/" + contract + "_Access/{}.pickle".format(tx)
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


def writeSplitedTraceTree(SCRIPT_DIR, contract, tx, splitedTraceTree):
    path = SCRIPT_DIR + "/../cache/" + contract + "_SplitedTraceTree/{}.pickle".format(tx)
    # print("write", path)
    # print(dataSourceMapList)
    with open(path, 'wb') as f:
        pickle.dump(splitedTraceTree, f)

def readSplitedTraceTree(SCRIPT_DIR, contract, tx):
    path = SCRIPT_DIR + "/../cache/" + contract + "_SplitedTraceTree/{}.pickle".format(tx)

    # print("read from  ", path)
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



def writeList(path, txList):
    # print("write", path)
    # print(dataSourceMapList)
    with open(path, 'wb') as f:
        pickle.dump(txList, f)


def readList(path):
    # path = SCRIPT_DIR + "/../cache/" + contract + "/{}.pickle".format(tx)
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


def writeListTxt(path, txList):
    # allow overwrite
    with open(path, 'w') as f:
        for tx in txList:
            f.write(tx + "\n")


def readListTxt(path):
    with open(path, 'r') as f:
        txList = f.readlines()
        txList = [tx.strip() for tx in txList]
    return txList
    


def writeCompressedJson(filePath: str, data: dict):
    with gzip.open(filePath, "wb") as f:
        pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)

def writeJson(filePath: str, data: dict):
    with open(filePath, "w") as f:
        json.dump(data, f, indent=4)

def readCompressedJson(filePath: str) -> dict:
    # print("readCompressedJson: ", filePath)
    with gzip.open(filePath, "rb") as f:
        jsonDict = pickle.load(f)                 
        return jsonDict

def readJson(filePath: str) -> dict:
    with open(filePath, "r") as f:
        jsonDict = json.load(f)                 
        return jsonDict
    
def setUpDirectories(script_dir , contract):
    path1 = script_dir + "/cache/" + contract
    path2 = script_dir + "/cache/" + contract + "_Access"
    path3 = script_dir + "/cache/" + contract + "_SplitedTraceTree"
    for path in [path1, path2, path3]:
        if not os.path.exists(path):
            os.makedirs(path)
    

if __name__ == "__main__":
    # filePath = "/home/zhiychen/Documents/TxGuard/Benchmarks/CVEAccessControl/Txs/0x4b89f8996892d137c3de1312d1dd4e4f4ffca171/0x0ba17dc46e3a67796376e707c618898e6e1a8d163988af5acbdb6012e7e36dd1.json.gz"
    # temp = readCompressedJson(filePath)

    # # originally, pc, op, gas, stack
    # # batch, op, gas, depth, stack
    # print(temp)

    filePath = "/home/zhiychen/Documents/TxGuard/tempppp.txt"

    TxList = ["0x1", "0x2", "0x3"]
    writeListTxt(filePath, TxList)

    TxList = readListTxt(filePath)
    print(TxList)