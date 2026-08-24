import requests
with open('/home/pvserver/alfredo-core/.env') as f:
    token = [line.split('=')[1] for line in f.read().split('\n') if line.startswith('HOME_ASSISTANT_TOKEN=')][0]
headers = {'Authorization': 'Bearer ' + token}
data = requests.get('http://192.168.0.56:8123/api/states', headers=headers).json()
for d in data:
    if 'scene' in d['entity_id'] and 'sala' in d['entity_id']:
        print(d['entity_id'])
