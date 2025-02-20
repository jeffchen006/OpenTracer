import requests
import json

url = "https://fragrant-green-season.quiknode.pro/cb1c4f0490a20c89699a3f04db464b414b2d5094/"

payload = json.dumps({
  "method": "eth_blockNumber",
  "params": [],
  "id": 1,
  "jsonrpc": "2.0"
})

headers = {
  'Content-Type': 'application/json'
}

response = requests.request("POST", url, headers=headers, data=payload)

print(response.text)