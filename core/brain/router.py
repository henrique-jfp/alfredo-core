import os
import json
import logging
import google.generativeai as genai
from typing import Dict, Any
from core.brain.skills.weather_skill import WeatherSkill
from core.brain.skills.traffic_skill import TrafficSkill
from core.brain.skills.list_skill import ListSkill
from core.brain.skills.time_skill import TimeSkill
from core.brain.skills.media_skill import MediaSkill
from core.brain.skills.quiz_skill import QuizSkill
from core.brain.skills.timer_skill import TimerSkill
from core.brain.skills.recipe_skill import RecipeSkill
from core.brain.skills.dream_skill import DreamSkill
from core.brain.skills.memory_skill import MemorySkill

logger = logging.getLogger("alfredo.agent")

_global_key_idx = 0

class AgentRouter:
    def __init__(self):
        self.skills = {
            "get_weather": WeatherSkill(),
            "get_traffic": TrafficSkill(),
            "manage_list": ListSkill(),
            "manage_timer": TimerSkill(),
            "get_time": TimeSkill(),
            "search_media": MediaSkill(),
            "manage_quiz": QuizSkill(),
            "manage_recipe": RecipeSkill(),
            "log_dream": DreamSkill(),
            "manage_memory": MemorySkill()
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
                    },
                    {
                        "name": "search_media",
                        "description": "Busca sugestões de filmes e séries baseadas em gênero, ano ou década usando a API do TMDB",
                        "parameters": {
                            "type": "OBJECT",
                            "properties": {
                                "media_type": {"type": "STRING", "description": "O tipo de mídia procurado: 'movie' para filmes, 'tv' para séries. O padrão é 'movie' se não for especificado."},
                                "genre": {"type": "STRING", "description": "O gênero desejado. Ex: 'Ficção científica', 'Ação', 'Comédia'"},
                                "decade_or_year": {"type": "STRING", "description": "Ano específico (ex: '1999') ou início de década (ex: '1990' para anos 90, '2000' para anos 2000)"}
                            }
                        }
                    },
                    {
                        "name": "manage_quiz",
                        "description": "Inicia ou encerra um jogo interativo de perguntas e respostas (Quiz / Tarefa Escolar) com o usuário.",
                        "parameters": {
                            "type": "OBJECT",
                            "properties": {
                                "action": {"type": "STRING", "description": "Ação a realizar: 'start' para iniciar o quiz, 'stop' para encerrar"},
                                "subject": {"type": "STRING", "description": "O assunto do quiz. Ex: 'matemática', 'geografia', 'conhecimentos gerais'"},
                                "difficulty": {"type": "STRING", "description": "O nível de dificuldade do quiz. Ex: 'criança de 9 anos', 'difícil', 'adulto'"}
                            },
                            "required": ["action"]
                        }
                    },
                    {
                        "name": "manage_recipe",
                        "description": "Ensina receitas passo a passo ou sugere harmonização de vinhos e comidas.",
                        "parameters": {
                            "type": "OBJECT",
                            "properties": {
                                "action": {"type": "STRING", "description": "Ação a realizar: 'recipe' para ditar uma receita, 'pairing' para harmonização"},
                                "query": {"type": "STRING", "description": "O nome do prato ou do vinho. Ex: 'risoto de funghi' ou 'vinho tinto'"}
                            },
                            "required": ["action", "query"]
                        }
                    },
                    {
                        "name": "log_dream",
                        "description": "Acionado quando o usuário relata um sonho. Extrai os temas centrais e gera uma interpretação profunda.",
                        "parameters": {
                            "type": "OBJECT",
                            "properties": {
                                "themes": {
                                    "type": "ARRAY", 
                                    "items": {"type": "STRING"}, 
                                    "description": "3 a 5 palavras-chave curtas ou temas principais do sonho relatado."
                                },
                                "interpretation": {
                                    "type": "STRING", 
                                    "description": "Uma interpretação poética e psicológica do sonho em 2 frases."
                                }
                            },
                            "required": ["themes", "interpretation"]
                        }
                    },
                    {
                        "name": "manage_memory",
                        "description": "Salva um fato ou preferência permanente sobre o usuário (ex: alergias, horários, gostos) na memória de longo prazo.",
                        "parameters": {
                            "type": "OBJECT",
                            "properties": {
                                "fact": {
                                    "type": "STRING", 
                                    "description": "A frase resumida sobre o fato a ser salvo. Ex: 'O usuário é alérgico a amendoim'."
                                }
                            },
                            "required": ["fact"]
                        }
                    }
                ]
            }
        ]

    def process(self, text: str, context: Dict[str, Any]) -> str:
        global _global_key_idx
        
        keys_env = os.getenv("GEMINI_API_KEYS")
        if keys_env:
            keys = [k.strip() for k in keys_env.split(",") if k.strip()]
        else:
            single = os.getenv("GEMINI_API_KEY")
            keys = [single.strip()] if single else []

        if not keys:
            return "Erro: Nenhuma chave do Gemini configurada no .env (utilize GEMINI_API_KEYS)."
            
        current_key = keys[_global_key_idx % len(keys)]
        logger.info(f"Revezamento: Usando chave do Gemini [{(_global_key_idx % len(keys)) + 1} de {len(keys)}] para esta requisição.")
        _global_key_idx += 1
            
        genai.configure(api_key=current_key)
            
        db = context.get("db")
        room_id = context.get("room_id")
        
        history_str = ""
        if db and room_id:
            from core.brain.memory import models
            from datetime import datetime, timedelta, timezone
            
            # 1. Fetch short-term history
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
                    
            # 2. Fetch long-term memories
            memory_facts = db.query(models.MemoryFact).filter(models.MemoryFact.room_id == room_id).all()
            if memory_facts:
                memories = [f"- {m.fact}" for m in memory_facts]
                long_term_memory = "\nFatos permanentes conhecidos sobre o usuário:\n" + "\n".join(memories)
            else:
                long_term_memory = ""
        else:
            long_term_memory = ""

        system_prompt = (
            "Você é o Alfredo, um assistente virtual ultra avançado para automação residencial. "
            "Responda sempre de forma natural, amigável e conversacional. Seja breve, no máximo 2 frases. "
            "NUNCA utilize emojis ou símbolos complexos nas suas respostas. "
            "Se o usuário pedir para traduzir algo ou aprender um idioma, traduza e SEMPRE adicione a forma "
            "de se pronunciar lendo em português, para que o sintetizador de voz fale corretamente. "
            "REGRA DO QUIZ: Se pelo histórico você perceber que está no meio de um jogo de perguntas (Quiz), "
            "valide se o usuário acertou a última pergunta, elogie-o ou corrija-o gentilmente, "
            "e SEMPRE termine sua fala com uma NOVA PERGUNTA, a menos que ele peça para parar. "
            "REGRA DA RECEITA: Ao ensinar uma receita passo a passo, NUNCA gere todos os passos. Ensine UM PASSO por vez e diga ao usuário para avisar quando terminar. "
            "Para não perder o contexto da receita nos passos seguintes, SEMPRE inclua o nome do prato na sua resposta (ex: 'Passo 3 do Risoto de Funghi: ...')."
        )
        
        if long_term_memory:
            system_prompt += f"\n{long_term_memory}"
            
        if history_str:
            system_prompt += f"\n\nHistórico recente:\n{history_str}"
            
        tools = self._get_tools_schema()
        model = genai.GenerativeModel(
            model_name='gemini-3.1-flash-lite',
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
