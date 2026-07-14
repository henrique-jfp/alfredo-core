import os
import json
import logging
import re
import threading
import google.generativeai as genai
from groq import Groq as GroqClient
from typing import Dict, Any
from core.brain.skills.weather_skill import WeatherSkill
from core.brain.skills.traffic_skill import TrafficSkill
from core.brain.skills.list_skill import ListSkill
from core.brain.skills.time_skill import TimeSkill
from core.brain.skills.media_skill import MediaSkill
from core.brain.skills.quiz_skill import QuizSkill
from core.brain.skills.calendar_skill import CalendarSkill
from core.brain.skills.timer_skill import TimerSkill
from core.brain.skills.recipe_skill import RecipeSkill
from core.brain.skills.dream_skill import DreamSkill
from core.brain.skills.memory_skill import MemorySkill
from core.brain.skills.translate_skill import TranslateSkill
from core.brain.skills.news_skill import NewsSkill
from core.brain.skills.music_skill import MusicSkill
from core.brain.skills.tv_skill import TVSkill
from core.brain.skills.youtube_skill import YouTubeSkill

logger = logging.getLogger("alfredo.agent")

_global_key_idx = 0
_global_key_lock = threading.Lock()


def _load_gemini_keys() -> list[str]:
    keys_env = os.getenv("GEMINI_API_KEYS", "")
    if keys_env:
        raw_keys = re.split(r"[\n,;]+", keys_env)
        keys = [key.strip().strip('"').strip("'") for key in raw_keys if key.strip()]
    else:
        single = os.getenv("GEMINI_API_KEY", "").strip()
        keys = [single.strip('"').strip("'")] if single else []

    deduped_keys = []
    seen = set()
    for key in keys:
        if key and key not in seen:
            deduped_keys.append(key)
            seen.add(key)
    return deduped_keys


def _select_next_gemini_key(keys: list[str]) -> tuple[str | None, int]:
    if not keys:
        return None, 0

    global _global_key_idx
    with _global_key_lock:
        key_index = _global_key_idx % len(keys)
        current_key = keys[key_index]
        current_number = key_index + 1
        _global_key_idx += 1
    return current_key, current_number


def get_gemini_key_status() -> tuple[int, int, int]:
    keys = _load_gemini_keys()
    total_keys = len(keys)
    with _global_key_lock:
        current_idx = (_global_key_idx % total_keys) + 1 if total_keys > 0 else 0
        global_requests = _global_key_idx
    return total_keys, current_idx, global_requests

