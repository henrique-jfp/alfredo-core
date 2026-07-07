import re
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Dict, Any, List
from core.brain.skills.base import Skill
from core.brain.memory import models

logger = logging.getLogger("alfredo.skills.calendar")

TZ = ZoneInfo("America/Sao_Paulo")

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

        # Cancelamento/remoção por voz
        if any(w in text_lower for w in ["cancele", "cancelar", "remova", "remover", "apague", "apagar", "exclua", "excluir"]) and \
           any(w in text_lower for w in ["compromisso", "evento", "agenda", "compromisso"]):
            return self._remove_event(db, room_id, text_lower)

        # Identifica a ação
        add_keywords = ["adicione", "adicionar", "marque", "marcar", "anote", "anotar", "agende", "agendar", "crie", "criar"]
        if any(w in text_lower for w in add_keywords):
            return self._add_event(db, room_id, text_lower)
        else:
            return self._read_events(db, room_id, text_lower)

    def _read_events(self, db, room_id, text_lower) -> str:
        target_date = datetime.now(TZ)
        day_str = "hoje"
        if "amanhã" in text_lower or "amanha" in text_lower:
            target_date += timedelta(days=1)
            day_str = "amanhã"
        elif "depois" in text_lower:
            target_date += timedelta(days=2)
            day_str = "depois de amanhã"

        start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
        end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=999999).astimezone(timezone.utc)

        events = db.query(models.Event).filter(
            models.Event.room_id == room_id,
            models.Event.start_time >= start_of_day,
            models.Event.start_time <= end_of_day
        ).order_by(models.Event.start_time.asc()).all()

        if not events:
            return f"Você não tem nenhum compromisso marcado para {day_str}."

        itens = []
        for e in events:
            local_time = e.start_time.astimezone(TZ)
            hora_str = local_time.strftime("%H:%M").replace(":00", " horas")
            itens.append(f"{e.title} às {hora_str}")

        if len(itens) > 1:
            texto = ", ".join(itens[:-1]) + " e " + itens[-1]
        else:
            texto = itens[0]

        return f"Para {day_str} você tem: {texto}."

    def _add_event(self, db, room_id, text_lower) -> str:
        # Captura hora e minuto: "às 14h30", "as 8:15", "para as 7h"
        match_time = re.search(r'(?:às|as|para as)\s+(\d+)(?:\s*[h:](\d+))?(?:\s*horas?|h)?', text_lower)
        if not match_time:
            return "Por favor, diga o horário do compromisso. Por exemplo: marque dentista amanhã às 14 horas."

        target_hour = int(match_time.group(1))
        target_minute = int(match_time.group(2)) if match_time.group(2) else 0

        now = datetime.now(TZ)
        target_date = now
        day_str = "hoje"

        if "amanhã" in text_lower or "amanha" in text_lower:
            target_date += timedelta(days=1)
            day_str = "amanhã"
        elif "depois" in text_lower:
            target_date += timedelta(days=2)
            day_str = "depois de amanhã"

        target_time = target_date.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)

        # Se o horário já passou, empurra para o dia seguinte
        if day_str == "hoje" and target_time <= now:
            target_time += timedelta(days=1)
            day_str = "amanhã"

        # Extrai o título: remove verbo, data, hora — o que sobra é o título
        title = text_lower
        for prefix in ["adicione", "adicionar", "marque", "marcar", "anote", "anotar", "agende", "agendar", "crie", "criar"]:
            title = re.sub(r'^' + prefix + r'\s+', '', title, flags=re.IGNORECASE)
        # Remove "para" no início
        title = re.sub(r'^para\s+', '', title)
        # Remove "amanhã", "hoje", "depois de amanhã", "depois"
        title = re.sub(r'\s*depois\s+de\s+amanhã', '', title)
        title = re.sub(r'\s*(amanhã|amanha|hoje)\s*', ' ', title)
        # Remove horário "às 14h30", "as 8:15", "para as 7h"
        title = re.sub(r'\s*(?:para\s+)?(?:às|as)\s+\d+(?::\d+)?(?:\s*horas?|h)?', '', title)
        # Remove "para" solto no final
        title = re.sub(r'\s+para\s*$', '', title)
        # Limpa espaços extras
        title = re.sub(r'\s+', ' ', title).strip()

        if not title:
            return "Não entendi o nome do compromisso."

        start_utc = target_time.astimezone(timezone.utc)

        new_event = models.Event(
            title=title,
            start_time=start_utc,
            room_id=room_id
        )
        db.add(new_event)
        db.commit()

        logger.info(f"Compromisso '{title}' adicionado para {day_str} às {target_hour}:{target_minute:02d}")
        return f"Adicionei o compromisso {title} na sua agenda para {day_str} às {target_hour}:{target_minute:02d}."

    def _remove_event(self, db, room_id, text_lower) -> str:
        events = db.query(models.Event).filter(
            models.Event.room_id == room_id,
            models.Event.start_time >= datetime.now(timezone.utc)
        ).order_by(models.Event.start_time.asc()).all()

        if not events:
            return "Você não tem nenhum compromisso futuro para cancelar."

        # Tenta encontrar pelo título
        for keyword in ["cancele", "cancelar", "remova", "remover", "apague", "apagar", "exclua", "excluir"]:
            text_lower = text_lower.replace(keyword, "")
        for keyword in ["o", "a", "compromisso", "evento", "da", "de", "agenda"]:
            text_lower = text_lower.replace(keyword, "")
        search = text_lower.strip()

        found = None
        if search:
            for e in events:
                if search in e.title.lower():
                    found = e
                    break

        if not found:
            # Cancela o primeiro (mais próximo)
            found = events[0]

        title = found.title
        db.delete(found)
        db.commit()
        return f"Pronto, cancelei o compromisso {title} da sua agenda."

    def execute_tool(self, kwargs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        db = context.get("db")
        room_id = context.get("room_id")
        action = kwargs.get("action")

        if not db or not room_id:
            return {"error": "Sem contexto de banco ou sala"}

        if action == "read":
            date_ref = kwargs.get("date", "hoje").lower()

            now = datetime.now(TZ)
            target_date = now
            day_str = "hoje"
            if date_ref in ("amanhã", "amanha"):
                target_date += timedelta(days=1)
                day_str = "amanhã"
            elif date_ref in ("depois", "depois de amanhã"):
                target_date += timedelta(days=2)
                day_str = "depois de amanhã"

            start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
            end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=999999).astimezone(timezone.utc)

            events = db.query(models.Event).filter(
                models.Event.room_id == room_id,
                models.Event.start_time >= start_of_day,
                models.Event.start_time <= end_of_day
            ).order_by(models.Event.start_time.asc()).all()

            if not events:
                return {
                    "events": [],
                    "direct_response": f"Você não tem nenhum compromisso marcado para {day_str}."
                }

            event_list = []
            for e in events:
                local_time = e.start_time.astimezone(TZ)
                event_list.append({
                    "id": e.id,
                    "title": e.title,
                    "start_time": local_time.isoformat()
                })

            if len(event_list) > 1:
                names = ", ".join([ev["title"] for ev in event_list[:-1]]) + " e " + event_list[-1]["title"]
            else:
                names = event_list[0]["title"]

            return {
                "events": event_list,
                "direct_response": f"Para {day_str} você tem: {names}."
            }

        elif action == "add":
            title = kwargs.get("title", "").strip()
            start_iso = kwargs.get("start_time", "").strip()

            if not title:
                return {"error": "Título do compromisso é obrigatório."}

            if start_iso:
                try:
                    start_dt = datetime.fromisoformat(start_iso)
                    if start_dt.tzinfo is None:
                        start_dt = start_dt.replace(tzinfo=TZ)
                    start_utc = start_dt.astimezone(timezone.utc)
                except ValueError:
                    return {"error": f"Formato de data inválido: {start_iso}"}
            else:
                now = datetime.now(TZ)
                start_utc = now.astimezone(timezone.utc)

            new_event = models.Event(
                title=title,
                start_time=start_utc,
                room_id=room_id
            )
            db.add(new_event)
            db.commit()

            local_time = start_utc.astimezone(TZ)
            return {
                "status": "success",
                "event": {"id": new_event.id, "title": title, "start_time": local_time.isoformat()},
                "direct_response": f"Adicionei o compromisso {title} na sua agenda."
            }

        elif action == "remove":
            event_id = kwargs.get("event_id")
            title_search = kwargs.get("title", "").strip().lower()

            events = db.query(models.Event).filter(
                models.Event.room_id == room_id,
                models.Event.start_time >= datetime.now(timezone.utc)
            ).order_by(models.Event.start_time.asc()).all()

            found = None
            if event_id is not None:
                for e in events:
                    if e.id == event_id:
                        found = e
                        break
            elif title_search:
                for e in events:
                    if title_search in e.title.lower():
                        found = e
                        break

            if not found:
                return {"error": "Compromisso não encontrado.", "status": "fail"}

            title = found.title
            db.delete(found)
            db.commit()
            return {"direct_response": f"Pronto, cancelei o compromisso {title}.", "status": "success"}

        return {"error": "Ação desconhecida. Use add, read ou remove."}
