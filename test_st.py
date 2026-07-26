import requests
import json

url = 'https://api.smartthings.com/v1/devices'
headers = {'Authorization': 'Bearer cae67689-6b43-4548-ab14-3263b4e25d37'}
try:
    resp = requests.get(url, headers=headers)
    print("STATUS:", resp.status_code)
    print("JSON:", json.dumps(resp.json(), indent=2))
except Exception as e:
    print(e)
