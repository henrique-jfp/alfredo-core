import re
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Dict, Any, List, Optional, Tuple
import dateparser
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
        if any(w in text_lower for w in ["cancele", "cancelar", "remova", "remover", "apague", "apagar", "exclua", "excluir"]):
            return self._remove_event(db, room_id, text_lower)

        # Reagendamento por voz
        move_keywords = ["mova", "mover", "move", "remarque", "reagende", "reagendar", "reagenda",
                         "adia", "adiar", "empurra", "empurrar", "adianta", "adiantar"]
        if any(w in text_lower for w in move_keywords):
            return self._reschedule_event(db, room_id, text_lower)

        # Identifica a ação
        add_keywords = ["adicione", "adicionar", "marque", "marcar", "anote", "anotar", "agende", "agendar", "crie", "criar"]
        if any(w in text_lower for w in add_keywords):
            return self._add_event(db, room_id, text_lower)
        else:
            return self._read_events(db, room_id, text_lower)

    def _read_events(self, db, room_id, text_lower) -> str:
        now = datetime.now(TZ)
        resolved = self._resolve_date(text_lower)
        if resolved:
            target_date, day_str = resolved
        else:
            target_date = now
            day_str = "hoje"

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

    @staticmethod
    def _resolve_date(text: str) -> Optional[Tuple[datetime, str]]:
        """Extrai referência de data de um texto em pt-BR.

        Retorna (datetime_inicio_do_dia, descricao) ou None.
        Ex: "próxima terça" → (datetime, "próxima terça")
        """
        now = datetime.now(TZ)
        text_lower = text.lower().strip()

        # 1. "depois de amanhã" — dateparser interpreta como "amanhã" (errado)
        m = re.search(r"depois\s+de\s+amanh[ãa]", text_lower)
        if m:
            return (now + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0), "depois de amanhã"

        # 2. Remove time patterns (às 14h, as 15:30) so dateparser doesn't confuse numbers
        clean_for_dp = re.sub(
            r"(?:às|as)\s+\d{1,2}(?:\s*[h:]\s*\d{1,2})?(?:\s*horas?|h)?",
            "", text_lower
        )

        # 3. dateparser.search — encontra datas no meio do texto
        try:
            from dateparser.search import search_dates
            results = search_dates(clean_for_dp, languages=["pt"], settings={
                "PREFER_DATES_FROM": "future",
                "RELATIVE_BASE": now,
                "TIMEZONE": "America/Sao_Paulo",
            })
            if results:
                fragment, dt = results[0]
                if isinstance(dt, datetime):
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=TZ)
                    desc = fragment.strip()
                    return dt.replace(hour=0, minute=0, second=0, microsecond=0), desc
        except Exception:
            pass

        # 4. Fallback manual para expressões que dateparser pode perder

        # "amanhã"
        if re.search(r"\bamanh[ãa]\b", text_lower):
            return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0), "amanhã"

        # "hoje"
        if re.search(r"\bhoje\b", text_lower):
            return now.replace(hour=0, minute=0, second=0, microsecond=0), "hoje"

        weekday_map = {
            "segunda": 0, "terça": 1, "terca": 1, "quarta": 2,
            "quinta": 3, "sexta": 4, "sábado": 5, "sabado": 5, "domingo": 6,
        }
        for name, num in weekday_map.items():
            pat = rf"(?:pr[óo]xima?|que\s+vem)\s+{re.escape(name)}"
            if re.search(pat, text_lower):
                days = num - now.weekday()
                if days <= 0:
                    days += 7
                return (now + timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0), f"próxima {name}"
            # Dia da semana "solta": "sexta"
            if re.search(rf"(?<![a-z]){re.escape(name)}(?![a-z])", text_lower):
                if not re.search(r"(?:pr[óo]xima?|que\s+vem)", text_lower):
                    days = num - now.weekday()
                    if days <= 0:
                        days += 7
                    return (now + timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0), name

        # "daqui a X dias"
        m = re.search(r"daqui\s+a\s+(\d+)\s+(?:dia|dias)", text_lower)
        if m:
            return (now + timedelta(days=int(m.group(1)))).replace(hour=0, minute=0, second=0, microsecond=0), f"daqui a {m.group(1)} dias"

        # "daqui a X semanas"
        m = re.search(r"daqui\s+a\s+(\d+)\s+(?:semana|semanas)", text_lower)
        if m:
            return (now + timedelta(weeks=int(m.group(1)))).replace(hour=0, minute=0, second=0, microsecond=0), f"daqui a {m.group(1)} semanas"

        # "mês que vem"
        if re.search(r"m[eê]s\s+que\s+vem", text_lower):
            proximo = (now.replace(day=1) + timedelta(days=35)).replace(day=1)
            return proximo.replace(hour=0, minute=0, second=0, microsecond=0), "mês que vem"

        # "semana que vem" / "próxima semana"
        if re.search(r"(?:semana|pr[óo]xima)\s+que\s+vem", text_lower) or re.search(r"pr[óo]xima\s+semana", text_lower):
            days = 7 - now.weekday()
            return (now + timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0), "semana que vem"

        return None

    @staticmethod
    def _parse_reminders(text_lower: str) -> str:
        match = re.search(
            r'(?:e\s+)?(?:me\s+)?lembr(?:e|ar)\s+(?:com\s+)?(.+?)(?:\s+antes\s*)?$',
            text_lower
        )
        if not match:
            return "60"

        reminder_text = match.group(1)
        values = []
        for part in re.split(r'[,;]|\s+e\s+', reminder_text):
            part = part.strip()
            m = re.match(r'(\d+)\s*(?:h(?:ora)?s?|minuto?s?|min)?', part)
            if m:
                num = int(m.group(1))
                if 'h' in part or 'hora' in part:
                    values.append(str(num * 60))
                else:
                    values.append(str(num))
            elif 'hora' in part:
                m2 = re.search(r'(\d+)', part)
                if m2:
                    values.append(str(int(m2.group(1)) * 60))

        if not values:
            return "60"
        return ",".join(values)

    def _add_event(self, db, room_id, text_lower) -> str:
        match_time = re.search(r'(?:às|as|para as)\s+(\d+)(?:\s*[h:](\d+))?(?:\s*horas?|h)?', text_lower)
        if not match_time:
            return "Por favor, diga o horário do compromisso. Por exemplo: marque dentista amanhã às 14 horas."

        target_hour = int(match_time.group(1))
        target_minute = int(match_time.group(2)) if match_time.group(2) else 0

        now = datetime.now(TZ)
        resolved = self._resolve_date(text_lower)
        if resolved:
            target_date, day_str = resolved
        else:
            target_date = now
            day_str = "hoje"

        target_time = target_date.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)

        if day_str == "hoje" and target_time <= now:
            target_time += timedelta(days=1)
            day_str = "amanhã"

        reminders_str = self._parse_reminders(text_lower)

        title = text_lower
        if resolved:
            title = re.sub(re.escape(day_str), "", title, flags=re.IGNORECASE)
        for prefix in ["adicione", "adicionar", "marque", "marcar", "anote", "anotar", "agende", "agendar", "crie", "criar"]:
            title = re.sub(r'^' + prefix + r'\s+', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\s*depois\s+de\s+amanhã', '', title)
        title = re.sub(r'\s*(amanhã|amanha|hoje)\s*', ' ', title)
        title = re.sub(r'\s*(?:para\s+)?(?:às|as)\s+\d+(?::\d+)?(?:\s*horas?|h)?', '', title)
        title = re.sub(r'\s+e\s+me\s+lembr(?:e|ar)\s+.+?antes', '', title)
        title = re.sub(r'\s+para\s*$', '', title)
        title = re.sub(r'\s+', ' ', title).strip()

        if not title:
            return "Não entendi o nome do compromisso."

        start_utc = target_time.astimezone(timezone.utc)

        # Conflito de agenda
        conflicts = self._check_conflict(db, room_id, start_utc)
        if conflicts:
            lista = []
            for c in conflicts:
                lista.append(f"'{c['title']}' às {c['start_time']}")
            if len(lista) == 1:
                msg = f"Você já tem {lista[0]} neste horário. Deseja substituir, manter ambos ou alterar o horário?"
            else:
                msg = f"Você já tem compromissos neste horário: {', '.join(lista[:-1])} e {lista[-1]}. Deseja substituir, manter todos ou alterar o horário?"
            return msg

        new_event = models.Event(
            title=title,
            start_time=start_utc,
            room_id=room_id,
            reminders=reminders_str
        )
        db.add(new_event)
        db.commit()

        from core.services.scheduler import wakeup_scheduler
        wakeup_scheduler()

        reminders_desc = self._format_reminders_desc(reminders_str)
        logger.info(f"Compromisso '{title}' adicionado para {day_str} às {target_hour}:{target_minute:02d} (lembretes: {reminders_str})")
        return f"Adicionei o compromisso {title} na sua agenda para {day_str} às {target_hour}:{target_minute:02d}.{reminders_desc}"

    @staticmethod
    def _check_conflict(db, room_id: str, start_utc: datetime, exclude_title: str = "") -> List[Dict]:
        """Busca eventos num raio de 60min do horário proposto.
        Retorna lista de dicts com {title, start_time} dos conflitos."""
        window_start = start_utc - timedelta(minutes=60)
        window_end = start_utc + timedelta(minutes=60)

        conflicts = db.query(models.Event).filter(
            models.Event.room_id == room_id,
            models.Event.start_time >= window_start,
            models.Event.start_time <= window_end,
        ).order_by(models.Event.start_time.asc()).all()

        result = []
        for ev in conflicts:
            if exclude_title and ev.title.lower() == exclude_title.lower():
                continue
            local = ev.start_time.astimezone(TZ)
            result.append({
                "title": ev.title,
                "start_time": local.strftime("%H:%M"),
            })
        return result

    @staticmethod
    def _format_reminders_desc(reminders_str: str) -> str:
        parts = [int(r.strip()) for r in reminders_str.split(",") if r.strip().isdigit()]
        if not parts or parts == [60]:
            return ""
        labels = []
        for p in parts:
            if p >= 1440:
                labels.append(f"{p // 1440} dia{'s' if p // 1440 > 1 else ''}")
            elif p == 60:
                labels.append("1 hora")
            else:
                labels.append(f"{p} minutos")
        if len(labels) == 1:
            return f" Vou lembrar você {labels[0]} antes."
        desc = ", ".join(labels[:-1]) + " e " + labels[-1]
        return f" Vou lembrar você {desc} antes."

    def _find_events_by_title(self, events, search: str) -> list:
        """Retorna todos os eventos cujo título contém todos os termos da busca."""
        terms = [t for t in search.split() if t not in ("o", "a", "os", "as", "de", "da", "do", "das", "dos", "para")]
        if not terms:
            return []
        results = []
        for e in events:
            title_lower = e.title.lower()
            if all(t in title_lower for t in terms):
                results.append(e)
        return results

    def _remove_event(self, db, room_id, text_lower) -> str:
        events = db.query(models.Event).filter(
            models.Event.room_id == room_id,
            models.Event.start_time >= datetime.now(timezone.utc)
        ).order_by(models.Event.start_time.asc()).all()

        if not events:
            return "Você não tem nenhum compromisso futuro para cancelar."

        # Limpa a busca
        for keyword in ["cancele", "cancelar", "remova", "remover", "apague", "apagar", "exclua", "excluir"]:
            text_lower = text_lower.replace(keyword, "")
        for keyword in ["o", "a", "compromisso", "evento", "da", "de", "agenda"]:
            text_lower = text_lower.replace(keyword, "")
        search = text_lower.strip()

        if search:
            candidates = self._find_events_by_title(events, search)
        else:
            candidates = []

        if len(candidates) == 1:
            found = candidates[0]
            title = found.title
            db.delete(found)
            db.commit()
            from core.services.scheduler import wakeup_scheduler
            wakeup_scheduler()
            return f"Pronto, cancelei o compromisso {title} da sua agenda."

        if len(candidates) > 1:
            lista = []
            for e in candidates:
                local = e.start_time.astimezone(TZ)
                lista.append(f"'{e.title}' ({local.strftime('%d/%m %H:%M')})")
            if len(lista) <= 3:
                return f"Encontrei {len(candidates)} compromissos: {', '.join(lista[:-1])} e {lista[-1]}. Qual deles você deseja cancelar?"
            return f"Encontrei {len(candidates)} compromissos com esse nome. Por favor, seja mais específico."

        # Nenhum match: cancela o primeiro (mais próximo)
        found = events[0]
        title = found.title
        db.delete(found)
        db.commit()
        from core.services.scheduler import wakeup_scheduler
        wakeup_scheduler()
        return f"Pronto, cancelei o compromisso {title} da sua agenda."

    def _reschedule_event(self, db, room_id, text_lower) -> str:
        # Extrai o título: remove verbos de movimento
        search = text_lower
        for kw in ["mova", "mover", "move", "remarque", "reagende", "reagendar", "reagenda",
                    "adia", "adiar", "empurra", "empurrar", "adianta", "adiantar",
                    "o", "a", "os", "as", "compromisso", "evento", "da", "de", "do", "para"]:
            search = re.sub(r'\b' + re.escape(kw) + r'\b', '', search).strip()
        # Remove datas/horários/offsets residuais que não fazem parte do título
        search = re.sub(r'(?:às|as)\s+\d{1,2}(?:\s*[h:]\s*\d{1,2})?(?:\s*horas?|h)?', '', search)
        search = re.sub(r'(?:em\s+)?\d+\s*(?:min(?:uto)?s?|h(?:ora)?s?)', '', search)
        search = re.sub(r'\b(?:hoje|amanh[ãa]|depois|quint[ao]|ter[cç][ao]|segund[ao]|quart[ao]|sext[ao]|s[aá]bad[ao]|doming[ao]|semana|m[eê]s|dia\w*)\b', '', search)
        search = re.sub(r'\s+', ' ', search).strip()

        events = db.query(models.Event).filter(
            models.Event.room_id == room_id,
            models.Event.start_time >= datetime.now(timezone.utc)
        ).order_by(models.Event.start_time.asc()).all()

        if not events:
            return "Você não tem nenhum compromisso futuro para remarcar."

        candidates = self._find_events_by_title(events, search)

        if len(candidates) == 0:
            # Tenta com a search mais literal (fallback)
            for e in events:
                if search in e.title.lower():
                    candidates = [e]
                    break
        if len(candidates) == 0:
            return f"Não encontrei nenhum compromisso com '{search}' na sua agenda."

        if len(candidates) > 1:
            lista = [f"'{e.title}'" for e in candidates]
            return f"Encontrei {len(candidates)} compromissos: {', '.join(lista[:-1])} e {lista[-1]}. Qual deles você deseja remarcar?"

        found = candidates[0]
        old_local = found.start_time.astimezone(TZ)

        # Detecta offset relativo: "adia em 30 minutos", "adianta 1 hora"
        offset_match = re.search(r'(?:em\s+)?(\d+)\s*(?:min(?:uto)?s?|h(?:ora)?s?)', text_lower)
        # Detecta "pra mais tarde" / "pra frente" → +1h
        later_match = re.search(r'mais\s+tarde|pra\s+frente|depois', text_lower)
        # Detecta "pra mais cedo" / "pra trás" → -1h
        earlier_match = re.search(r'mais\s+cedo|pra\s+tr[sá]s|antes', text_lower)

        if offset_match and ('adia' in text_lower or 'empurra' in text_lower or 'adianta' in text_lower or 'adiar' in text_lower):
            num = int(offset_match.group(1))
            unit = offset_match.group(0)
            is_hours = 'h' in unit or 'hora' in unit
            delta = timedelta(hours=num) if is_hours else timedelta(minutes=num)
            if 'adianta' in text_lower or 'mais cedo' in text_lower:
                delta = -delta
            new_local = old_local + delta
        elif later_match:
            new_local = old_local + timedelta(hours=1)
        elif earlier_match:
            new_local = old_local - timedelta(hours=1)
        else:
            # Movimento absoluto: "move X para quinta", "remarque X para amanhã às 14h"
            # Extrai a parte depois de "para" ou "em"
            target_text = re.split(r'\b(?:para|em)\b', text_lower, maxsplit=1)
            target_text = target_text[-1] if len(target_text) > 1 else text_lower
            target_text = target_text.strip().lstrip("o a ").strip()

            # Tenta extrair horário do target
            time_match = re.search(r'(?:às|as)\s+(\d{1,2})(?:\s*[h:](\d{2}))?(?:\s*horas?|h)?', target_text)
            new_hour = int(time_match.group(1)) if time_match else old_local.hour
            new_min = int(time_match.group(2)) if (time_match and time_match.group(2)) else old_local.minute

            # Tenta extrair data do target
            resolved = self._resolve_date(target_text)
            if resolved:
                new_date, _ = resolved
            else:
                new_date = old_local.replace(hour=0, minute=0, second=0, microsecond=0)

            new_local = new_date.replace(hour=new_hour, minute=new_min, second=0, microsecond=0)
            if new_local <= old_local and new_date.date() == old_local.date():
                new_local += timedelta(days=1)

        new_utc = new_local.astimezone(timezone.utc)

        # Verifica conflito no novo horário
        conflicts = self._check_conflict(db, room_id, new_utc, exclude_title=found.title)
        if conflicts:
            return f"Já existe '{conflicts[0]['title']}' às {conflicts[0]['start_time']} neste novo horário. Deseja substituir ou escolher outro?"

        old_str = old_local.strftime("%A, %d/%m às %H:%M")
        new_str = new_local.strftime("%A, %d/%m às %H:%M")

        found.start_time = new_utc
        db.commit()

        from core.services.scheduler import wakeup_scheduler
        wakeup_scheduler()

        logger.info(f"Compromisso '{found.title}' remarcado de {old_str} para {new_str}")
        return f"Pronto, remarcado '{found.title}' de {old_str} para {new_str}."

    def execute_tool(self, kwargs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        db = context.get("db")
        room_id = context.get("room_id")
        action = kwargs.get("action")

        if not db or not room_id:
            return {"error": "Sem contexto de banco ou sala"}

        if action == "read":
            date_ref = kwargs.get("date", "hoje")

            resolved = self._resolve_date(date_ref)
            if resolved:
                target_date, day_str = resolved
            else:
                target_date = datetime.now(TZ)
                day_str = "hoje"

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
                hora_str = local_time.strftime("%H:%M").replace(":00", " horas")
                event_list.append({
                    "id": e.id,
                    "title": e.title,
                    "start_time": local_time.isoformat(),
                    "time": hora_str
                })

            if len(event_list) > 1:
                nomes = []
                for ev in event_list:
                    nomes.append(f"{ev['title']} às {ev['time']}")
                desc = ", ".join(nomes[:-1]) + " e " + nomes[-1]
            else:
                ev = event_list[0]
                desc = f"{ev['title']} às {ev['time']}"

            return {
                "events": event_list,
                "direct_response": f"Para {day_str} você tem: {desc}."
            }

        elif action == "add":
            title = kwargs.get("title", "").strip()
            start_iso = kwargs.get("start_time", "").strip()
            reminders_minutes = kwargs.get("reminders_minutes", [60])

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

            # Conflito de agenda
            conflicts = self._check_conflict(db, room_id, start_utc, exclude_title=title)
            if conflicts:
                evento_atual = {"title": title, "start_time": start_utc.astimezone(TZ).strftime("%H:%M")}
                todos_conflitos = [{"title": c["title"], "start_time": c["start_time"]} for c in conflicts]
                if len(conflicts) == 1:
                    msg = f"Você já tem '{conflicts[0]['title']}' às {conflicts[0]['start_time']} neste horário. Deseja substituir, manter ambos ou alterar o horário?"
                else:
                    conflitos_str = "; ".join([f"'{c['title']}' às {c['start_time']}" for c in conflicts])
                    msg = f"Você já tem compromissos neste horário: {conflitos_str}. Deseja substituir, manter todos ou alterar o horário?"
                return {
                    "status": "conflict",
                    "conflicting_events": todos_conflitos,
                    "proposed_event": evento_atual,
                    "direct_response": msg
                }

            valid_reminders = [str(max(1, int(r))) for r in reminders_minutes if isinstance(r, (int, float, str)) and str(r).strip().isdigit()]
            reminders_str = ",".join(sorted(set(valid_reminders), key=lambda x: int(x), reverse=True)) if valid_reminders else "60"

            new_event = models.Event(
                title=title,
                start_time=start_utc,
                room_id=room_id,
                reminders=reminders_str
            )
            db.add(new_event)
            db.commit()

            from core.services.scheduler import wakeup_scheduler
            wakeup_scheduler()

            local_time = start_utc.astimezone(TZ)
            reminders_desc = self._format_reminders_desc(reminders_str)
            return {
                "status": "success",
                "event": {"id": new_event.id, "title": title, "start_time": local_time.isoformat()},
                "direct_response": f"Adicionei o compromisso {title} na sua agenda.{reminders_desc}"
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
                candidates = self._find_events_by_title(events, title_search)
                if len(candidates) == 1:
                    found = candidates[0]
                elif len(candidates) > 1:
                    lista = [{"title": e.title, "start_time": e.start_time.astimezone(TZ).isoformat()} for e in candidates]
                    return {
                        "status": "multiple_found",
                        "candidates": lista,
                        "direct_response": f"Encontrei {len(candidates)} compromissos. Seja mais específico."
                    }

            if not found:
                return {"error": "Compromisso não encontrado.", "status": "fail"}

            title = found.title
            db.delete(found)
            db.commit()
            
            from core.services.scheduler import wakeup_scheduler
            wakeup_scheduler()
            
            return {"direct_response": f"Pronto, cancelei o compromisso {title}.", "status": "success"}

        elif action == "reschedule":
            title_search = kwargs.get("title", "").strip().lower()
            event_id = kwargs.get("event_id")
            new_start_iso = kwargs.get("new_start_time", "").strip()
            offset_minutes = kwargs.get("offset_minutes")

            if not title_search and event_id is None:
                return {"error": "Informe o título ou ID do evento.", "status": "fail"}

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
                candidates = self._find_events_by_title(events, title_search)
                if len(candidates) == 1:
                    found = candidates[0]
                elif len(candidates) > 1:
                    lista = [{"title": e.title, "start_time": e.start_time.astimezone(TZ).isoformat()} for e in candidates]
                    return {
                        "status": "multiple_found",
                        "candidates": lista,
                        "direct_response": f"Encontrei {len(candidates)} compromissos. Seja mais específico."
                    }

            if not found:
                return {"error": "Compromisso não encontrado.", "status": "fail"}

            old_local = found.start_time.astimezone(TZ)

            if offset_minutes is not None:
                try:
                    delta = timedelta(minutes=int(offset_minutes))
                except (ValueError, TypeError):
                    return {"error": "Offset inválido.", "status": "fail"}
                new_local = old_local + delta
            elif new_start_iso:
                try:
                    new_dt = datetime.fromisoformat(new_start_iso)
                    if new_dt.tzinfo is None:
                        new_dt = new_dt.replace(tzinfo=TZ)
                    new_local = new_dt.astimezone(TZ)
                except ValueError:
                    return {"error": f"Formato de data inválido: {new_start_iso}", "status": "fail"}
            else:
                return {"error": "Informe new_start_time ou offset_minutes.", "status": "fail"}

            new_utc = new_local.astimezone(timezone.utc)

            conflicts = self._check_conflict(db, room_id, new_utc, exclude_title=found.title)
            if conflicts:
                return {
                    "status": "conflict",
                    "conflicting_events": [{"title": c["title"], "start_time": c["start_time"]} for c in conflicts],
                    "direct_response": f"Já existe '{conflicts[0]['title']}' neste novo horário."
                }

            old_str = old_local.strftime("%A, %d/%m às %H:%M")
            new_str = new_local.strftime("%A, %d/%m às %H:%M")

            found.start_time = new_utc
            db.commit()

            from core.services.scheduler import wakeup_scheduler
            wakeup_scheduler()

            logger.info(f"Compromisso '{found.title}' remarcado de {old_str} para {new_str}")
            return {
                "status": "success",
                "event": {"id": found.id, "title": found.title, "start_time": new_local.isoformat()},
                "direct_response": f"Pronto, remarcado '{found.title}' de {old_str} para {new_str}."
            }

        return {"error": "Ação desconhecida. Use add, read, remove ou reschedule."}
