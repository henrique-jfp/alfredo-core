import re
import json
import logging
import unicodedata
from typing import Optional, Dict, Any

import yt_dlp
import requests

logger = logging.getLogger("alfredo.youtube_service")

YDL_OPTS = {
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
    'noplaylist': True,
}

LIVE_SEARCH_URL = "https://www.youtube.com/youtubei/v1/search"
LIVE_SEARCH_PARAMS = "EgJAAQ=="


def _normalize(s: str) -> str:
    if not s:
        return ""
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return s.replace(" ", "").lower()


def _search_live_api(query: str) -> Optional[str]:
    payload = {
        "context": {
            "client": {
                "clientName": "WEB",
                "clientVersion": "2.20241201.00.00"
            }
        },
        "query": query,
        "params": LIVE_SEARCH_PARAMS,
    }

    try:
        resp = requests.post(LIVE_SEARCH_URL, json=payload, timeout=5)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning(f"Live API request failed: {e}")
        return None

    try:
        candidates = []
        contents = (
            data.get('contents', {})
            .get('twoColumnSearchResultsRenderer', {})
            .get('primaryContents', {})
            .get('sectionListRenderer', {})
            .get('contents', [])
        )
        for content in contents:
            items = content.get('itemSectionRenderer', {}).get('contents', [])
            for item in items:
                video = item.get('videoRenderer', {})
                if video:
                    v_id = video.get('videoId')
                    title = video.get('title', {}).get('runs', [{}])[0].get('text', '').lower()
                    uploader = video.get('ownerText', {}).get('runs', [{}])[0].get('text', '').lower()
                    if v_id:
                        candidates.append({"id": v_id, "title": title, "uploader": uploader})

        if not candidates:
            return None

        norm_query = _normalize(query)
        best_match = None
        best_score = -1

        for c in candidates:
            score = 0
            if norm_query and norm_query in _normalize(c['uploader']):
                score += 100
            if norm_query and norm_query in _normalize(c['title']):
                score += 20
            if score > best_score:
                best_score = score
                best_match = c

        if best_match and best_score > 0:
            return f"https://www.youtube.com/watch?v={best_match['id']}"

    except Exception as e:
        logger.warning(f"Live API parse failed: {e}")

    return None


def search_audio(query: str, is_live: bool = False) -> Optional[Dict[str, Any]]:
    if is_live:
        url = _search_live_api(query)
        if url:
            logger.info(f"Live API encontrou: {url}")
            return _extract_audio(url)
        logger.info("Live API não encontrou resultado, fallback para yt-dlp search")

    search_url = f"ytsearch1:{query}"

    try:
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(search_url, download=False)

            if 'entries' in info and len(info['entries']) > 0:
                entry = info['entries'][0]
            else:
                entry = info

            if not entry or not entry.get('url'):
                return None

            return {
                "title": entry.get('title', 'Vídeo Desconhecido'),
                "url": entry.get('url'),
            }
    except Exception as e:
        logger.error(f"yt-dlp error: {e}")
        return None


def _extract_audio(url: str) -> Optional[Dict[str, Any]]:
    try:
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info or not info.get('url'):
                return None
            return {
                "title": info.get('title', 'Vídeo Desconhecido'),
                "url": info.get('url'),
            }
    except Exception as e:
        logger.error(f"yt-dlp extract error: {e}")
        return None


def is_ambiguous_query(query: str) -> bool:
    normalized = re.sub(r"\s+", " ", query).strip().lower()
    ambiguous = {
        "ultimo video", "ultimo video do youtube", "video do youtube",
        "youtube", "musica", "tocar", "toca", "play",
    }
    return normalized in ambiguous or len(normalized) < 4
