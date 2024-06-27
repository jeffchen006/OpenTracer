## Code Structure

The code is structured as follows:

* parser.py: a localized version of the parserGlobal. It only cares about one contract. 

Given a contract C, a list of Txs Txs. 



For each transaction

* parser.py: The main parser class, basically does anything similar to a transaction viewer. Only cares about execution tree, call/staticcall/delegatecall/return/stop/gasless. It gives high-level info like the execution tree, call data, return value, msg.sender. 

* functions.py: Some helper functions for the parser class and the TraceTree class which is used to build the execution tree.

* TraceTree.py: The TraceTree class which is used to build the execution tree.

* tracker.py: the tracker class tracks the stack changes. And apply data flow analysis. 


