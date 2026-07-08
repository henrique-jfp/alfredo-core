import requests

pat = '7fba416a-bdae-40b8-bf0d-8ecb83bf5d44'
device_id = '9254e132-ec14-186d-a217-04e978a30efd'

url = f"https://api.smartthings.com/v1/devices/{device_id}/commands"
headers = {"Authorization": f"Bearer {pat}"}
payload = {"commands": [{"component": "main", "capability": "switch", "command": "on"}]}

print(f"Enviando para {url}")
response = requests.post(url, headers=headers, json=payload, timeout=5)
print("Status Code:", response.status_code)
print("Response Text:", response.text)
