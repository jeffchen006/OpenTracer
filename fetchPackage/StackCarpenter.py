import sys

class stackCarpener:
    
    def __init__(self) -> None:
        """opcodeInputStackmap: opcode -> length of input required by that opcode"""
        """opcodeOutputStackmap: opcode -> length of output emitted by that opcode"""
        
        self.opcodeInputStackmap = {
            "STOP": 0, "ADD": 2,
            "MUL": 2, "SUB": 2,
            "DIV": 2, "SDIV": 2,
            "MOD": 2, "SMOD": 2,
            "ADDMOD": 3, "MULMOD": 3,
            "EXP": 2, "SIGNEXTEND": 2,
            "LT": 2, "GT": 2,
            "SLT": 2, "SGT": 2,
            "EQ": 2, "ISZERO": 1,
            "AND": 2, "OR": 2,
            "XOR": 2, "NOT": 1,
            "BYTE": 2, "SHL": 2,
            "SHR": 2, "SAR": 2,
            "SHA3": 2, "KECCAK256": 2,
            "ADDRESS": 0,
            "BALANCE": 1, "ORIGIN": 0,
            "CALLER": 0, "CALLVALUE": 0,
            "CALLDATALOAD": 1, "CALLDATASIZE": 0,
            "CALLDATACOPY": 3, "CODESIZE": 0,
            "CODECOPY": 3, "GASPRICE": 0,
            "EXTCODESIZE": 1, "EXTCODECOPY": 4,
            "RETURNDATASIZE": 0, "RETURNDATACOPY": 3,
            "EXTCODEHASH": 1, "BLOCKHASH": 1,
            "COINBASE": 0, "TIMESTAMP": 0,
            "NUMBER": 0, "DIFFICULTY": 0,
            "GASLIMIT": 0, "CHAINID": 0,
            "SELFBALANCE": 0, "BASEFEE": 0,
            "POP": 1, "MLOAD": 1,
            "MSTORE": 2, "MSTORE8": 2,
            "SLOAD": 1, "SSTORE": 2,
            "JUMP": 1, "JUMPI": 2,
            "PC": 0, "MSIZE": 0,
            "GAS": 0, "JUMPDEST": 0,
            "PUSH1": 0, "PUSH2": 0, "PUSH3": 0, "PUSH4": 0, "PUSH5": 0, "PUSH6": 0,
            "PUSH7": 0, "PUSH8": 0, "PUSH9": 0, "PUSH10": 0, "PUSH11": 0, "PUSH12": 0,
            "PUSH13": 0, "PUSH14": 0, "PUSH15": 0, "PUSH16": 0, "PUSH17": 0, "PUSH18": 0,
            "PUSH19": 0, "PUSH20": 0, "PUSH21": 0, "PUSH22": 0, "PUSH23": 0, "PUSH24": 0,
            "PUSH25": 0, "PUSH26": 0, "PUSH27": 0, "PUSH28": 0, "PUSH29": 0, "PUSH30": 0,
            "PUSH31": 0, "PUSH32": 0,
            "DUP1": 1, "DUP2": 2, "DUP3": 3, "DUP4": 4, "DUP5": 5, "DUP6": 6,
            "DUP7": 7, "DUP8": 8, "DUP9": 9, "DUP10": 10, "DUP11": 11, "DUP12": 12,
            "DUP13": 13, "DUP14": 14, "DUP15": 15, "DUP16": 16, "SWAP1": 2, "SWAP2": 3,
            "SWAP3": 4, "SWAP4": 5, "SWAP5": 6, "SWAP6": 7, "SWAP7": 8, "SWAP8": 9,
            "SWAP9": 10, "SWAP10": 11, "SWAP11": 12, "SWAP12": 13, "SWAP13": 14, "SWAP14": 15,
            "SWAP15": 16, "SWAP16": 17,
            "LOG0": 2, "LOG1": 3, "LOG2": 4, "LOG3": 5, "LOG4": 6, 
            "CREATE": 3,
            "CALL": 7, "CALLCODE": 7,
            "RETURN": 2, "DELEGATECALL": 6,
            "CREATE2": 4, "STATICCALL": 6,
            "REVERT": 2, "SELFDESTRUCT": 1,
            "INVALID": 0, "opcode 0xfe not defined": 0
        }

        self.opcodeOutputStackmap = {
            "STOP": 0, "ADD": 1,
            "MUL": 1, "SUB": 1,
            "DIV": 1, "SDIV": 1,
            "MOD": 1, "SMOD": 1,
            "ADDMOD": 1, "MULMOD": 1,
            "EXP": 1, "SIGNEXTEND": 1,
            "LT": 1, "GT": 1,
            "SLT": 1, "SGT": 1,
            "EQ": 1, "ISZERO": 1,
            "AND": 1, "OR": 1,
            "XOR": 1, "NOT": 1,
            "BYTE": 1, "SHL": 1,
            "SHR": 1, "SAR": 1,
            "SHA3": 1, "KECCAK256": 1,
            "ADDRESS": 1,
            "BALANCE": 1, "ORIGIN": 1,
            "CALLER": 1, "CALLVALUE": 1,
            "CALLDATALOAD": 1, "CALLDATASIZE": 1,
            "CALLDATACOPY": 0, "CODESIZE": 1,
            "CODECOPY": 0, "GASPRICE": 1,
            "EXTCODESIZE": 1, "EXTCODECOPY": 0,
            "RETURNDATASIZE": 1, "RETURNDATACOPY": 0,
            "EXTCODEHASH": 1, "BLOCKHASH": 1,
            "COINBASE": 1, "TIMESTAMP": 1,
            "NUMBER": 1, "DIFFICULTY": 1,
            "GASLIMIT": 1, "CHAINID": 1,
            "SELFBALANCE": 1, "BASEFEE": 1,
            "POP": 0, "MLOAD": 1,
            "MSTORE": 0, "MSTORE8": 0,
            "SLOAD": 1, "SSTORE": 0,
            "JUMP": 0, "JUMPI": 0,
            "PC": 1, "MSIZE": 1,
            "GAS": 1, "JUMPDEST": 0,
            "PUSH1": 1, "PUSH2": 1, "PUSH3": 1, "PUSH4": 1, "PUSH5": 1, "PUSH6": 1,
            "PUSH7": 1, "PUSH8": 1, "PUSH9": 1, "PUSH10": 1, "PUSH11": 1, "PUSH12": 1,
            "PUSH13": 1, "PUSH14": 1, "PUSH15": 1, "PUSH16": 1, "PUSH17": 1, "PUSH18": 1,
            "PUSH19": 1, "PUSH20": 1, "PUSH21": 1, "PUSH22": 1, "PUSH23": 1, "PUSH24": 1,
            "PUSH25": 1, "PUSH26": 1, "PUSH27": 1, "PUSH28": 1, "PUSH29": 1, "PUSH30": 1,
            "PUSH31": 1, "PUSH32": 1,
            "DUP1": 2, "DUP2": 3, "DUP3": 4, "DUP4": 5, "DUP5": 6, "DUP6": 7,
            "DUP7": 8, "DUP8": 9, "DUP9": 10, "DUP10": 11, "DUP11": 12, "DUP12": 13,
            "DUP13": 14, "DUP14": 15, "DUP15": 16, "DUP16": 17, 
            "SWAP1": 2, "SWAP2": 3, "SWAP3": 4, "SWAP4": 5, "SWAP5": 6, "SWAP6": 7,
            "SWAP7": 8, "SWAP8": 9, "SWAP9": 10, "SWAP10": 11, "SWAP11": 12, "SWAP12": 13,
            "SWAP13": 14, "SWAP14": 15, "SWAP15": 16, "SWAP16": 17,
            "LOG0": 0, "LOG1": 0, "LOG2": 0, "LOG3": 0, "LOG4": 0,
            "CREATE": 1, "CALL": 1, "CALLCODE": 1,
            "RETURN": 0, "DELEGATECALL": 1,
            "CREATE2": 1, "STATICCALL": 1,
            "REVERT": 0, "SELFDESTRUCT": 0,
            "INVALID": 0, "opcode 0xfe not defined": 0
        }
        
    def opcode2InputStackLength(self, opcode: str) -> int:
        """Given an opcode, return the stack length needed to execute the opcode"""
        if opcode in self.opcodeInputStackmap:
            return self.opcodeInputStackmap[opcode]
        else:
            sys.exit("Opcode {} not found in opcode2InputStackLength!!".format(opcode))

    def opcode2OutputStackLength(self, opcode: str) -> int:
        """Given an opcode, return the stack length after executing the opcode"""
        if opcode in self.opcodeOutputStackmap:
            return self.opcodeOutputStackmap[opcode]
        else:
            sys.exit("Opcode {} not found in opcode2OutputStackLength!!".format(opcode))
