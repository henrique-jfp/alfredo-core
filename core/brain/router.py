import logging
import spacy
from typing import Dict, Any, List

from core.brain.skills.base import Skill
from core.brain.skills.time_skill import TimeSkill
from core.brain.skills.weather_skill import WeatherSkill
from core.brain.skills.timer_skill import TimerSkill
from core.brain.skills.list_skill import ListSkill
from core.brain.skills.news_skill import NewsSkill
from core.brain.skills.calendar_skill import CalendarSkill
from core.brain.skills.traffic_skill import TrafficSkill
from core.brain.skills.music_skill import MusicSkill
from core.brain.skills.youtube_skill import YouTubeSkill
from core.brain.skills.fallback_skill import FallbackSkill

logger = logging.getLogger("alfredo.router")

class IntentRouter:
    def __init__(self):
        logger.info("Carregando modelo NLP (Spacy: pt_core_news_sm)...")
        try:
            self.nlp = spacy.load("pt_core_news_sm")
        except OSError:
            logger.warning("Modelo Spacy não encontrado. Baixando em background (ou instale: python -m spacy download pt_core_news_sm). Usando fallback em regex.")
            self.nlp = None
            
        # Registrando Skills Ativas
        self.skills: List[Skill] = [
            TimeSkill(),
            WeatherSkill(),
            TimerSkill(),
            ListSkill(),
            NewsSkill(),
            CalendarSkill(),
            TrafficSkill(),
            MusicSkill(),
            YouTubeSkill(),
            FallbackSkill() # Sempre a última a ser processada
        ]

    def _extract_intent(self, text: str) -> str:
        """
        Analisa o texto e classifica na melhor intent.
        Se nlp estiver disponivel, usa processamento. 
        Senão, usa heurística basica.
        """
        text_lower = text.lower()
        
        # Heurísticas rápidas (O Spacy pode ser usado depois para refinar entidades)
        if "horas" in text_lower or "que dia" in text_lower or "data" in text_lower:
            return "TIME"
            
        if "clima" in text_lower or "tempo" in text_lower or "chover" in text_lower or "temperatura" in text_lower:
            return "WEATHER"
            
        if "cronômetro" in text_lower or "cronometro" in text_lower or "timer" in text_lower or "me avise" in text_lower or "daqui a" in text_lower or "alarme" in text_lower or "acorde" in text_lower or "desperte" in text_lower or "lembrete" in text_lower or "lembre" in text_lower or "lembrar" in text_lower:
            return "TIMER"
            
        if "lista" in text_lower or "anote" in text_lower or "comprar" in text_lower:
            return "LIST"
            
        if "notícia" in text_lower or "noticia" in text_lower or "manchete" in text_lower or "acontecendo" in text_lower:
            return "NEWS"
            
        if "agenda" in text_lower or "compromisso" in text_lower or "reunião" in text_lower or "reuniao" in text_lower or "calendário" in text_lower or "calendario" in text_lower:
            return "CALENDAR"
            
        if "trânsito" in text_lower or "transito" in text_lower or "trabalho" in text_lower or "rota" in text_lower or "viagem" in text_lower:
            return "TRAFFIC"
            
        if "tocar" in text_lower or "toca " in text_lower or "toque " in text_lower or "reproduza" in text_lower or "reproduzir" in text_lower or "pausar" in text_lower or "pare a música" in text_lower or "próxima música" in text_lower or "parar música" in text_lower or "para de tocar" in text_lower:
            # Se for youtube especifico, tem prioridade
            if "youtube" in text_lower or "live da" in text_lower or "live do" in text_lower or "último vídeo" in text_lower or "ultimo video" in text_lower or "canal" in text_lower or "ao vivo" in text_lower:
                return "YOUTUBE"
            return "MUSIC"
            
        if "youtube" in text_lower or "último vídeo" in text_lower or "ultimo video" in text_lower or "canal" in text_lower or "ao vivo" in text_lower:
            return "YOUTUBE"
            
        # TODO: Adicionar heurísticas de Automação (Ligar luz, etc).
        
        return "UNKNOWN"

    def process(self, text: str, context: Dict[str, Any]) -> str:
        """
        Recebe o texto transcrito, acha a intent, executa a skill e retorna a string pro TTS.
        """
        if not text or len(text.strip()) == 0:
            return "Desculpe, não entendi o que você disse."
            
        intent = self._extract_intent(text)
        logger.info(f"Intent identificada: {intent}")
        
        # Procurar skill capaz de resolver
        for skill in self.skills:
            if skill.can_handle(intent, text):
                logger.info(f"Delegando para a Skill: {skill.name}")
                return skill.execute(text, context)
                
        # Se não achou (UNKNOWN), na Etapa 4 passaremos para o LLM.
        # Por enquanto devolvemos um erro elegante.
        logger.warning("Nenhuma skill local pôde resolver.")
        return f"Você disse {text}, mas eu ainda não aprendi a fazer isso."

# Singleton do router
_router_instance = None

def get_router() -> IntentRouter:
    global _router_instance
    if _router_instance is None:
        _router_instance = IntentRouter()
    return _router_instance
