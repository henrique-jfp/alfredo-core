import os
import requests
import logging
from typing import Dict, Any
from core.brain.skills.base import Skill
from core.brain.memory import models

logger = logging.getLogger("alfredo.skills")

class FallbackSkill(Skill):
    """
    Skill acionada quando o IntentRouter não consegue identificar uma intenção local.
    Delega a resposta para o LLM na nuvem (Groq - Llama-3).
    """
    
    @property
    def name(self) -> str:
        return "FallbackSkill (Groq/Gemini LLM)"

    def can_handle(self, intent: str, text: str) -> bool:
        return intent == "UNKNOWN"

    def execute(self, text: str, context: Dict[str, Any]) -> str:
        db = context.get("db")
        room_id = context.get("room_id")
        
        system_prompt = (
            "Você é a Alexa, assistente inteligente criada para uma casa inteligente. "
            "Responda a essa pergunta com uma resposta muito curta e direta, não mais que 1 ou 2 frases. NUNCA use emojis."
        )
        
        # 1. Recuperar histórico
        history_messages = []
        if db and room_id:
            from datetime import datetime, timedelta, timezone
            ten_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=10)
            
            # Buscar últimas 3 interações dos últimos 10 minutos
            last_interactions = db.query(models.Interaction).filter(
                models.Interaction.room_id == room_id,
                models.Interaction.input_text.isnot(None),
                models.Interaction.output_text.isnot(None),
                models.Interaction.input_text != "",
                models.Interaction.timestamp >= ten_minutes_ago
            ).order_by(models.Interaction.id.desc()).limit(3).all()
            
            # Inverter para ficar na ordem cronológica (mais antiga primeiro)
            for interaction in reversed(last_interactions):
                history_messages.append({"role": "user", "content": interaction.input_text})
                history_messages.append({"role": "assistant", "content": interaction.output_text})
        
        # Tenta Groq primeiro
        try:
            return self._call_groq(text, history_messages, system_prompt, db, room_id)
        except Exception as e:
            logger.warning(f"Groq falhou ({e}). Tentando fallback para Gemini...")
            try:
                return self._call_gemini(text, history_messages, system_prompt, db, room_id)
            except Exception as e2:
                logger.error(f"Gemini também falhou: {e2}")
                return "Desculpe, minhas conexões de inteligência na nuvem estão fora do ar."

    def _call_groq(self, text: str, history: list, system_prompt: str, db: Any, room_id: str) -> str:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key or api_key == "gsk_sua_chave_aqui":
            raise ValueError("Chave da Groq API não configurada.")
            
        model = "llama-3.1-8b-instant" 
        
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": text})
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 150
        }
        
        logger.info("Enviando texto para a Groq (LLM Fallback)...")
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=5
        )
        response.raise_for_status()
        
        data = response.json()
        reply = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)
        
        reply = reply.replace("*", "").replace("😊", "").replace("🤖", "").strip()
        logger.info(f"Resposta do Groq: {reply} (Tokens: {tokens})")
        
        # Gravar uso
        if db and room_id:
            usage = models.AIUsage(provider="Groq", tokens_used=tokens, room_id=room_id)
            db.add(usage)
            db.commit()
            
        return reply

    def _call_gemini(self, text: str, history: list, system_prompt: str, db: Any, room_id: str) -> str:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or api_key == "sua_chave_aqui":
            raise ValueError("Chave da Gemini API não configurada.")
            
        # Adaptar history para o formato Gemini
        gemini_history = []
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            gemini_history.append({"role": role, "parts": [{"text": msg["content"]}]})
            
        gemini_history.append({"role": "user", "parts": [{"text": text}]})
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        payload = {
            "system_instruction": {
                "parts": {"text": system_prompt}
            },
            "contents": gemini_history,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 150
            }
        }
        
        logger.info("Enviando texto para o Gemini (Fallback do Fallback)...")
        response = requests.post(url, json=payload, timeout=8)
        response.raise_for_status()
        
        data = response.json()
        reply = data["candidates"][0]["content"]["parts"][0]["text"]
        tokens = data.get("usageMetadata", {}).get("totalTokenCount", 0)
        
        reply = reply.replace("*", "").replace("😊", "").replace("🤖", "").strip()
        logger.info(f"Resposta do Gemini: {reply} (Tokens: {tokens})")
        
        # Gravar uso
        if db and room_id:
            usage = models.AIUsage(provider="Gemini", tokens_used=tokens, room_id=room_id)
            db.add(usage)
            db.commit()
            
        return reply
