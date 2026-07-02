import os
import json
import logging
import google.generativeai as genai
from typing import Dict, Any
from core.brain.skills.weather_skill import WeatherSkill
from core.brain.skills.traffic_skill import TrafficSkill
from core.brain.skills.list_skill import ListSkill
from core.brain.skills.timer_skill import TimerSkill
from core.brain.skills.time_skill import TimeSkill

logger = logging.getLogger("alfredo.agent")

class AgentRouter:
    def __init__(self):
        self.skills = {
            "get_weather": WeatherSkill(),
            "get_traffic": TrafficSkill(),
            "manage_list": ListSkill(),
            "manage_timer": TimerSkill(),
            "get_time": TimeSkill()
        }

    def _get_tools_schema(self):
        return [
            {
                "function_declarations": [
                    {
                        "name": "get_weather",
                        "description": "Obtém a previsão do tempo para um local e data",
                        "parameters": {
                            "type": "OBJECT",
                            "properties": {
                                "location": {"type": "STRING", "description": "Cidade ou local alvo. Opcional."},
                                "date": {"type": "STRING", "description": "Data alvo, ex: 'hoje', 'amanhã', 'depois de amanhã'"}
                            }
                        }
                    },
                    {
                        "name": "get_traffic",
                        "description": "Obtém a estimativa de trânsito e rota entre dois lugares",
                        "parameters": {
                            "type": "OBJECT",
                            "properties": {
                                "origin": {"type": "STRING", "description": "Local de origem (ex: casa). Se omitido, assume casa do usuário."},
                                "destination": {"type": "STRING", "description": "Local de destino (ex: trabalho, supermercado, farmácia)"}
                            },
                            "required": ["destination"]
                        }
                    },
                    {
                        "name": "manage_list",
                        "description": "Adiciona, lê, deleta ou envia por e-mail itens de listas (tarefas ou compras)",
                        "parameters": {
                            "type": "OBJECT",
                            "properties": {
                                "action": {"type": "STRING", "description": "Ação a realizar: 'add', 'read', 'clear' ou 'email'"},
                                "list_type": {"type": "STRING", "description": "Tipo de lista: 'compras' ou 'tarefas'"},
                                "items": {
                                    "type": "ARRAY", 
                                    "items": {"type": "STRING"},
                                    "description": "Itens a adicionar (apenas para a ação 'add')"
                                }
                            },
                            "required": ["action", "list_type"]
                        }
                    },
                    {
                        "name": "manage_timer",
                        "description": "Cria alarmes (horas absolutas) ou cronômetros (tempo relativo), ou lista os existentes",
                        "parameters": {
                            "type": "OBJECT",
                            "properties": {
                                "action": {"type": "STRING", "description": "Ação a realizar: 'create', 'list' ou 'delete'"},
                                "duration_seconds": {"type": "INTEGER", "description": "Duração em segundos para timers relativos (ex: daqui a 5 min = 300)"},
                                "target_hour": {"type": "INTEGER", "description": "Hora absoluta (0-23) para alarmes ou despertadores (ex: às 7 da manhã = 7)"},
                                "message": {"type": "STRING", "description": "Mensagem ou motivo do alarme/lembrete"}
                            },
                            "required": ["action"]
                        }
                    },
                    {
                        "name": "get_time",
                        "description": "Retorna a data atual ou o horário atual do sistema",
                        "parameters": {
                            "type": "OBJECT",
                            "properties": {
                                "request_type": {"type": "STRING", "description": "O que o usuário quer saber: 'time' ou 'date'"}
                            },
                            "required": ["request_type"]
                        }
                    }
                ]
            }
        ]

    def process(self, text: str, context: Dict[str, Any]) -> str:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return "Erro: Chave do Gemini não configurada no .env"
            
        genai.configure(api_key=api_key)
            
        db = context.get("db")
        room_id = context.get("room_id")
        
        history_str = ""
        if db and room_id:
            from core.brain.memory import models
            from datetime import datetime, timedelta, timezone
            ten_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=10)
            last_interactions = db.query(models.Interaction).filter(
                models.Interaction.room_id == room_id,
                models.Interaction.input_text.isnot(None),
                models.Interaction.output_text.isnot(None),
                models.Interaction.input_text != "",
                models.Interaction.timestamp >= ten_minutes_ago
            ).order_by(models.Interaction.id.desc()).limit(3).all()
            for interaction in reversed(last_interactions):
                history_str += f"Usuário: {interaction.input_text}\nAlfredo: {interaction.output_text}\n"

        system_prompt = "Você é o Alfredo, um assistente virtual ultra avançado para automação residencial. Responda sempre de forma natural, amigável e conversacional. Evite respostas engessadas ou mecânicas. Fale como um humano. Seja breve, evite parágrafos longos, use no máximo 2 frases sempre que possível."
        if history_str:
            system_prompt += f"\n\nHistórico recente:\n{history_str}"
            
        tools = self._get_tools_schema()
        model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            tools=tools,
            system_instruction=system_prompt
        )

        try:
            logger.info("Enviando requisição ao Gemini 2.5 Flash para Tool Calling...")
            chat = model.start_chat()
            response = chat.send_message(text)
            
            if response.parts:
                part = response.parts[0]
                if part.function_call:
                    function_name = part.function_call.name
                    # Extrai os argumentos como um dicionario python
                    arguments = type(part.function_call).to_dict(part.function_call).get("args", {})
                    logger.info(f"Tool Calling: {function_name} com args {arguments}")
                    
                    skill = self.skills.get(function_name)
                    if not skill:
                        return "Desculpe, a ferramenta solicitada não existe."
                        
                    if hasattr(skill, "execute_tool"):
                        tool_result_obj = skill.execute_tool(arguments, context)
                    else:
                        tool_result_obj = skill.execute(text, context)
                        
                    logger.info(f"Resultado da Tool: {tool_result_obj}")
                    
                    logger.info("Enviando resultado da ferramenta de volta para o Gemini...")
                    tool_response = chat.send_message(
                        genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name=function_name,
                                response={"result": tool_result_obj}
                            )
                        )
                    )
                    
                    final_text = tool_response.text.strip()
                    logger.info(f"Resposta final gerada: {final_text}")
                    return final_text
                else:
                    logger.info("Nenhuma ferramenta acionada. Resposta direta do Gemini.")
                    return response.text.strip()
            
            return "Desculpe, não entendi a resposta do meu novo cérebro."
            
        except Exception as e:
            logger.error(f"Erro na API do Gemini: {e}")
            return "Tive um problema de comunicação com o meu núcleo neural."

def get_router():
    return AgentRouter()
