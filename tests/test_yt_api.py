import requests
import json

url = "https://www.youtube.com/youtubei/v1/search"
payload = {
    "context": {
        "client": {
            "clientName": "WEB",
            "clientVersion": "2.20210721.00.00"
        }
    },
    "query": "caze tv",
    "params": "EgJAAQ=="
}

response = requests.post(url, json=payload)
data = response.json()

# O formato da resposta tem várias camadas
contents = data.get('contents', {}).get('twoColumnSearchResultsRenderer', {}).get('primaryContents', {}).get('sectionListRenderer', {}).get('contents', [])
for content in contents:
    items = content.get('itemSectionRenderer', {}).get('contents', [])
    for item in items:
        video = item.get('videoRenderer', {})
        if video:
            print("Title:", video.get('title', {}).get('runs', [{}])[0].get('text'))
            print("Video ID:", video.get('videoId'))
            print("Is Live?", "BADGE_STYLE_TYPE_LIVE_NOW" in str(video.get('badges', [])))
            print("---")