class AgentRouter:
    def __init__(self):
        self.skills = {
            "get_weather": WeatherSkill(),
            "get_traffic": TrafficSkill(),
            "manage_list": ListSkill(),
            "manage_timer": TimerSkill(),
            "get_time": TimeSkill(),
            "search_media": MediaSkill(),
            "manage_music": MusicSkill(),
            "manage_quiz": QuizSkill(),
            "manage_recipe": RecipeSkill(),
            "manage_calendar": CalendarSkill(),
            "log_dream": DreamSkill(),
            "manage_memory": MemorySkill(),
            "translate": TranslateSkill(),
            "get_news": NewsSkill(),
            "manage_tv": TVSkill(),
            "play_youtube": YouTubeSkill()
        }
        self.groq_client = None
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=groq_key)
            except Exception as e:
                logger.warning(f"Não foi possível inicializar o cliente Groq: {e}")
                
        # Semantic Router Local (Fast Interceptor)
        from core.brain.semantic_router import FastSemanticRouter
        self.semantic_router = FastSemanticRouter()

    def _get_tools_schema(self):
        return [
            {
                "function_declarations": [
                    {
                        "name": "get_weather",
                        "description": "Obtém a previsão do tempo para um local e data",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "location": {"type": "string", "description": "Cidade ou local alvo. Opcional."},
                                "date": {"type": "string", "description": "Data alvo em linguagem natural. Ex: 'hoje', 'amanhã', 'depois de amanhã', 'próxima terça', 'sexta', 'semana que vem', 'mês que vem', 'daqui a 3 dias'"}
                            }
                        }
                    },
                    {
                        "name": "get_traffic",
                        "description": "Acione SEMPRE que o usuário perguntar sobre trânsito, tempo de viagem ou rota. NUNCA pergunte sobre meio de transporte.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "origin": {"type": "string", "description": "Origem. Se omitido, use 'casa'."},
                                "destination": {"type": "string", "description": "Destino. Se omitido, use 'trabalho'."}
                            }
                        }
                    },
                    {
                        "name": "manage_list",
                        "description": "GERENCIAR LISTAS: use esta ferramenta OBRIGATORIAMENTE para adicionar, ler, remover, limpar ou enviar via Telegram itens em listas de 'compras' ou 'tarefas'. NÃO responda como texto — execute a ferramenta.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string", "description": "Ação a realizar: 'add', 'read', 'remove', 'clear' ou 'email'"},
                                "list_type": {
                                    "type": "string",
                                    "description": "Tipo de lista suportado pelo Dashboard.",
                                    "enum": ["compras", "tarefas"]
                                },
                                "items": {
                                    "type": "array", 
                                    "items": {"type": "string"},
                                    "description": "Itens a adicionar (apenas para a ação 'add')"
                                },
                                "item": {
                                    "type": "string",
                                    "description": "Item a remover (apenas para a ação 'remove')"
                                }
                            },
                            "required": ["action", "list_type"]
                        }
                    },
                    {
                        "name": "manage_timer",
                        "description": "GERENCIAR ALARMES E TIMERS: use esta ferramenta OBRIGATORIAMENTE para criar, listar ou deletar alarmes, despertadores ou cronômetros. Se o usuário pedir múltiplos timers na mesma frase, CHAME ESTA FERRAMENTA MÚLTIPLAS VEZES (uma para cada timer). NUNCA responda que o alarme foi criado sem acionar esta ferramenta.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string", "description": "Ação a realizar: 'create', 'list' ou 'delete'"},
                                "duration_seconds": {"type": "integer", "description": "Duração em segundos para timers relativos (ex: daqui a 5 min = 300)"},
                                "target_hour": {"type": "integer", "description": "Hora absoluta (0-23) para alarmes ou despertadores (ex: às 7 da manhã = 7, às 3 da tarde = 15)"},
                                "target_minute": {"type": "integer", "description": "Minuto absoluto (0-59) para alarmes (ex: 7h43 = 43). Padrão é 0."},
                                "message": {"type": "string", "description": "Mensagem ou motivo do alarme/lembrete"}
                            },
                            "required": ["action"]
                        }
                    },
                    {
                        "name": "get_time",
                        "description": "Retorna a data atual ou o horário atual do sistema",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "request_type": {"type": "string", "description": "O que o usuário quer saber: 'time' ou 'date'"}
                            },
                            "required": ["request_type"]
                        }
                    },
                    {
                        "name": "search_media",
                        "description": "Busca sugestões de filmes e séries baseadas em gênero, ano ou década usando a API do TMDB",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "media_type": {"type": "string", "description": "O tipo de mídia procurado: 'movie' para filmes, 'tv' para séries. O padrão é 'movie' se não for especificado."},
                                "genre": {"type": "string", "description": "O gênero desejado. Ex: 'Ficção científica', 'Ação', 'Comédia'"},
                                "decade_or_year": {"type": "string", "description": "Ano específico (ex: '1999') ou início de década (ex: '1990' para anos 90, '2000' para anos 2000)"}
                            }
                        }
                    },
                    {
                        "name": "manage_music",
                        "description": "Controla a reprodução no Spotify: tocar música/artista/playlist, pausar, pular faixa, voltar, retomar e ajustar volume. Use APENAS para MÚSICAS no Spotify. Para lives, podcasts ou conteúdo que só existe no YouTube, use 'play_youtube'.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string", "description": "Ação: 'search' para buscar e tocar, 'pause', 'resume', 'next', 'previous' ou 'volume'"},
                                "query": {"type": "string", "description": "Nome da música ou artista (apenas para action='search')"},
                                "volume": {"type": "integer", "description": "Volume de 0 a 100 (apenas para action='volume')"}
                            },
                            "required": ["action"]
                        }
                    },
                    {
                        "name": "manage_quiz",
                        "description": "Inicia, atualiza placar ou encerra um jogo interativo de perguntas e respostas (Quiz / Tarefa Escolar) com o usuário.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string", "description": "'start' para iniciar, 'update' para salvar placar, 'stop' para encerrar"},
                                "subject": {"type": "string", "description": "O assunto do quiz. Ex: 'matemática', 'geografia', 'conhecimentos gerais'"},
                                "difficulty": {"type": "string", "description": "O nível de dificuldade do quiz. Ex: 'criança de 9 anos', 'difícil', 'adulto'"},
                                "score": {"type": "number", "description": "Número de acertos (usar com action='update')"},
                                "questions_count": {"type": "number", "description": "Total de perguntas feitas (usar com action='update')"},
                                "max_questions": {"type": "number", "description": "Limite máximo de perguntas (padrão: 10)"}
                            },
                            "required": ["action"]
                        }
                    },
                    {
                        "name": "manage_recipe",
                        "description": "Ensina receitas passo a passo ou sugere harmonização de vinhos e comidas.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string", "description": "'recipe' para iniciar, 'next_step' após cada passo, 'pairing' para harmonização, 'finish' para encerrar"},
                                "query": {"type": "string", "description": "O nome do prato ou do vinho. Ex: 'risoto de funghi' ou 'vinho tinto'"},
                                "step": {"type": "number", "description": "Número do próximo passo (usar com action='next_step')"}
                            },
                            "required": ["action", "query"]
                        }
                    },
                    {
                        "name": "manage_calendar",
                        "description": "Gerencia compromissos na agenda: adiciona, lê, remove ou remarca eventos futuros.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string", "description": "Ação: 'add', 'read', 'remove' ou 'reschedule'"},
                                "title": {"type": "string", "description": "Título do compromisso (para add/remove/reschedule)"},
                                "start_time": {"type": "string", "description": "Data e hora ISO 8601. Ex: '2026-07-05T14:30:00' (para add)"},
                                "date": {"type": "string", "description": "Data para leitura em linguagem natural: 'hoje', 'amanhã', 'depois de amanhã', 'próxima terça', 'sexta', 'semana que vem', 'mês que vem', 'daqui a 3 dias' (apenas para read)"},
                                "reminders_minutes": {
                                    "type": "array",
                                    "items": {"type": "number"},
                                    "description": "Minutos antes do evento para lembrar. Padrão: [60]. Ex: [60,15,5] lembra 1h, 15min e 5min antes. Use [1440] para 1 dia antes."
                                },
                                "new_start_time": {"type": "string", "description": "Nova data/hora ISO 8601 (para reschedule). Ex: '2026-07-11T14:00:00'"},
                                "offset_minutes": {"type": "number", "description": "Deslocamento em minutos (para reschedule). Positivo = adiar, negativo = adiantar. Ex: 30 adia 30 min"}
                            },
                            "required": ["action"]
                        }
                    },
                    {
                        "name": "log_dream",
                        "description": "Acionado quando o usuário relata um sonho. Extrai os temas centrais e gera uma interpretação profunda.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "themes": {
                                    "type": "array", 
                                    "items": {"type": "string"}, 
                                    "description": "3 a 5 palavras-chave curtas ou temas principais do sonho relatado."
                                },
                                "interpretation": {
                                    "type": "string", 
                                    "description": "Uma interpretação poética e psicológica do sonho em 2 frases."
                                },
                                "raw_text": {
                                    "type": "string",
                                    "description": "O relato completo do sonho como o usuário contou, preservado para registro."
                                }
                            },
                            "required": ["themes", "interpretation", "raw_text"]
                        }
                    },
                    {
                        "name": "manage_memory",
                        "description": "Salva um fato ou preferência permanente sobre o usuário (ex: alergias, horários, gostos) na memória de longo prazo.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "fact": {
                                    "type": "string", 
                                    "description": "A frase resumida sobre o fato a ser salvo. Ex: 'O usuário é alérgico a amendoim'."
                                }
                            },
                            "required": ["fact"]
                        }
                    },
                    {
                        "name": "translate",
                        "description": "Traduz frases ou palavras entre idiomas, ou dá mini-aulas de idiomas. Ex: 'traduza hello para português', 'como se fala obrigado em inglês', 'me dá uma aula de francês'",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string", "description": "Ação a realizar: 'translate' para tradução normal, 'lesson' para mini-aula"},
                                "text": {"type": "string", "description": "A frase ou palavra a ser traduzida ou o tópico da aula"},
                                "target_language": {"type": "string", "description": "Idioma alvo da tradução ou aula. Ex: 'inglês', 'espanhol', 'francês', 'italiano'"}
                            },
                            "required": ["action"]
                        }
                    },
                    {
                        "name": "get_news",
                        "description": "Obtém as principais manchetes de notícias do Brasil e do mundo. Permite filtrar por categoria: política, esportes, economia, mundo, tecnologia, saúde, cultura ou ciência.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "category": {"type": "string", "description": "Categoria opcional: politica, esportes, economia, mundo, tecnologia, saude, cultura, ciencia"}
                            }
                        }
                    },
                    {
                        "name": "manage_tv",
                        "description": "OBRIGATÓRIO: Acione esta ferramenta SEMPRE que o usuário pedir para ligar, desligar, alterar volume, mutar ou abrir aplicativos na televisão/TV. Permite executar MÚLTIPLAS ações em sequência (ex: ligar a tv e depois abrir netflix).",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "actions": {
                                    "type": "array",
                                    "description": "Lista de ações sequenciais a executar na TV.",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "action": {
                                                "type": "string",
                                                "description": "Ação a realizar",
                                                "enum": ["power_on", "power_off", "mute", "unmute", "volume_up", "volume_down", "set_volume", "open_app"]
                                            },
                                            "app_name": {"type": "string", "description": "Nome do app (ex: netflix, youtube)"},
                                            "volume": {"type": "integer", "description": "Volume (apenas set_volume)"}
                                        },
                                        "required": ["action"]
                                    }
                                }
                            },
                            "required": ["actions"]
                        }
                    },
                    {
                        "name": "play_youtube",
                        "description": "Toca ou para áudio do YouTube: transmissões ao vivo (ex: CazéTV, GloboNews), podcasts, vídeos. Use para LIVES, PODCASTS, CANAIS ou quando o usuário disser 'no YouTube'. Para músicas no Spotify, use 'manage_music'. Use action='stop' quando o usuário pedir para parar o YouTube.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string", "description": "Ação: 'play' (padrão) para tocar, 'stop' para parar a reprodução"},
                                "query": {"type": "string", "description": "Nome do canal, live, podcast ou vídeo (apenas para action='play')"},
                                "is_live": {"type": "boolean", "description": "Se é uma transmissão ao vivo (apenas para action='play')"}
                            },
                            "required": ["action"]
                        }
                    }
                ]
            }
        ]

    def _is_simple_query(self, text: str, context: Dict[str, Any] = None) -> bool:
        """Determina heurísticamente se a requisição pode ser respondida pelo Groq Fast Path."""
        
        # Se houver uma sessão ativa, não é simple query (precisamos do Gemini para continuar a ferramenta)
        if context:
            db = context.get("db")
            room_id = context.get("room_id")
            if db and room_id:
                from core.brain.memory import models
                session = db.query(models.SessionState).filter(models.SessionState.room_id == room_id).first()
                if session:
                    return False
        
        """Detecta queries que NÃO precisam de ferramentas (tools) e podem ir
        direto para o Groq fast path (~300ms vs ~2-3s do Gemini).
        
        Abrange: saudações, despedidas, agradecimentos, piadas, perguntas de
        conhecimento geral, confirmações e queries curtas conversacionais.
        """
        simple_keywords = [
            # Saudações e despedidas
            "oi", "olá", "ola", "bom dia", "boa tarde", "boa noite",
            "e aí", "e ai", "opa", "tchau", "até logo", "ate logo",
            "até mais", "ate mais", "boa noite",
            # Agradecimentos e confirmações
            "obrigado", "brigado", "valeu", "sim", "não", "nao",
            "talvez", "ok", "tá bom", "ta bom", "beleza", "certo",
            "entendi", "legal", "show", "massa",
            # Piadas e entretenimento
            "piada", "conte", "conta", "história", "historia", "estória",
            "curiosidade", "fato curioso", "fato interessante",
            # Pedidos de informação geral (sem tools)
            "fale", "diga", "explique", "explica", "me fala", "me diga",
            "me conta", "me explica", "o que é", "o que são",
            "quem é", "quem foi", "quem era", "quem são",
            "como funciona", "por que", "porque", "por quê",
            # Auto-referência
            "como você", "quem é você", "o que você",
            "qual sua", "qual é sua", "qual o seu",
            # (removido: tradução precisa do Gemini para <lang> tags)
            # Conselhos e opiniões
            "o que acha", "o que você acha", "sua opinião",
            "me ajuda", "me ajude", "sugere", "sugira", "recomenda",
        ]
        
        # Keywords que indicam necessidade de tools (NÃO é simple query)
        tool_keywords = [
            "tempo", "clima", "previsão", "chuva", "sol",
            "trânsito", "transito", "rota", "caminho",
            "lista", "compras", "compra", "adicione", "adiciona",
            "remova", "remove", "apague", "apaga",
            "alarme", "timer", "cronômetro", "cronometro",
            "lembrete", "desperte", "despertador", "acorde",
            "daqui a", "daqui ", "minutos", "minuto",
            "toque", "toca", "tocar", "música", "musica", "spotify",
            "pause", "pausa", "pule", "pula", "próxima", "proxima",
            "volume",
            "receita", "ingrediente", "passo",
            "sonho", "sonhei", "diário",
            "quiz", "pergunta", "prova", "tarefa escolar",
            "agenda", "compromisso", "evento", "calendário",
            "notícia", "noticia", "manchete", "jornal", "news",
            "memorize", "memoriza", "lembre", "lembra", "guarde", "guarda",
            "que horas", "que hora", "que dia", "que data",
            "filme", "série", "serie",
            "tv", "televisão", "televisao",
            "abre", "abrir", "abri",
            "netflix", "globoplay", "disney", "prime", "hbo", "max", "apple tv",
            "youtube", "yt", "live", "podcast",
            "claro tv", "claro tv+", "claro"
        ]
        
        text_lower = text.lower().strip()
        # Remove wake word do início se presente (ex: "alfredo conte uma piada" -> "conte uma piada")
        wake_prefixes = ["alfredo", "alfre", "fredo", "al fredo", "hey alfredo", "ok alfredo"]
        for prefix in wake_prefixes:
            if text_lower.startswith(prefix + " "):
                text_lower = text_lower[len(prefix) + 1:]
                break
        
        # Se contém keyword de tool, NÃO é simple query (precisa do Gemini para tool calling)
        if any(kw in text_lower for kw in tool_keywords):
            return False
        
        words = set(text_lower.split())
        if any(text_lower.startswith(kw) for kw in simple_keywords):
            return True
        if any(kw in words for kw in simple_keywords if " " not in kw):
            return True
        # Queries curtas (até 5 palavras) sem menção de tools são conversacionais
        if len(text_lower.split()) <= 5:
            return True
        return False

    def _process_fast(self, text: str, context: Dict[str, Any]) -> str:
        """Fast path via Groq (~300ms) para queries conversacionais sem tools."""
        if not self.groq_client:
            return None
        import random
        system = (
            "Você é o Alfredo, assistente residencial amigável e natural. "
            "Responda com 1-2 frases curtas e diretas. NUNCA use emojis. "
            "Se o usuário te chamar de Alexa, não corrija — é apenas a wake word do sistema. "
            f"Seja variado e criativo — nunca repita respostas (Semente aleatória: {random.randint(1,10000)})."
        )
        db = context.get("db")
        room_id = context.get("room_id")
        if db and room_id:
            try:
                from core.brain.memory import models
                memory_facts = db.query(models.MemoryFact).filter(models.MemoryFact.room_id == room_id).all()
                if memory_facts:
                    memories = "\n".join([f"- {m.fact}" for m in memory_facts])
                    system += f"\n\nFatos sobre o usuário:\n{memories}"
                # Injetar mini-histórico para contexto conversacional
                from datetime import datetime, timedelta, timezone
                ten_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=10)
                last_interactions = db.query(models.Interaction).filter(
                    models.Interaction.room_id == room_id,
                    models.Interaction.input_text.isnot(None),
                    models.Interaction.output_text.isnot(None),
                    models.Interaction.input_text != "",
                    models.Interaction.timestamp >= ten_minutes_ago
                ).order_by(models.Interaction.id.desc()).limit(2).all()
                if last_interactions:
                    history = ""
                    for interaction in reversed(last_interactions):
                        history += f"Usuário: {interaction.input_text}\nAlfredo: {interaction.output_text}\n"
                    system += f"\n\nHistórico recente:\n{history}"
            except Exception:
                pass
        
        # Injetar horário atual
        from datetime import datetime
        now = datetime.now()
        system += f"\n\nHorário atual: {now.strftime('%d/%m/%Y %H:%M')}"
        
        try:
            import time
            t_start = time.time()
            completion = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": text}
                ],
                temperature=0.8,
                max_tokens=200,
                timeout=2.5  # Prevent hanging for 1 minute
            )
            result = completion.choices[0].message.content.strip()
            latency = int((time.time() - t_start) * 1000)
            logger.info(f"Groq fast path respondeu em {latency}ms")
            return result
        except Exception as e:
            logger.error(f"Erro no fast path do Groq: {e}")
            return None

    async def _process_fast_stream(self, text: str, context: Dict[str, Any]):
        """Fast path via Groq (~300ms) com streaming real de tokens."""
        if not self.groq_client:
            return
        import random
        system = (
            "Você é o Alfredo, assistente residencial amigável e natural. "
            "Responda com 1-2 frases curtas e diretas. NUNCA use emojis. "
            "Se o usuário te chamar de Alexa, não corrija — é apenas a wake word do sistema. "
            f"Seja variado e criativo — nunca repita respostas (Semente aleatória: {random.randint(1,10000)})."
        )
        db = context.get("db")
        room_id = context.get("room_id")
        if db and room_id:
            try:
                from core.brain.memory import models
                memory_facts = db.query(models.MemoryFact).filter(models.MemoryFact.room_id == room_id).all()
                if memory_facts:
                    memories = "\n".join([f"- {m.fact}" for m in memory_facts])
                    system += f"\n\nFatos sobre o usuário:\n{memories}"
                from datetime import datetime, timedelta, timezone
                ten_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=10)
                last_interactions = db.query(models.Interaction).filter(
                    models.Interaction.room_id == room_id,
                    models.Interaction.input_text.isnot(None),
                    models.Interaction.output_text.isnot(None),
                    models.Interaction.input_text != "",
                    models.Interaction.timestamp >= ten_minutes_ago
                ).order_by(models.Interaction.id.desc()).limit(2).all()
                if last_interactions:
                    history = ""
                    for interaction in reversed(last_interactions):
                        history += f"Usuário: {interaction.input_text}\nAlfredo: {interaction.output_text}\n"
                    system += f"\n\nHistórico recente:\n{history}"
            except Exception:
                pass
        
        from datetime import datetime
        now = datetime.now()
        system += f"\n\nHorário atual: {now.strftime('%d/%m/%Y %H:%M')}"
        
        try:
            import time, asyncio
            t_start = time.time()
            
            # Groq client is synchronous, so we run the streaming request in a thread
            def do_stream():
                return self.groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": text}
                    ],
                    temperature=0.8,
                    max_tokens=200,
                    stream=True,
                    timeout=3.0
                )
            
            stream = await asyncio.to_thread(do_stream)
            
            buffer = ""
            first_chunk = True
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    buffer += content
                    if first_chunk:
                        logger.info(f"Groq TTFB (Time to First Byte): {int((time.time() - t_start) * 1000)}ms")
                        first_chunk = False
                    
                    sentences = self._extract_sentences(buffer)
                    for sentence in sentences:
                        yield sentence
                    buffer = self._get_remainder(buffer)
                    await asyncio.sleep(0)  # Yield ao event loop
                    
            if buffer.strip():
                yield buffer.strip()
                
        except Exception as e:
            logger.error(f"Erro no fast path stream do Groq: {e}")

    @staticmethod
    def _split_sentences(text: str):
        """Divide texto em frases por pontuação final (.?!)."""
        remainder = text.strip()
        while remainder:
            for sep in [". ", "? ", "! ", "\n\n"]:
                idx = remainder.find(sep)
                if idx != -1:
                    sentence = remainder[:idx + len(sep)].strip()
                    if sentence:
                        yield sentence
                    remainder = remainder[idx + len(sep):].strip()
                    break
            else:
                yield remainder
                return

    @staticmethod
    def _extract_sentences(buffer: str):
        """Extrai frases completas do início do buffer (para streaming)."""
        import re
        while True:
            # Encontra pontuações (. ? !) seguidas de espaço, quebra de linha, ou final do buffer atual
            match = re.search(r'([.?!])(?:\s+|\n|$)', buffer)
            if match:
                idx = match.end(1) # Corta exatamente depois da pontuação
                sentence = buffer[:idx].strip()
                if sentence:
                    yield sentence
                buffer = buffer[match.end():].strip()
            else:
                break

    @staticmethod
    def _get_remainder(buffer: str) -> str:
        """Retorna o resto do texto que não formou uma frase completa ainda."""
        import re
        while True:
            match = re.search(r'([.?!])(?:\s+|\n|$)', buffer)
            if match:
                buffer = buffer[match.end():].strip()
            else:
                break
        return buffer

    def process(self, text: str, context: Dict[str, Any]) -> str:
        # Semantic Router Intercept — executa tools determinísticas sem Gemini
        match = self.semantic_router.match(text)
        if match:
            tool_name, tool_args, direct_response = match
            skill = self.skills.get(tool_name)
            if skill:
                if hasattr(skill, "execute_tool"):
                    if tool_name in ("manage_calendar",):
                        tool_args["_text"] = text
                    result = skill.execute_tool(tool_args, context)
                else:
                    result = skill.execute(text, context)
                if isinstance(result, str):
                    return result
                elif isinstance(result, dict) and result.get("direct_response"):
                    return result["direct_response"]
            if direct_response:
                return direct_response

        # Fast path: Groq para queries simples que não precisam de ferramentas
        if self._is_simple_query(text):
            fast_result = self._process_fast(text, context)
            if fast_result:
                logger.info(f"Groq fast path: {fast_result[:60]}...")
                return fast_result
            logger.info("Groq fast path falhou, caindo para Gemini")

        keys = _load_gemini_keys()
        if not keys:
            return "Erro: Nenhuma chave do Gemini configurada no .env (utilize GEMINI_API_KEYS)."

        current_key, selected_key_number = _select_next_gemini_key(keys)
        if not current_key:
            return "Erro: Nenhuma chave do Gemini configurada no .env (utilize GEMINI_API_KEYS)."

        logger.info(f"Revezamento: Usando chave do Gemini [{selected_key_number} de {len(keys)}] para esta requisição.")
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
                    
            # 2. Fetch long-term memories using RAG (Vector Search)
            memory_facts = db.query(models.MemoryFact).filter(models.MemoryFact.room_id == room_id).all()
            if memory_facts:
                try:
                    import json
                    from core.services.embedding_service import get_embedding, cosine_similarity
                    # Obtém vetor da fala do usuário
                    user_vec = get_embedding(text)
                    relevant_memories = []
                    
                    if user_vec:
                        for memory in memory_facts:
                            if not memory.embedding:
                                # Se é um dado legado sem embedding, nós mantemos por garantia ou ignoramos?
                                # Por segurança, incluiremos dados sem embeddings ou com falhas
                                relevant_memories.append((1.0, memory.fact))
                                continue
                                
                            try:
                                mem_vec = json.loads(memory.embedding)
                                sim = cosine_similarity(user_vec, mem_vec)
                                if sim > 0.3: # Threshold
                                    relevant_memories.append((sim, memory.fact))
                            except Exception as e:
                                logger.error(f"Erro ao calcular RAG da memória ID {memory.id}: {e}")
                                relevant_memories.append((1.0, memory.fact))
                        
                        # Ordena pela similaridade decrescente e pega os Top 5
                        relevant_memories.sort(key=lambda x: x[0], reverse=True)
                        top_memories = relevant_memories[:5]
                        
                        if top_memories:
                            memories_str = [f"- {m[1]}" for m in top_memories]
                            long_term_memory = "\nFatos permanentes relevantes conhecidos sobre o usuário (Contexto Local):\n" + "\n".join(memories_str)
                        else:
                            long_term_memory = ""
                    else:
                        # Fallback se a API do Google GenAI falhar no embedding
                        memories_str = [f"- {m.fact}" for m in memory_facts[:5]]
                        long_term_memory = "\nFatos permanentes conhecidos sobre o usuário:\n" + "\n".join(memories_str)
                except Exception as e:
                    logger.error(f"Erro fatal no pipeline RAG: {e}")
                    long_term_memory = ""
            else:
                long_term_memory = ""

            # 3. Fetch active session state
            session = db.query(models.SessionState).filter(models.SessionState.room_id == room_id).first()
            if session:
                try:
                    state_dict = json.loads(session.state_data) if session.state_data else {}
                except (json.JSONDecodeError, TypeError):
                    state_dict = {}
                skill = session.skill_name
                params_str = "; ".join(f"{k}: {v}" for k, v in state_dict.items() if k != "end")
                session_context = (
                    f"\nContexto de sessão ativa: você estava em [{skill}] com os parâmetros ({params_str}). "
                    f"Continue naturalmente de onde parou. Se o usuário quiser encerrar, finalize a sessão."
                )
            else:
                session_context = ""
        else:
            long_term_memory = ""
            session_context = ""

        system_prompt = (
            "Você é o Alfredo, assistente residencial amigável e natural. "
            "Respostas utilitárias (horas/clima) sejam diretas. Respostas criativas (piadas/histórias) sejam variadas e surpreendentes — NUNCA repita a mesma piada. "
            "NUNCA use emojis. "
            "Se o usuário te chamar de Alexa, não corrija — é apenas a wake word do sistema. "
            "Traduções: use <lang=\"LOCALE\">texto</lang> (ex: <lang=\"en-US\">apple</lang>). "
            "Quiz ativo: valide, corrija e faça nova pergunta. "
            "Receita ativa: UM passo por vez, sempre cite o prato. "
            "REGRA CRÍTICA: se existe uma ferramenta para a ação pedida (lista, timer/despertador, TV, música, agenda, memória), você DEVE chamá-la. "
            "NUNCA diga que vai fazer algo (ex: 'vou adicionar', 'configurando o alarme') sem de fato invocar a function correspondente — isso engana o usuário, pois nada é executado."
        )
        
        if long_term_memory:
            system_prompt += f"\n{long_term_memory}"
            
        if session_context:
            system_prompt += session_context

        if history_str:
            system_prompt += f"\n\nHistórico recente:\n{history_str}"
            
        from datetime import datetime
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo("America/Sao_Paulo"))
        system_prompt += f"\n\nContexto Oculto do Sistema:\n- Horário e data atual exatos: {now.strftime('%d/%m/%Y %H:%M:%S')}"
        tools = self._get_tools_schema()
        model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            tools=tools,
            system_instruction=system_prompt,
            generation_config=genai.GenerationConfig(temperature=0.9)
        )

        try:
            import time
            start_time = time.time()
            logger.info("Enviando requisição ao Gemini para Tool Calling...")
            chat = model.start_chat()
            response = chat.send_message(text)
            latency_ms = int((time.time() - start_time) * 1000)
            
            tokens = 0
            if response.usage_metadata:
                tokens = response.usage_metadata.total_token_count

            if response.parts:
                part = response.parts[0]
                if part.function_call:
                    # Preserva qualquer texto que o Gemini gerou junto com a tool call
                    try:
                        gemini_text = response.text
                    except (ValueError, AttributeError):
                        gemini_text = ""
                    if gemini_text.strip():
                        logger.info(f"Gemini gerou texto + tool: {gemini_text[:60]}...")

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

                    # Persist session state if skill returned session data
                    if isinstance(tool_result_obj, dict):
                        session_data = tool_result_obj.get("session")
                        if session_data is not None and db and room_id:
                            from datetime import datetime, timezone
                            existing = db.query(models.SessionState).filter(
                                models.SessionState.room_id == room_id
                            ).first()
                            if session_data.get("end"):
                                if existing:
                                    db.delete(existing)
                                    db.commit()
                                    logger.info(f"Sessão encerrada para sala {room_id}")
                            else:
                                if existing:
                                    existing.skill_name = function_name
                                    existing.state_data = json.dumps(session_data.get("params", {}))
                                    existing.updated_at = datetime.now(timezone.utc)
                                else:
                                    new_session = models.SessionState(
                                        room_id=room_id,
                                        skill_name=function_name,
                                        state_data=json.dumps(session_data.get("params", {}))
                                    )
                                    db.add(new_session)
                                db.commit()
                                logger.info(f"Sessão salva para sala {room_id}: {function_name}")

                    # DIRECT RESPONSE OPTIMIZATION:
                    # If tool returned a string or has direct_response, skip second Gemini call
                    if isinstance(tool_result_obj, str):
                        logger.info(f"Tool retornou string direta — pulando segunda chamada Gemini")
                        if db and room_id:
                            from core.brain.memory import models
                            ai_usage = models.AIUsage(
                                provider=f"Gemini (Key {selected_key_number})",
                                tokens_used=tokens,
                                latency_ms=latency_ms,
                                room_id=room_id
                            )
                            db.add(ai_usage)
                            db.commit()
                        return tool_result_obj
                    if isinstance(tool_result_obj, dict) and tool_result_obj.get("direct_response"):
                        logger.info(f"Tool tem direct_response — pulando segunda chamada Gemini")
                        if db and room_id:
                            from core.brain.memory import models
                            ai_usage = models.AIUsage(
                                provider=f"Gemini (Key {selected_key_number})",
                                tokens_used=tokens,
                                latency_ms=latency_ms,
                                room_id=room_id
                            )
                            db.add(ai_usage)
                            db.commit()
                        # Concatena o texto do Gemini com o resultado real da tool
                        if gemini_text.strip():
                            return f"{gemini_text} {tool_result_obj['direct_response']}"
                        return tool_result_obj["direct_response"]

                    logger.info("Enviando resultado da ferramenta de volta para o Gemini...")
                    tool_start_time = time.time()
                    tool_response = chat.send_message(
                        genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name=function_name,
                                response={"result": tool_result_obj}
                            )
                        )
                    )
                    latency_ms += int((time.time() - tool_start_time) * 1000)
                    if tool_response.usage_metadata:
                        tokens += tool_response.usage_metadata.total_token_count
                    
                    # Salva no banco de dados
                    if db and room_id:
                        from core.brain.memory import models
                        ai_usage = models.AIUsage(
                            provider=f"Gemini (Key {selected_key_number})",
                            tokens_used=tokens,
                            latency_ms=latency_ms,
                            room_id=room_id
                        )
                        db.add(ai_usage)
                        db.commit()
                        
                    final_text = tool_response.text.strip()
                    logger.info(f"Resposta final gerada: {final_text}")
                    return final_text
                else:
                    logger.info("Nenhuma ferramenta acionada. Resposta direta do Gemini.")
                    
                    # Salva no banco de dados
                    if db and room_id:
                        from core.brain.memory import models
                        ai_usage = models.AIUsage(
                            provider=f"Gemini (Key {selected_key_number})",
                            tokens_used=tokens,
                            latency_ms=latency_ms,
                            room_id=room_id
                        )
                        db.add(ai_usage)
                        db.commit()
                        
                        
                    return response.text.strip()
            
            logger.warning(f"Gemini retornou parts vazias. Finish reason: {response.candidates[0].finish_reason if response.candidates else 'Unknown'}. Fallback sem tools...")
            model_fallback = genai.GenerativeModel(
                model_name='gemini-2.5-flash',
                system_instruction=system_prompt,
                generation_config=genai.GenerationConfig(temperature=0.9)
            )
            chat_fallback = model_fallback.start_chat()
            fallback_resp = chat_fallback.send_message(text)
            
            if fallback_resp.parts:
                return fallback_resp.text.strip()
                
            return "Desculpe, não entendi a resposta do meu novo cérebro."
            
        except Exception as e:
            logger.error(f"Erro na API do Gemini: {e}")
            return "Tive um problema de comunicação com o meu núcleo neural."
    async def process_stream_async(self, text: str, context: Dict[str, Any]):
        """
        Gera a resposta via stream verdadeiro do Gemini, fazendo yield de frases
        completas conforme chegam para que o TTS possa começar a falar imediatamente.
        
        Para tool calls, executa a skill e faz yield do resultado (ou re-envia
        ao Gemini para formatação, também em streaming real).
        """
        import asyncio
        import time

        # ──────────────────────────────────────────────────────────────
        # FAST INTERCEPT: Semantic routing local para comandos diretos (<5ms)
        # ──────────────────────────────────────────────────────────────
        
        db = context.get("db")
        room_id = context.get("room_id")
        
        session_active = False
        if db and room_id:
            from core.brain.memory import models
            session = db.query(models.SessionState).filter(models.SessionState.room_id == room_id).first()
            if session:
                session_active = True
                
        if not session_active:
            match = self.semantic_router.match(text)
            if match:
                tool_name, tool_args, direct_response = match
                
                # Registra TTFB rápido caso a tool demore muito (o generator só envia chunks)
                # O direct_response pode ser feito no yield, mas se precisar chamar a skill:
                if direct_response:
                    for sentence in self._extract_sentences(direct_response):
                        yield sentence
                    remainder = self._get_remainder(direct_response)
                    if remainder.strip():
                        yield remainder.strip()
                    
                    # Chama a tool async pra executar a ação por trás dos panos (TV, música)
                    skill = self.skills.get(tool_name)
                    if skill:
                        if not hasattr(self, '_bg_tasks'):
                            self._bg_tasks = set()
                        if hasattr(skill, "execute_tool"):
                            task = asyncio.create_task(
                                asyncio.to_thread(skill.execute_tool, tool_args, context)
                            )
                        else:
                            task = asyncio.create_task(
                                asyncio.to_thread(skill.execute, text, context)
                            )
                        self._bg_tasks.add(task)
                        task.add_done_callback(self._bg_tasks.discard)
                    return
                else:
                    # Precisamos da skill pra gerar a resposta (ex: pegar horas)
                    skill = self.skills.get(tool_name)
                    if skill:
                        if hasattr(skill, "execute_tool"):
                            if tool_name in ("manage_calendar",):
                                tool_args["_text"] = text
                            result = await asyncio.to_thread(skill.execute_tool, tool_args, context)
                        else:
                            result = await asyncio.to_thread(skill.execute, text, context)
                            
                        # Manda o resultado (string direta ou do dict direct_response)
                        if isinstance(result, str):
                            for sentence in self._extract_sentences(result):
                                yield sentence
                            remainder = self._get_remainder(result)
                            if remainder.strip():
                                yield remainder.strip()
                            return
                        elif isinstance(result, dict) and result.get("direct_response"):
                            for sentence in self._extract_sentences(result["direct_response"]):
                                yield sentence
                            remainder = self._get_remainder(result["direct_response"])
                            if remainder.strip():
                                yield remainder.strip()
                            return

        # ──────────────────────────────────────────────────────────────
        # FIX DE LATÊNCIA: checar o fast path do Groq ANTES de mexer no
        # cliente do Gemini. Antes, a rotação de chave + limpeza do cache
        # do SDK (_client_manager.clients.clear() + genai.configure())
        # rodava em TODA requisição, mesmo nas que caem no fast path e
        # nunca chegam a chamar o Gemini nesse turno. Isso forçava a
        # reconstrução do cliente HTTP/gRPC (custo de conexão) à toa.
        # Movendo pra depois do fast path, esse custo só é pago quando
        # o Gemini de fato vai ser usado.
        # ──────────────────────────────────────────────────────────────

        # Fast path: Groq para queries simples que não precisam de ferramentas
        if self._is_simple_query(text, context):
            success = False
            async for chunk in self._process_fast_stream(text, context):
                yield chunk
                success = True
            
            if success:
                return
                
            logger.info("Groq fast path (stream) falhou, caindo para Gemini (stream)")
        keys = _load_gemini_keys()
        if not keys:
            yield "Erro: Nenhuma chave do Gemini configurada."
            return

        current_key, selected_key_number = _select_next_gemini_key(keys)
        if not current_key:
            yield "Erro: Nenhuma chave do Gemini configurada."
            return

        logger.info(f"Revezamento: Usando chave do Gemini [{selected_key_number} de {len(keys)}] para este stream.")

        # Limpar o cache do SDK para forçar a nova chave de API em clientes assíncronos
        # (só executado agora, quando realmente vamos chamar o Gemini)
        try:
            from google.generativeai.client import _client_manager
            _client_manager.clients.clear()
        except Exception:
            pass

        genai.configure(api_key=current_key)

        # Montar contexto idêntico ao `process`
        db = context.get("db")
        room_id = context.get("room_id")
        history_str = ""
        long_term_memory = ""
        session_context = ""
        
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
                    
            memory_facts = db.query(models.MemoryFact).filter(models.MemoryFact.room_id == room_id).all()
            if memory_facts:
                long_term_memory = "\nFatos permanentes conhecidos sobre o usuário:\n" + "\n".join([f"- {m.fact}" for m in memory_facts])

            # Fetch active session state
            session = db.query(models.SessionState).filter(models.SessionState.room_id == room_id).first()
            if session:
                try:
                    state_dict = json.loads(session.state_data) if session.state_data else {}
                except (json.JSONDecodeError, TypeError):
                    state_dict = {}
                skill = session.skill_name
                params_str = "; ".join(f"{k}: {v}" for k, v in state_dict.items() if k != "end")
                session_context = (
                    f"\nContexto de sessão ativa: você estava em [{skill}] com os parâmetros ({params_str}). "
                    f"Continue naturalmente de onde parou. Se o usuário quiser encerrar, finalize a sessão."
                )

        system_prompt = (
            "Você é o Alfredo, um assistente virtual ultra avançado para automação residencial. "
            "Responda sempre de forma natural, amigável e conversacional. Seja breve, no máximo 2 frases. "
            "NUNCA utilize emojis ou símbolos complexos nas suas respostas. "
            "Se o usuário te chamar de Alexa, não corrija — é apenas a wake word do sistema. "
            "Traduções: use <lang=\"LOCALE\">texto</lang> (ex: <lang=\"en-US\">apple</lang>). "
            "REGRA CRÍTICA: se existe uma ferramenta para a ação pedida (lista, timer/despertador, TV, música, agenda, memória), você DEVE chamá-la. "
            "NUNCA diga que vai fazer algo sem de fato invocar a function correspondente."
        )
        if long_term_memory: system_prompt += f"\n{long_term_memory}"
        if session_context: system_prompt += session_context
        if history_str: system_prompt += f"\n\nHistórico recente:\n{history_str}"
        
        # Forçamos a injeção do horário atual
        from datetime import datetime
        now = datetime.now()
        system_prompt += f"\n\nContexto Oculto do Sistema:\n- Horário e data atual exatos: {now.strftime('%d/%m/%Y %H:%M:%S')}"
        
        tools = self._get_tools_schema()
        
        model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            system_instruction=system_prompt,
            tools=tools,
            generation_config=genai.GenerationConfig(temperature=0.8)
        )
        
        chat = model.start_chat()
        
        logger.info("Iniciando requisição ao Gemini (Stream)...")
        t_start = time.time()
        
        response = await chat.send_message_async(text, stream=True)
        
        buffer = ""
        first_chunk = False
        is_tool = False
        tool_calls_to_execute = []
        
        try:
            async for chunk in response:
                try:
                    if chunk.parts:
                        for part in chunk.parts:
                            if part.function_call:
                                is_tool = True
                                tool_calls_to_execute.append({
                                    "name": part.function_call.name,
                                    "args": type(part.function_call).to_dict(part.function_call).get("args", {})
                                })
                except Exception:
                    pass

                chunk_text = ""
                try:
                    chunk_text = chunk.text
                except Exception:
                    pass

                if chunk_text:
                    if not first_chunk:
                        logger.info(f"GEMINI TTFB (Primeiro Chunk): {time.time() - t_start:.3f}s")
                        first_chunk = True
                    buffer += chunk_text
                    
                    # STREAMING REAL: yield frases completas imediatamente
                    # para que o TTS comece a falar enquanto o Gemini gera o resto
                    for sentence in self._extract_sentences(buffer):
                        yield sentence
                    buffer = self._get_remainder(buffer)
        except Exception as e:
            logger.error(f"Erro no stream do Gemini: {e}")
            if not first_chunk:
                yield "Tive uma pequena falha nos meus circuitos, mas já estou de volta."

        if is_tool and tool_calls_to_execute:
            tool_responses_list = []
            direct_response_accumulated = ""
            
            for t_call in tool_calls_to_execute:
                t_name = t_call["name"]
                t_args = t_call["args"]
                logger.info(f"Tool Call detectado no stream: {t_name} ({time.time() - t_start:.2f}s). Executando...")
                
                skill = self.skills.get(t_name)
                tool_result_obj = None
                if skill:
                    if hasattr(skill, "execute_tool"):
                        tool_result_obj = await asyncio.to_thread(skill.execute_tool, t_args, context)
                    else:
                        tool_result_obj = await asyncio.to_thread(skill.execute, text, context)

                    # Persist session state if skill returned session data
                    if isinstance(tool_result_obj, dict):
                        session_data = tool_result_obj.get("session")
                        if session_data is not None and db and room_id:
                            from datetime import datetime, timezone
                            existing = db.query(models.SessionState).filter(
                                models.SessionState.room_id == room_id
                            ).first()
                            if session_data.get("end"):
                                if existing:
                                    db.delete(existing)
                                    db.commit()
                                    logger.info(f"Sessão encerrada para sala {room_id}")
                            else:
                                if existing:
                                    existing.skill_name = t_name
                                    existing.state_data = json.dumps(session_data.get("params", {}))
                                    existing.updated_at = datetime.now(timezone.utc)
                                else:
                                    new_session = models.SessionState(
                                        room_id=room_id,
                                        skill_name=t_name,
                                        state_data=json.dumps(session_data.get("params", {}))
                                    )
                                    db.add(new_session)
                                db.commit()
                                logger.info(f"Sessão salva para sala {room_id}: {t_name}")

                if isinstance(tool_result_obj, str):
                    direct_response_accumulated += tool_result_obj + " "
                    tool_responses_list.append(genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=t_name,
                            response={"result": tool_result_obj}
                        )
                    ))
                elif isinstance(tool_result_obj, dict) and tool_result_obj.get("direct_response"):
                    direct_response_accumulated += tool_result_obj["direct_response"] + " "
                    tool_responses_list.append(genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=t_name,
                            response={"result": tool_result_obj}
                        )
                    ))
                else:
                    tool_responses_list.append(genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=t_name,
                            response={"result": tool_result_obj if tool_result_obj else "Desculpe, a ferramenta solicitada não existe."}
                        )
                    ))

            if direct_response_accumulated.strip():
                logger.info(f"Tool(s) retornaram string direta — pulando segunda chamada Gemini")
                direct = f"{buffer} {direct_response_accumulated.strip()}" if buffer.strip() else direct_response_accumulated.strip()
                yield direct.strip()
                buffer = ""  # Já fez yield
            else:
                # Segunda chamada ao Gemini para formatar a resposta da tool — TAMBÉM em streaming real
                logger.info("Enviando resultado(s) da tool ao Gemini (stream)...")
                # Mandar todas as partes de uma vez
                tool_response_stream = await chat.send_message_async(tool_responses_list, stream=True)

                async for chunk in tool_response_stream:
                    chunk_text = ""
                    try:
                        chunk_text = chunk.text
                    except Exception:
                        pass
                        
                    if chunk_text:
                        buffer += chunk_text
                        # Streaming real também na segunda chamada
                        for sentence in self._extract_sentences(buffer):
                            yield sentence
                        buffer = self._get_remainder(buffer)

        # Yield qualquer sobra restante no buffer
        if buffer.strip():
            yield buffer.strip()
        
        total_time = time.time() - t_start
        logger.info(f"Pipeline LLM concluído em {total_time:.2f}s")

_router_instance = None

def get_router():
    """Singleton: evita re-instanciar 14 skills a cada request."""
    global _router_instance
    if _router_instance is None:
        _router_instance = AgentRouter()
    return _router_instance