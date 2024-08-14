# OpenTracer 

A video description of OpenTracer can be found here: https://youtu.be/vTdmjWdYd30

For users of OpenTracer, please fill in your own endpoints of etherscan, ethereum archive nodes, and quicknode (or any endpoint supporting `debug_traceTransaction` rpc call) in `settings.toml` in order to use it.




## A Dynamic Analysis Tool for EVM Transaction Traces

OpenTracer is a powerful Ethereum Virtual Machine (EVM) trace dynamic analysis tool designed to extract and analyze data from transaction traces. It offers a comprehensive suite of features for developers and analysts looking to gain deeper insights into smart contract interactions and behaviors.

### Feature 1: Open-source Transaction Explorer

OpenTracer provides functionalities similar to well-known transaction explorers. It allows users to input a transaction hash and obtain detailed parsed transaction traces that include contract addresses, gas costs, ether transfers, function signatures, and storage changes. The tool is comparable to:
   - [Phalcon](https://explorer.phalcon.xyz/)
   - [Tx Tracer](https://openchain.xyz/trace)
   - [Cruise](https://cruise.supremacy.team/)
   - [Ethtx](https://ethtx.info/)
   - [Tenderly](https://dashboard.tenderly.co/explorer)
   - [eigenphi](https://tx.eigenphi.io/analyseTransaction)

Example output:

Parsed Invocation Tree
```plaintext
[Meta Info] TxHash: 0xed2e82bb59e2ea39bfdc7d08ae2f7fcad7200e00163f6e3440b9a5d72fc3ef5d   tx.origin: 0x710295b5f326c2e47e6dd2e7f6b5b0f7c5ac2f24
    [CALL] { value:0.00e+00 } 0x0000000000085d4780b73119b644ae5ecd22b376.(830E...0000) -> 1
      [sload] 0x6e41e0fbe643dfdb6043698bf865aada82dc46b953f754a3468eaa272a362dc7: 0xb650eb28d35691dd1bd481325d40e65273844f9b
        [DELEGATECALL] { gas:68985, value:0.00e+00 } 0xb650eb28d35691dd1bd481325d40e65273844f9b.0xa9059cbb(830e...dc8c) -> 1
          [sload] 0xd9db5c8b748acb11ccfc8f1de90c21032834bbac7c7506aba03614eebc209a11: 0x0
          [sload] 0xc06734647f3ef212fc58ea058fd795439a9e23dee75f4a6fdce5e660379b6b2e: 0x0
          [sload] 0xd0d5ab6396a7546ff8fd2ace4291181e66a87c625f7c7a692a26032f794550e: 0x6d65d13dabfeccdc8c
          [sload] 0xd0d5ab6396a7546ff8fd2ace4291181e66a87c625f7c7a692a26032f794550e: 0x6d65d13dabfeccdc8c
          [sload] 0xec01746e8e90bd328487896e4a321e712fca6dc8e63894b574abdd7f604679cc: 0x0
          [sload] 0xec01746e8e90bd328487896e4a321e712fca6dc8e63894b574abdd7f604679cc: 0x0
```

Parsed Invocation Tree with Decoded Storage Access
```plaintext
[Meta Info]  TxHash: 0xed2e82bb59e2ea39bfdc7d08ae2f7fcad7200e00163f6e3440b9a5d72fc3ef5d   tx.origin: 0x710295b5f326c2e47e6dd2e7f6b5b0f7c5ac2f24
    [CALL] { value:0.00e+00 } 0x0000000000085d4780b73119b644ae5ecd22b376.fallback(830E...0000) -> 1
      [sload] 0x6e41e0fbe643dfdb6043698bf865aada82dc46b953f754a3468eaa272a362dc7: 0xb650eb28d35691dd1bd481325d40e65273844f9b
        [DELEGATECALL] { gas:68985, value:0.00e+00 } 0xb650eb28d35691dd1bd481325d40e65273844f9b.transfer(['0x830eba02481b20f07cbb988312e23f3ade93cc1e', 2018031817111227915404]) -> [True]
          [sload] 0x16[ CALLER-000000000000000000000000710295b5f326c2e47e6dd2e7f6b5b0f7c5ac2f24 ]: 0x0
          [sload] 0x16[ msg.data[4:36]-000000000000000000000000830eba02481b20f07cbb988312e23f3ade93cc1e ]: 0x0
          [sload] 0xd0d5ab6396a7546ff8fd2ace4291181e66a87c625f7c7a692a26032f794550e: 0x6d65d13dabfeccdc8c
          [sstore] 0xd0d5ab6396a7546ff8fd2ace4291181e66a87c625f7c7a692a26032f794550e: 0x0
          [sload] 0xe[ msg.data[4:36]-000000000000000000000000830eba02481b20f07cbb988312e23f3ade93cc1e ]: 0x0
          [sstore] 0xe[ msg.data[4:36]-000000000000000000000000830eba02481b20f07cbb988312e23f3ade93cc1e ]: 0x6d65d13dabfeccdc8c
```




### Feature 2: Dynamically infer invariants from transaction history

This feature allows users to extract "any" data from transactions and infer invariants from user-defined invariant-related data. It allows users to input a smart contract address, and an end block number, and the tool will return invariants that hold for all transactions that happened from the deployment of the smart contract to the user-defined block number. This feature is e



For example,
```plaintext

=====================================================
=============== Access Control ======================
=====================================================
func initialize0xcc2a9a5b has only 1 sender
func initialize0xcc2a9a5b has only 1 origin
func invest0xE8B5E51F has only 1 sender
func invest0xE8B5E51F has more than 5 origins
func withdrawTo0xC86283C8 has only 1 sender
func withdrawTo0xC86283C8 has only 1 origin
==invariant map: 
{ 'initialize0xcc2a9a5b': { 'isOriginOwner': '0xe36cc0432619247ab12f1cdd19bb3e7a24a7f47c',
                            'isSenderOwner': '0xe36cc0432619247ab12f1cdd19bb3e7a24a7f47c',
                            'require(origin==sender)': True},
  'invest0xE8B5E51F': { 'isSenderOwner': '0x0a548513693a09135604e78b8a8fe3bb801586e6',
                        'require(origin==sender)': False},
  'withdrawTo0xC86283C8': { 'isOriginOwner': '0xe36cc0432619247ab12f1cdd19bb3e7a24a7f47c',
                            'isSenderOwner': '0x0a548513693a09135604e78b8a8fe3bb801586e6',
                            'require(origin==sender)': False}}
Interpretation of the above invariant map: 
For the function initialize0xcc2a9a5b:
        is the invariant require(origin==sender) satisfied? True
        is the invariant isSenderOwner satisfied? 0xe36cc0432619247ab12f1cdd19bb3e7a24a7f47c
        is the invariant isOriginOwner satisfied? 0xe36cc0432619247ab12f1cdd19bb3e7a24a7f47c
For the function invest0xE8B5E51F:
        is the invariant require(origin==sender) satisfied? False
        is the invariant isSenderOwner satisfied? 0x0a548513693a09135604e78b8a8fe3bb801586e6
For the function withdrawTo0xC86283C8:
        is the invariant require(origin==sender) satisfied? False
        is the invariant isSenderOwner satisfied? 0x0a548513693a09135604e78b8a8fe3bb801586e6
        is the invariant isOriginOwner satisfied? 0xe36cc0432619247ab12f1cdd19bb3e7a24a7f47c

```

### Feature 3: Translate Results of debug_traceTransaction to other trace required by other tools

Since OpenTracer records all information of
a transaction (by parsing result of `debug_traceTransaction` and augments it using `eth_getTransactionReceipt` and EtherScan results), we believe with moderate effort, OpenTracer can translate the results to other trace formats required by other tools, to replace the modified archive node part of many research works. Here we provide an example of how to translate the results to the format required by [TxSpector] (https://github.com/OSUSecLab/TxSpector/). 


TxSpector requires an input of a special form of trace, in a txt file. Each line contains a program counter, an opcode, and key input to that opcode. For example, TxSpector provides the following [example](https://github.com/OSUSecLab/TxSpector/blob/master/example/0x37085f336b5d3e588e37674544678f8cb0fc092a6de5d83bd647e20e5232897b.txt). 

The authors chose to modify the Geth node and print out the required information when replaying a transaction. This is primarily because no existing RPC geth endpoint provides all the required information, they would have to use multiple RPC methods to collect information, parse and combine them to get the required information. Directly modifying a Geth node is easier in this case. However, for future users of TxSpector, they would have to merge the changes to the latest version of Geth, which is not trivial. During our experiment with TxSpector, we discovered a few new EVM opcodes are not supported by TxSpector, which would require additional effort to change the Geth node, which is not trivial.

We believe with moderate effort, OpenTracer can translate the results to the format required by TxSpector. Since OpenTracer already collects ALL information about a transaction, users only need to truncate the information to the required format. 

We implemented a TxSpector translator on top of functionalities provided by OpenTracer using only ~300 lines of code at `TxSpectorTranslator/translator.py`. 
It should be much easier to maintain and extend the translator in the future. Adding a new opcode only requires modifying some if conditions in the code.

As an example, we translate the demo transaction `0x37085f336b5d3e588e37674544678f8cb0fc092a6de5d83bd647e20e5232897b` to the format required by TxSpector, and compare it with the original TxSpector demo input. It matches.  






## Compatibility and Testing
OpenTracer has been rigorously tested on both Ubuntu Linux and MacOS.

### Characteristics
- **Soundness**: No false positives are reported; all invariants are verified across all input transactions.
- **Interpretability**: The invariants are straightforward, generally easy to understand, and mostly human-readable.
- **Practicality**: Derived from real-world high-profile DeFi projects and audit report recommendations.
- **Extensibility**: Easily expandable to include additional templates or handle more complex invariants.


## Dependencies
To ensure smooth operation of OpenTracer, the following dependencies must be installed:

### sqlite3
Utilized for caching transactions and contracts data.
- Pre-installed on MacOS.

### Vyper and Solidity Compilers
- [vyper-select](https://github.com/jeffchen006/vyper-select)
- [solc-select](https://github.com/crytic/solc-select)
  - Ensure to install all necessary compiler versions through the tools above.

### Slither
A Solidity static analysis framework.
```bash
python3 -m pip install slither-analyzer
```

### TrueBlocks (Only needed if feature 2 is needed )
Install TrueBlocks from the official documentation.

https://trueblocks.io/docs/install/install-core/



#### check whether trueBlocks is installed correctly 

After installation, ensure to configure TrueBlocks correctly:
    
```bash
chifra init
```
If you encounter issues with RPC connections:
```bash
EROR[21-06|15:55:48.033] error making request to rpcProvider (http://localhost:8545): Post "http://localhost:8545": dial tcp [::1]:8545: connect: connection refused
```

Modify the `$CONFIG/trueBlocks.toml` to include a valid RPC endpoint, such as:

```plaintext
[chains.mainnet]
...
rpcProvider = "http://localhost:8545"
...
```
We recommend some free rpc endpoint such as "https://eth.llamarpc.com"
It takes about 10 mins for TrueBlocks to create the index for transaction history. 

After the index is created, you can run the following command to check whether TrueBlocks is installed correctly:
```bash
chifra blocks 23
```

The correct output
```bash
{
  "data": [
    {
      "baseFeePerGas": 0,
      "blockNumber": 23,
      "date": "2015-07-30 15:30:08 UTC",
      "difficulty": 17255485474,
      "gasLimit": 5000,
      "gasUsed": 0,
      "hash": "0x639f5f5e5b7e354de98dbc0857be83603d57ff55029f6488c96da0c5e42ed91a",
      "miner": "0x0193d941b50d91be6567c7ee1c0fe7af498b4137",
      "parentHash": "0xa8f91e9df6bfd1424a9ec9b0149f01aa31cceed3b21bac7376d90d7f0cd80cf4",
      "timestamp": 1438270208,
      "transactions": [],
      "uncles": [],
      "withdrawals": []
    }
  ]
}
```



## Usage Example

For a practical demonstration of OpenTracer, let's use the contract `Punk_1` as an example. It is important to understand that TrueBlocks captures every occurrence of a contract address in transactions, but not all are relevant to the contract's functional transaction history.

For instance, suppose the target contract is `A`. A simple ERC20 transfer like `transfer(A, 1);` includes `A` in the transaction. However, since there is no invocation of `A`'s functions, such occurrences should not be considered part of `A`'s transaction history.

We collected 31 transactions from TrueBlocks for `Punk_1` up to block 12995895, where a significant event (hack) occurred. Our OpenTracer FSE 2024 paper, however, identifies only 28 transactions as relevant. This discrepancy arises because certain transactions need to be excluded for various reasons:

1. **Deployment Transaction**: The initial transaction that deploys `Punk_1` is unique and typically behaves differently from subsequent transactions. For instance, the deployment transaction identified by `0x39a78785a85250ee6f17459113efa2bdc2d5069a37f751171ee44efb3ac219f7` is excluded.
   
2. **Post-Exploit Transactions**: Transactions occurring after significant events, like exploits, may not be representative of the typical contract behavior. An example is `0x7604c7dd6e9bcdba8bac277f1f8e7c1e4c6bb57afd4ddf6a16f629e8495a0281`, which follows the hack transaction `0x597d11c05563611cb4ad4ed4c57ca53bbe3b7d3fefc37d1ef0724ad58904742b`.

3. **Non-Invoking Transactions**: Transactions where the contract address is merely a parameter and not the primary actor do not reflect direct interactions with the contract. An example is `0x8c7cc6ab0a5ed76098152927c52a7f3d3ded6f95783fbd13e05b174574bb2763`.

In the OpenTracer paper, we also discuss how transaction history is divided into a training set (70%) and a testing set (30%), which differs from the complete history used here for invariant inference.




## Folder Structure
Below is a detailed overview of the folder structure provided in the artifact, which aids in understanding the roles and functions of each component:


### Source Code Folders
- `cache/`: Contains cached transaction trace data
- `constraintPackage/`: Includes scripts and modules for generating invariants.
- `crawlPackage/`: Includes tools for crawling blockchain-related information from sources like EtherScan, TrueBlocks, and Ethereum Archive Node.
- `fetchPackage/`: Responsible for fetching results from debug_traceTransaction and pruning them.
- `main.py`: The main Python script for demonstrating three main features of OpenTracer.
- `parserPackage/`: Contains parsing utilities for processing data.
- `staticAnalyzer/`: Contains code for analyzing Solidity and Vyper source code to assist invariant generation.
- `trackerPackage/`: Includes tools for dynamic taint analysis.
- `TxSpectorTranslator/`: Includes a translator for converting OpenTracer results to the format required by TxSpector, and a demo transaction for testing.
- `utilsPackage/`: Contains utility scripts and modules supporting various functions.
- `settings.toml`: Provides configuration settings for various scripts and tools. It is supposed to be secret and not shared.




## Knowledge Base
There are three primary types of traces that are provided by different Ethereum nodes:

- **Transaction Trace (trace)**: Basic trace providing an overview of transaction actions.
- **State Difference (stateDiff)**: Details all state changes resulting from transaction execution.
- **Virtual Machine Execution Trace (vmTrace)**: Offers a detailed trace of the VM's state throughout the transaction, including subcalls. This trace is what OpenTracer uses. 


### Tips for Managing Large Transaction Histories
For transaction histories exceeding 100,000 entries, consider organizing them into separate folders labeled from `0x0` to `0xf` to optimize processing speed.


### Challenges in Bytecode Analysis
One of the more challenging aspects of trace analysis involves dealing with proxy-implementation patterns, which often require manual verification to identify the active implementation.

### Learning Resources
For those interested in a deeper understanding of EVM bytecode and its implications, the following resources are invaluable:
- [Understanding how a simple contract breaks into bytecode](https://ethereum.stackexchange.com/questions/58652/understanding-how-a-simple-contract-breaks-into-bytecode)
- [Ethereum opcode meaning of first few instructions](https://ethereum.stackexchange.com/questions/56824/ethereum-opcode-meaning-of-first-few-instructions)
- [Understanding EVM Bytecode - Part 1 to 4 by Trustlook](https://blog.trustlook.com/understand-evm-bytecode-part-1/)
- [EVM: From Solidity to Byte Code, Memory, and Storage](https://www.youtube.com/watch?v=RxL_1AfV7N4&t=3248s)
