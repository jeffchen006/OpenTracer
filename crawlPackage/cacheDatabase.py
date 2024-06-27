import json
import sys


def _save_transaction_receipt(receipt, cur, txHash, conn):
    # receipt is assumed to be a dictionary
    # and its in proper format
    transactionhash = receipt['transactionHash']
    blockNumber = receipt['blockNumber']
    if not isinstance(blockNumber, int):
        blockNumber = int(blockNumber, 16)
    contractAddress = receipt['contractAddress']
    cumulativeGasUsed = receipt['cumulativeGasUsed']
    if not isinstance(cumulativeGasUsed, int):
        cumulativeGasUsed = int(cumulativeGasUsed, 16)
    effectiveGasPrice = receipt['effectiveGasPrice']
    if not isinstance(effectiveGasPrice, int):
        effectiveGasPrice = int(effectiveGasPrice, 16)
    from_ = receipt['from']
    gasUsed = receipt['gasUsed']
    if not isinstance(gasUsed, int):
        gasUsed = int(gasUsed, 16)

    status = receipt['status']
    if isinstance(status, int):
        status = hex(status)
    to = receipt['to']
    transactionIndex = receipt['transactionIndex']
    if not isinstance(transactionIndex, int):
        transactionIndex = int(transactionIndex, 16)
    type = receipt['type']
    input = receipt['input'] if 'input' in receipt else None
    value = receipt['value'] if 'value' in receipt else None
    

    data = (
        transactionhash,
        blockNumber,
        contractAddress,
        cumulativeGasUsed,
        effectiveGasPrice,
        from_,
        gasUsed,
        status,
        to,
        transactionIndex,
        type,
        input,
        value
    )
    # Insert the data into the transactions table
    cur.execute('''
    INSERT OR REPLACE INTO transactions (
        transactionHash, blockNumber, contractAddress, cumulativeGasUsed,
        effectiveGasPrice, fromAddress, gasUsed, status, toAddress, transactionIndex, type, input, value
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', data)
    conn.commit()


def _load_transaction_receipt(transaction_hash, cur):
    # Query the database for the transaction with the specified hash
    cur.execute('''
    SELECT * FROM transactions WHERE transactionHash = ?
    ''', (transaction_hash,))
    
    # Fetch the result
    transaction = cur.fetchone()
        
    if transaction:
        # Convert the transaction tuple to a more readable format (optional)
        transaction_dict = {
            'transactionHash': transaction[0],
            'blockNumber': transaction[1],
            'transactionIndex': transaction[2],
            'contractAddress': transaction[3],
            'from': transaction[4],
            'to': transaction[5],
            'status': transaction[6],
            'type': transaction[7],
            'gasUsed': transaction[8],
            'cumulativeGasUsed': transaction[9],
            'effectiveGasPrice': transaction[10],
            'input': transaction[11],
            'value': transaction[12]
        }
        return transaction_dict
    else:
        return None
    

def _save_contract(receipt, cur, contractAddress, conn):
# {'SourceCode': '', 'ABI': 'Contract source code not verified', 'ContractName': '', 'CompilerVersion': '', 'OptimizationUsed': '', 'Runs': '', 'ConstructorArguments': '', 'EVMVersion': 'Default', 'Library': '', 'LicenseType': 'Unknown', 'Proxy': '0', 'Implementation': '', 'SwarmSource': ''}  
    # receipt is assumed to be a dictionary
    if not isinstance(receipt, dict):
        sys.exit("Error: receipt is not a dictionary")
    if 'SourceCode' not in receipt or 'ABI' not in receipt or \
        'ContractName' not in receipt or 'CompilerVersion' not in receipt or \
        'OptimizationUsed' not in receipt or 'Runs' not in receipt or \
        'ConstructorArguments' not in receipt or 'EVMVersion' not in receipt or \
        'Library' not in receipt or 'LicenseType' not in receipt or \
        'Proxy' not in receipt or 'Implementation' not in receipt or \
        'SwarmSource' not in receipt:
        sys.exit("Error: receipt is missing a key")

    SourceCode = receipt['SourceCode']
    ABI = receipt['ABI']
    ContractName = receipt['ContractName']
    CompilerVersion = receipt['CompilerVersion']
    OptimizationUsed = receipt['OptimizationUsed']
    Runs = receipt['Runs']
    ConstructorArguments = receipt['ConstructorArguments']
    EVMVersion = receipt['EVMVersion']
    Library = receipt['Library']
    LicenseType = receipt['LicenseType']
    Proxy = receipt['Proxy']
    Implementation = receipt['Implementation']
    SwarmSource = receipt['SwarmSource']

    data = (
        contractAddress,
        SourceCode,
        ABI,
        ContractName,
        CompilerVersion,
        OptimizationUsed,
        Runs,
        ConstructorArguments,
        EVMVersion,
        Library,
        LicenseType,
        Proxy,
        Implementation,
        SwarmSource
    )


    # Insert the data into the contracts table
    cur.execute('''
    INSERT OR REPLACE INTO contracts (
        contractAddress, SourceCode, ABI, ContractName, CompilerVersion, OptimizationUsed, Runs,
        ConstructorArguments, EVMVersion, Library, LicenseType, Proxy, Implementation, SwarmSource
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', data)
    conn.commit()
    pass

def _load_contract(contractAddress, cur):
    # Query the database for the contract with the specified address
    cur.execute('''
    SELECT * FROM contracts WHERE contractAddress = ?
    ''', (contractAddress,))

    # Fetch the result
    contract = cur.fetchone()
    if contract:
        # Convert the contract tuple to a more readable format (optional)
        contract_dict = {
            'contractAddress': contract[0],
            'SourceCode': contract[1],
            'ABI': contract[2],
            'ContractName': contract[3],
            'CompilerVersion': contract[4],
            'OptimizationUsed': contract[5],
            'Runs': contract[6],
            'ConstructorArguments': contract[7],
            'EVMVersion': contract[8],
            'Library': contract[9],
            'LicenseType': contract[10],
            'Proxy': contract[11],
            'Implementation': contract[12],
            'SwarmSource': contract[13]
        }
        return contract_dict
    else:
        return None
