import requests
try:
    print(requests.get('http://127.0.0.1:10001/api/tv/status/ROOM_LIVING').json())
except Exception as e:
    print(e)
