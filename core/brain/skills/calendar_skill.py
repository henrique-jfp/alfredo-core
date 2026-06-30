import re
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from core.brain.skills.base import Skill
from core.brain.memory import models

logger = logging.getLogger("alfredo.skills.calendar")

class CalendarSkill(Skill):
    @property
    def name(self) -> str:
        return "CalendarSkill"

    def can_handle(self, intent: str, text: str) -> bool:
        return intent == "CALENDAR"

    def execute(self, text: str, context: Dict[str, Any]) -> str:
        db = context.get("db")
        room_id = context.get("room_id")
        text_lower = text.lower()
        
        if not db or not room_id:
            return "Desculpe, não consegui acessar o banco de dados da agenda."

        # Identifica a ação (adicionar ou ler)
        if "adicione" in text_lower or "marque" in text_lower or "anote" in text_lower or "agende" in text_lower:
            return self._add_event(db, room_id, text_lower, text)
        else:
            return self._read_events(db, room_id, text_lower)

    def _read_events(self, db, room_id, text_lower) -> str:
        # Define o dia a buscar
        target_date = datetime.now()
        day_str = "hoje"
        if "amanhã" in text_lower or "amanha" in text_lower:
            target_date += timedelta(days=1)
            day_str = "amanhã"
            
        start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        events = db.query(models.Event).filter(
            models.Event.room_id == room_id,
            models.Event.start_time >= start_of_day,
            models.Event.start_time <= end_of_day
        ).order_by(models.Event.start_time.asc()).all()
        
        if not events:
            return f"Você não tem nenhum compromisso marcado para {day_str}."
            
        itens = []
        for e in events:
            hora = e.start_time.strftime("%H e %M").replace(" e 00", " horas")
            itens.append(f"{e.title} às {hora}")
            
        # Formatar
        if len(itens) > 1:
            texto = ", ".join(itens[:-1]) + " e " + itens[-1]
        else:
            texto = itens[0]
            
        return f"Para {day_str} você tem: {texto}."

    def _add_event(self, db, room_id, text_lower, original_text) -> str:
        # Ex: adicione dentista amanhã às 14 horas
        match_time = re.search(r'(?:às|as|para as)\s+(\d+)(?:\s*horas?|h)?', text_lower)
        if not match_time:
            return "Por favor, diga o horário do compromisso. Por exemplo: marque dentista amanhã às 14 horas."
            
        target_hour = int(match_time.group(1))
        
        target_date = datetime.now()
        day_str = "hoje"
        if "amanhã" in text_lower or "amanha" in text_lower:
            target_date += timedelta(days=1)
            day_str = "amanhã"
            
        target_time = target_date.replace(hour=target_hour, minute=0, second=0, microsecond=0)
        
        # Extrair o título
        # "adicione dentista amanhã às 14 horas" -> "dentista"
        match_title = re.search(r'(?:adicione|marque|anote|agende)\s+(.*?)\s+(?:para|hoje|amanhã|amanha|às|as)', text_lower)
        if not match_title:
            return "Não entendi o nome do compromisso."
            
        title = match_title.group(1).strip()
        
        new_event = models.Event(
            title=title,
            start_time=target_time,
            room_id=room_id
        )
        db.add(new_event)
        db.commit()
        
        logger.info(f"Compromisso '{title}' adicionado para {day_str} às {target_hour}h")
        return f"Adicionei o compromisso {title} na sua agenda para {day_str} às {target_hour} horas."
