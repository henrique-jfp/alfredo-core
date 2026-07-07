import logging
import time
import requests
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional, List, Tuple
from core.brain.skills.base import Skill

logger = logging.getLogger("alfredo.skills.news")

CACHE_TTL = 300  # 5 minutos

class NewsSkill(Skill):
    def __init__(self):
        self._cache: Optional[Tuple[float, str, List[str]]] = None

    @property
    def name(self) -> str:
        return "NewsSkill"

    def can_handle(self, intent: str, text: str) -> bool:
        return intent == "NEWS"

    def _fetch_headlines(self, url: str) -> List[str]:
        """Busca e parseia feed RSS ou Atom. Retorna lista de títulos (máx 5)."""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()

        root = ET.fromstring(response.content)

        # Tenta RSS 2.0 (<item>) primeiro, depois Atom (<entry>)
        items = root.findall('.//item')
        if not items:
            items = root.findall('.//{http://www.w3.org/2005/Atom}entry')
            if not items:
                items = root.findall('.//entry')

        headlines = []
        for item in items[:5]:
            # RSS: <title>, Atom: <title>
            title_el = item.find('title')
            if title_el is None:
                title_el = item.find('{http://www.w3.org/2005/Atom}title')
            if title_el is not None and title_el.text:
                clean = title_el.text.strip().replace('\n', ' ').replace('\r', '')
                # Remove sufixo comum do G1: " | G1" ou " — G1"
                clean = clean.split('|')[0].split('—')[0].split('–')[0].strip()
                if clean:
                    headlines.append(clean)

        return headlines[:5]

    def _get_cached_or_fetch(self, db, rss_url: str) -> List[str]:
        """Retorna headlines do cache (se válido) ou busca novo."""
        now = time.time()
        if self._cache and (now - self._cache[0]) < CACHE_TTL and self._cache[1] == rss_url:
            logger.info("Usando cache de notícias (válido por 5 min)")
            return self._cache[2]

        headlines = self._fetch_headlines(rss_url)
        self._cache = (now, rss_url, headlines)
        return headlines

    def _format_tts(self, headlines: List[str]) -> str:
        """Formata lista de manchetes em texto TTS conciso."""
        if not headlines:
            return "Não encontrei nenhuma manchete no momento."

        intro = "Aqui estão as principais manchetes. "
        parts = []
        for i, h in enumerate(headlines, 1):
            parts.append(f"{i}... {h}")
        return intro + ". ".join(parts) + "."

    def execute(self, text: str, context: Dict[str, Any]) -> str:
        db = context.get("db")
        if not db:
            return "Erro: banco de dados não disponível."

        from core.brain.memory import models
        settings = db.query(models.Setting).all()
        config = {s.key: s.value for s in settings}
        rss_url = config.get("news_rss_url", "https://g1.globo.com/rss/g1/")

        # Verifica se o usuário pediu uma categoria específica
        text_lower = text.lower()
        category_map = {
            "política": "politica", "politica": "politica",
            "esportes": "esportes", "esporte": "esportes", "futebol": "esportes",
            "economia": "economia", "dinheiro": "economia",
            "mundo": "mundo", "internacional": "mundo", "exterior": "mundo",
            "tecnologia": "tecnologia", "tech": "tecnologia",
            "saúde": "saude", "saude": "saude",
            "cultura": "cultura", "entretenimento": "cultura",
            "ciência": "ciencia", "ciencia": "ciencia"
        }
        for keyword, category in category_map.items():
            if keyword in text_lower:
                rss_url = f"https://g1.globo.com/rss/g1/{category}/"
                break

        try:
            headlines = self._get_cached_or_fetch(db, rss_url)
            return self._format_tts(headlines)
        except requests.exceptions.Timeout:
            logger.error("Timeout ao buscar notícias")
            return "O feed de notícias está demorando muito para responder. Tente novamente mais tarde."
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro de conexão ao buscar notícias: {e}")
            return "Desculpe, não consegui acessar o servidor de notícias no momento."
        except ET.ParseError as e:
            logger.error(f"Erro ao parsear XML do feed: {e}")
            return "O formato do feed de notícias está inválido no momento."
        except Exception as e:
            logger.error(f"Erro inesperado ao buscar notícias: {e}")
            return "Desculpe, ocorreu um erro ao buscar as notícias."

    def execute_tool(self, kwargs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        db = context.get("db")
        if not db:
            return {"error": "Banco de dados indisponível"}

        from core.brain.memory import models
        settings = db.query(models.Setting).all()
        config = {s.key: s.value for s in settings}
        base_url = config.get("news_rss_url", "https://g1.globo.com/rss/g1/")

        category = kwargs.get("category", "").strip().lower()
        valid_categories = ["politica", "esportes", "economia", "mundo", "tecnologia", "saude", "cultura", "ciencia"]
        rss_url = f"https://g1.globo.com/rss/g1/{category}/" if category in valid_categories else base_url

        try:
            headlines = self._get_cached_or_fetch(db, rss_url)
            text = self._format_tts(headlines)
            return {
                "headlines": headlines,
                "direct_response": text
            }
        except Exception as e:
            logger.error(f"Erro no execute_tool do NewsSkill: {e}")
            return {"error": "Não foi possível buscar as notícias."}
