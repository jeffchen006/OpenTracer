#!/bin/bash
folder_name="logs0311_TimeLock_DataFlow"

# Ensure the directory exists
mkdir -p "/Users/jeffchen/Documents/OpenTracer/$folder_name"

# List of benchmarks
benchmarks=("DoughFina1" "DoughFina2" "Bedrock_DeFi1" "Bedrock_DeFi2" "GFOX1" "GFOX2"
            "BlueberryProtocol1" "BlueberryProtocol2" "BlueberryProtocol3" 
            "BlueberryProtocol4" "BlueberryProtocol5" "UwULend1")

# Loop through each benchmark and run the command
for benchmark in "${benchmarks[@]}"; do
    time /usr/bin/python3 main.py "$benchmark" > "/Users/jeffchen/Documents/OpenTracer/$folder_name/$benchmark.txt"
done

# List of benchmarks
benchmarks=("PrismaFi1" "PrismaFi2" "PrismaFi3" "PikeFinance" "OnyxDAO1" "OnyxDAO2"
            "OnyxDAO3" "OnyxDAO4" "OnyxDAO5" "OnyxDAO6" "OnyxDAO7")

# Loop through each benchmark and run the command
for benchmark in "${benchmarks[@]}"; do
    time /usr/bin/python3 main.py "$benchmark" > "/Users/jeffchen/Documents/OpenTracer/$folder_name/$benchmark.txt"
done