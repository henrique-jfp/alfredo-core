import logging
import requests
import xml.etree.ElementTree as ET
from typing import Dict, Any
from core.brain.skills.base import Skill

logger = logging.getLogger("alfredo.skills.news")

class NewsSkill(Skill):
    @property
    def name(self) -> str:
        return "NewsSkill"

    def can_handle(self, intent: str, text: str) -> bool:
        return intent == "NEWS"

    def execute(self, text: str, context: Dict[str, Any]) -> str:
        url = "https://g1.globo.com/rss/g1/"
        
        try:
            logger.info("Buscando notícias no feed RSS do G1...")
            # Headers para evitar bloqueio por ser bot
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            
            # Parseia o XML
            root = ET.fromstring(response.content)
            
            # Encontra as primeiras 3 notícias
            items = root.findall('.//item')[:3]
            
            if not items:
                return "Desculpe, não consegui encontrar nenhuma manchete no momento."
                
            headlines = []
            for item in items:
                title = item.find('title')
                if title is not None and title.text:
                    # G1 às vezes coloca traços ou quebras de linha
                    clean_title = title.text.strip()
                    headlines.append(clean_title)
                    
            # Formatar texto para o TTS ler com pausas
            intro = "Aqui estão as principais manchetes de agora. "
            body = " ".join([f"Notícia {i+1}... {headline}." for i, headline in enumerate(headlines)])
            
            return intro + body
            
        except Exception as e:
            logger.error(f"Erro ao buscar notícias: {e}")
            return "Desculpe, estou sem acesso ao servidor de notícias no momento."
