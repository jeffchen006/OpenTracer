This is a static analyzer which gets all information from smart contracts(alternatively, verified contract address).

It includes wrappers to get information from Solidity and Vyper compilers.

It also contains a wrapper of Slither to better support this project, cross-validating results from Solidity and Vyper compilers.



Particularly, for contracts compiled with vyper-0.2.15 or before, there is no such an "-f layout" option, so I really cannot find storage layout. 

Therefore, it requires me to predict storage Layout using past trace data. Luckily, it is not a common case and I can do it manually.


Other scenarios include developers used their customized storage Layout file (Vyper) or even customized compilers to compiler the contracts. 


Recently, a couple of decompilers are open sourced. They can be used to predict storage layout for unverified contracts, interested readers can check it out:

https://github.com/smlxl/storage-layout-extractor

https://github.com/nevillegrech/gigahorse-toolchain

https://github.com/banteg/storage-layout



