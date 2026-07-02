import re
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Dict, Any
from core.brain.skills.base import Skill
from core.brain.memory import models

logger = logging.getLogger("alfredo.skills.timer")

class TimerSkill(Skill):
    @property
    def name(self) -> str:
        return "TimerSkill"

    def can_handle(self, intent: str, text: str) -> bool:
        return intent == "TIMER"

    def _extract_duration_or_absolute(self, text: str) -> int:
        """Extrai a duração em segundos (relativo) ou calcula diferença até horário (absoluto)."""
        text_lower = text.lower()
        
        # Mapeamento básico de números por extenso
        text_num = {
            "um": 1, "uma": 1, "dois": 2, "duas": 2, "três": 3, "tres": 3, 
            "quatro": 4, "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9, 
            "dez": 10, "onze": 11, "doze": 12, "quinze": 15, "vinte": 20, 
            "trinta": 30, "quarenta": 40, "cinquenta": 50, "sessenta": 60
        }
        
        # 1. Tentar capturar horas absolutas (ex: "alarme para as 8 horas")
        is_alarm_intent = "alarme" in text_lower or "acorde" in text_lower or "desperte" in text_lower or "às" in text_lower or "as" in text_lower
        if is_alarm_intent:
            match = re.search(r'(?:às|as|para as)\s+(\d+)(?:\s*horas?|h|da manhã|da tarde|da noite)?', text_lower)
            if match:
                target_hour = int(match.group(1))
                if "tarde" in text_lower or "noite" in text_lower:
                    if target_hour < 12:
                        target_hour += 12
                        
                tz = ZoneInfo("America/Sao_Paulo")
                now = datetime.now(tz)
                target_time = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
                
                # Se tem 'amanhã' ou se o horário já passou hoje
                if "amanhã" in text_lower or "amanha" in text_lower or target_time <= now:
                    target_time += timedelta(days=1)
                    
                duration_seconds = int((target_time - now).total_seconds())
                return duration_seconds
                
        # 2. Captura relativa normal
        number = 0
        digit_match = re.search(r'(\d+)', text_lower)
        if digit_match:
            number = int(digit_match.group(1))
        else:
            for word, val in text_num.items():
                if re.search(rf'\b{word}\b', text_lower):
                    number = val
                    break
        
        if number == 0:
            return 0
            
        if "segundo" in text_lower:
            seconds = number
        elif "hora" in text_lower:
            seconds = number * 3600
        else:
            seconds = number * 60
            
        return seconds
        
    def _extract_message(self, text: str) -> str:
        """Extrai a mensagem do lembrete, se houver."""
        text_lower = text.lower()
        match = re.search(r'(?:lembra de|lembre de|lembrar de|lembrete de)\s+(.*?)(?:\s+(?:daqui a|em|às|as|para as|amanhã|amanha)\b|$)', text_lower)
        if match:
            return match.group(1).strip()
        return None

    def execute(self, text: str, context: Dict[str, Any]) -> str:
        db = context.get("db")
        room_id = context.get("room_id")
        text_lower = text.lower()
        
        if not db or not room_id:
            logger.error("Contexto sem DB ou room_id na TimerSkill")
            return "Desculpe, não consegui acessar o banco de dados para criar o temporizador."
            
        if "quais" in text_lower and "lembrete" in text_lower:
            timers = db.query(models.Timer).filter(models.Timer.is_active == True, models.Timer.room_id == room_id).all()
            if not timers:
                return "Você não tem nenhum lembrete ou alarme ativo."
            
            resp = []
            for t in timers:
                resp.append(f"um {'alarme' if t.timer_type == 'alarm' else 'lembrete'} para {t.message or 'avisar o tempo'}")
            return "Você tem " + ", ".join(resp) + "."
            
        duration_seconds = self._extract_duration_or_absolute(text)
        
        if duration_seconds == 0:
            logger.warning(f"Não foi possível extrair a duração do texto: '{text}'")
            return "Desculpe, não consegui ouvir bem o horário ou tempo. De quantos minutos você precisa ou para que horas?"
            
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)
        
        reminder_msg = self._extract_message(text)
        
        is_alarm = "alarme" in text_lower or "acorde" in text_lower or "desperte" in text_lower or "às" in text_lower
        
        new_timer = models.Timer(
            room_id=room_id,
            duration_seconds=duration_seconds,
            expires_at=expires_at,
            message=reminder_msg,
            timer_type="alarm" if is_alarm else "timer",
            is_active=True
        )
        db.add(new_timer)
        db.commit()
        
        # Injetar notificação na fila de websockets do router
        ws_tasks = context.get("ws_tasks")
        device_id = context.get("device_id")
        if ws_tasks is not None and device_id:
            ws_tasks.append({
                "device_id": device_id,
                "payload": {
                    "type": "timer_start",
                    "duration_seconds": duration_seconds,
                    "message": reminder_msg or "Timer iniciado"
                }
            })
        
        logger.info(f"Timer criado para a sala {room_id} (Duração: {duration_seconds}s)")
        
        if reminder_msg:
            return f"Combinado! Vou te lembrar de {reminder_msg}."
        elif is_alarm:
            target_dt = datetime.now(ZoneInfo("America/Sao_Paulo")) + timedelta(seconds=duration_seconds + 5)
            return f"Entendido, alarme configurado para às {target_dt.hour} horas."
        else:
            # Formata o tempo para a resposta falada
            if duration_seconds < 60:
                time_str = f"{duration_seconds} segundos"
            elif duration_seconds < 3600:
                mins = duration_seconds // 60
                time_str = f"{mins} minuto{'s' if mins > 1 else ''}"
            else:
                hrs = duration_seconds // 3600
                time_str = f"{hrs} hora{'s' if hrs > 1 else ''}"
                
                
            return f"Entendido, cronômetro de {time_str} iniciado."

    def execute_tool(self, kwargs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        db = context.get("db")
        room_id = context.get("room_id")
        action = kwargs.get("action")
        
        if not db or not room_id:
            return {"error": "Sem contexto de banco ou sala"}
            
        if action == "list":
            timers = db.query(models.Timer).filter(models.Timer.is_active == True, models.Timer.room_id == room_id).all()
            if not timers:
                return {"message": "Nenhum timer ativo"}
            return {"active_timers": [{"id": t.id, "type": t.timer_type, "message": t.message, "expires_in_seconds": (t.expires_at - datetime.now(timezone.utc)).total_seconds()} for t in timers]}
            
        elif action == "delete":
            return {"error": "Deleção via voz não está autorizada por enquanto, instrua o usuário a usar o painel web."}
            
        elif action == "create":
            dur = kwargs.get("duration_seconds")
            target = kwargs.get("target_hour")
            msg = kwargs.get("message", "")
            
            tz = ZoneInfo("America/Sao_Paulo")
            now_sp = datetime.now(tz)
            
            if dur is not None:
                duration_seconds = dur
                is_alarm = False
            elif target is not None:
                is_alarm = True
                target_time = now_sp.replace(hour=target, minute=0, second=0, microsecond=0)
                if target_time <= now_sp:
                    target_time += timedelta(days=1)
                duration_seconds = int((target_time - now_sp).total_seconds())
            else:
                return {"error": "Faltam parâmetros de tempo"}
                
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)
            
            new_timer = models.Timer(
                room_id=room_id,
                duration_seconds=duration_seconds,
                expires_at=expires_at,
                message=msg,
                timer_type="alarm" if is_alarm else "timer",
                is_active=True
            )
            db.add(new_timer)
            db.commit()
            
            ws_tasks = context.get("ws_tasks")
            device_id = context.get("device_id")
            if ws_tasks is not None and device_id:
                ws_tasks.append({
                    "device_id": device_id,
                    "payload": {
                        "type": "timer_start",
                        "duration_seconds": duration_seconds,
                        "message": msg or "Timer iniciado"
                    }
                })
                
            return {
                "status": "success",
                "type": "alarm" if is_alarm else "timer",
                "duration_seconds": duration_seconds,
                "message": msg
            }
