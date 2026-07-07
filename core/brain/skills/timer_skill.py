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
        
        # Mapeamento completo de números por extenso
        text_num = {
            "um": 1, "uma": 1, "dois": 2, "duas": 2, "três": 3, "tres": 3, 
            "quatro": 4, "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9, 
            "dez": 10, "onze": 11, "doze": 12, "treze": 13, "catorze": 14, "quatorze": 14,
            "quinze": 15, "dezesseis": 16, "dezessete": 17, "dezoito": 18, "dezenove": 19,
            "vinte": 20, "trinta": 30, "quarenta": 40, "cinquenta": 50, "sessenta": 60,
            "setenta": 70, "oitenta": 80, "noventa": 90, "cem": 100, "cento": 100
        }
        # Palavras que indicam 30 (meia/meio)
        trinta_words = {"meia", "meio"}
        
        # 1. Tentar capturar horas absolutas (ex: "alarme para as 8 horas")
        is_alarm_intent = (
            "alarme" in text_lower or "acorde" in text_lower or "desperte" in text_lower or
            "despertador" in text_lower or "acordar" in text_lower or "às" in text_lower or
            bool(re.search(r'\bas\s+\d+', text_lower))
        )
        if is_alarm_intent:
            match = re.search(r'(?:às|as|para as)\s+(\d+)(?:\s*[h:](\d+))?(?:\s*horas?|h|da manhã|da tarde|da noite)?', text_lower)
            if match:
                target_hour = int(match.group(1))
                target_minute = int(match.group(2)) if match.group(2) else 0
                if "tarde" in text_lower or "noite" in text_lower:
                    if target_hour < 12:
                        target_hour += 12
                        
                tz = ZoneInfo("America/Sao_Paulo")
                now = datetime.now(tz)
                target_time = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
                
                # Se tem 'amanhã' ou se o horário já passou hoje
                if "amanhã" in text_lower or "amanha" in text_lower or target_time <= now:
                    target_time += timedelta(days=1)
                    
                duration_seconds = int((target_time - now).total_seconds())
                return duration_seconds
                
        # 2. Captura relativa normal
        number = 0

        # 2a. Verifica "meia hora" / "meio minuto" / "meia"
        for mword in trinta_words:
            if re.search(rf'\b{mword}\s+(?:hora|minuto)', text_lower):
                number = 30
                break

        if number == 0:
            # 2b. Tenta captura composta: "vinte e cinco", "trinta e dois"
            tens_order = ["vinte", "trinta", "quarenta", "cinquenta", "sessenta", "setenta", "oitenta", "noventa"]
            comp_match = re.search(
                r'\b(' + '|'.join(tens_order) + r')\s+e\s+(' + '|'.join(
                    [w for w in text_num if text_num[w] < 10 and w not in trinta_words]
                ) + r')\b',
                text_lower
            )
            if comp_match:
                number = text_num[comp_match.group(1)] + text_num[comp_match.group(2)]

        if number == 0:
            # 2c. Tenta extrair dígito
            digit_match = re.search(r'(\d+)', text_lower)
            if digit_match:
                number = int(digit_match.group(1))

        if number == 0:
            # 2d. Por extenso simples
            for word, val in sorted(text_num.items(), key=lambda x: -len(x[0])):
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

        # Cancelamento por voz
        cancel_keywords = ["cancela", "cancelar", "para", "parar", "remove", "remover", "deleta", "deletar"]
        target_keywords = ["timer", "alarme", "lembrete", "cronômetro", "cronometro", "temporizador"]
        is_cancel = any(w in text_lower for w in cancel_keywords) and any(w in text_lower for w in target_keywords)
        if is_cancel:
            timers = db.query(models.Timer).filter(
                models.Timer.is_active == True, models.Timer.room_id == room_id
            ).order_by(models.Timer.expires_at.desc()).all()
            if not timers:
                return "Você não tem nenhum timer ativo para cancelar."

            # Tenta encontrar por mensagem
            message_text = text_lower.replace("cancela", "").replace("cancelar", "").replace("para", "").replace("parar", "").replace("remove", "").replace("remover", "").replace("deleta", "").replace("deletar", "").replace("o", "").replace("a", "").strip()
            found = None
            if message_text:
                for t in timers:
                    if t.message and t.message.lower() in message_text:
                        found = t
                        break
            if not found and timers:
                found = timers[0]  # cancela o mais recente

            if found:
                found.is_active = False
                db.commit()
                label = found.message or f"{'alarme' if found.timer_type == 'alarm' else 'timer'}"
                return f"OK, {label} cancelado."

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
                return {"direct_response": "Você não tem nenhum timer ativo.", "status": "success"}
            names = [f"{t.message or 'timer'}" for t in timers]
            return {
                "active_timers": [{"id": t.id, "type": t.timer_type, "message": t.message, "expires_in_seconds": (t.expires_at - datetime.now(timezone.utc)).total_seconds()} for t in timers],
                "direct_response": f"Você tem {len(timers)} timer ativo: {' e '.join(names)}." if timers else "Nenhum timer ativo.",
                "status": "success"
            }
            
        elif action == "delete":
            timer_id = kwargs.get("timer_id")
            timers = db.query(models.Timer).filter(
                models.Timer.is_active == True, models.Timer.room_id == room_id
            ).order_by(models.Timer.expires_at.desc()).all()
            if not timers:
                return {"error": "Nenhum timer ativo para cancelar.", "status": "fail"}

            found = None
            if timer_id is not None:
                for t in timers:
                    if t.id == timer_id:
                        found = t
                        break
            else:
                # Cancela o mais recente se nenhum ID foi especificado
                found = timers[0]

            if not found:
                return {"error": "Timer não encontrado.", "status": "fail"}

            found.is_active = False
            db.commit()
            label = found.message or f"{'alarme' if found.timer_type == 'alarm' else 'timer'}"
            return {"direct_response": f"OK, {label} cancelado.", "status": "success"}
            
        elif action == "create":
            dur = kwargs.get("duration_seconds")
            target = kwargs.get("target_hour")
            msg = kwargs.get("message", "")
            
            tz = ZoneInfo("America/Sao_Paulo")
            now_sp = datetime.now(tz)
            
            if dur is not None:
                duration_seconds = dur
                is_alarm = False
                expires_at = datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)
            elif target is not None:
                is_alarm = True
                target_hour = int(float(target))
                target_minute = int(float(kwargs.get("target_minute", 0)))
                target_time = now_sp.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
                if target_time <= now_sp:
                    target_time += timedelta(days=1)
                duration_seconds = int((target_time - now_sp).total_seconds())
                expires_at = target_time.astimezone(timezone.utc)
            else:
                return {"error": "Faltam parâmetros de tempo"}
                
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
                
            if msg:
                direct = f"Combinado, vou te lembrar de {msg}."
            elif is_alarm:
                direct = f"Alarme configurado para {target_hour}:{target_minute:02d}."
            elif duration_seconds < 60:
                direct = f"Timer de {duration_seconds} segundos iniciado."
            elif duration_seconds < 3600:
                direct = f"Timer de {duration_seconds // 60} minutos iniciado."
            else:
                direct = f"Timer de {duration_seconds // 3600} horas iniciado."
            return {
                "status": "success",
                "type": "alarm" if is_alarm else "timer",
                "duration_seconds": duration_seconds,
                "message": msg,
                "direct_response": direct
            }
