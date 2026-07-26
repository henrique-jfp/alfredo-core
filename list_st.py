import requests
url = 'https://api.smartthings.com/v1/devices'
headers = {'Authorization': 'Bearer cae67689-6b43-4548-ab14-3263b4e25d37'}
resp = requests.get(url, headers=headers).json()
for d in resp.get('items', []):
    print(d['deviceId'], d['name'], d['label'])
