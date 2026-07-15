import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from core.brain.skills.base import Skill
from core.brain.memory import models

logger = logging.getLogger("alfredo.skills.routine")

# Mapeamento de dias da semana em inglês (Gemini) -> formato do scheduler (0=Sunday)
_DIAS_SEMANA = {
    "sunday": 0, "monday": 1, "tuesday": 2, "wednesday": 3,
    "thursday": 4, "friday": 5, "saturday": 6,
    "domingo": 0, "segunda": 1, "terça": 2, "terca": 2,
    "quarta": 3, "quinta": 4, "sexta": 5, "sábado": 6, "sabado": 6,
}

# Trigger types que o scheduler atual suporta nativamente
_TRIGGERS_SUPORTADOS = {"time"}

def _mapear_dias(recurrence: List[str]) -> str:
    """Converte lista de nomes de dias para string CSV no formato do scheduler.

    Ex: ['monday', 'wednesday', 'friday'] -> '1,3,5'
    """
    numeros = set()
    for dia in recurrence:
        dia_lower = dia.strip().lower()
        num = _DIAS_SEMANA.get(dia_lower)
        if num is not None:
            numeros.add(str(num))
    if not numeros:
        # Padrão: todos os dias
        return "0,1,2,3,4,5,6"
    return ",".join(sorted(numeros, key=lambda x: (int(x) + 6) % 7))  # começa na segunda


class RoutineSkill(Skill):
    """Skill para criar, atualizar e deletar rotinas de automação via voz.

    Mapeia linguagem natural do usuário para a tabela `routines` do banco,
    que é processada pelo scheduler existente.
    """

    @property
    def name(self) -> str:
        return "RoutineSkill"

    def can_handle(self, intent: str, text: str) -> bool:
        return intent == "ROUTINE"

    def execute(self, text: str, context: Dict[str, Any]) -> str:
        """Fallback legado — não usado pelo Gemini Tool Calling."""
        return "Use a ferramenta manage_routine para gerenciar rotinas."

    # ------------------------------------------------------------------
    # Schema da Tool exposta ao Gemini (definido no router.py)
    # ------------------------------------------------------------------
    @staticmethod
    def get_tool_schema() -> dict:
        """Retorna o schema function_declaration para o Gemini."""
        return {
            "name": "manage_routine",
            "description": (
                "GERENCIAR ROTINAS DE AUTOMAÇÃO: use esta ferramenta para CRIAR, ATUALIZAR ou DELETAR "
                "rotinas que o Alfredo executa automaticamente em horários agendados. "
                "EXEMPLOS de frases que você DEVE converter para esta ferramenta:\n"
                "- 'Toda segunda-feira às 7h da manhã, acende a luz do quarto e toca notícias'\n"
                "- '15 minutos antes do pôr do sol no Rio de Janeiro, acende a luz da varanda'\n"
                "- 'Quando a temperatura da sala passar de 30°C, liga o ar-condicionado'\n"
                "- 'Cria uma rotina para acender a luz da sala todo dia às 18h'\n"
                "- 'Apaga a rotina do café da manhã'\n\n"
                "IMPORTANTE: se o usuário pedir algo como 'acende a luz do quarto' sem contexto de "
                "recorrência/horário, NÃO invoque esta ferramenta — a ação deve ser tratada como "
                "comando único, não como rotina."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Ação a realizar: 'create' para criar, 'update' para alterar, 'delete' para remover.",
                        "enum": ["create", "update", "delete"]
                    },
                    "name": {
                        "type": "string",
                        "description": "Nome amigável da rotina (ex: 'Bom dia', 'Acender varanda', 'Café da manhã'). "
                                       "Se o usuário não der um nome explícito, gere um automaticamente baseado nas ações."
                    },
                    "trigger_type": {
                        "type": "string",
                        "description": (
                            "Tipo de gatilho da rotina:\n"
                            "- 'time': horário fixo (ex: '07:00', '18:30'). Suportado pelo sistema.\n"
                            "- 'sunset_offset': offset do pôr do sol (ex: '-15m' = 15 minutos antes). "
                            "ATENÇÃO: este tipo PODE NÃO estar implementado no scheduler. Avise o usuário se não for suportado.\n"
                            "- 'temperature_threshold': gatilho por temperatura (ex: '>30C'). "
                            "ATENÇÃO: este tipo PODE NÃO estar implementado no scheduler. Avise o usuário se não for suportado.\n"
                            "PADRÃO: 'time' se o usuário mencionar horário."
                        )
                    },
                    "trigger_value": {
                        "type": "string",
                        "description": (
                            "Valor do gatilho:\n"
                            "- Para trigger_type='time': horário no formato HH:MM (ex: '07:00', '18:30', '14:15'). "
                            "Converta '7h', '7 horas', 'sete da manhã' para '07:00'. 'meio-dia' -> '12:00'.\n"
                            "- Para trigger_type='sunset_offset': offset relativo ao pôr do sol "
                            "(ex: '-15m' para 15 minutos antes, '+30m' para 30 minutos depois).\n"
                            "- Para trigger_type='temperature_threshold': condição (ex: '>30C', '<18C')."
                        )
                    },
                    "recurrence": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Dias da semana em que a rotina deve ser executada. "
                            "Use ['monday','tuesday','wednesday','thursday','friday'] para dias úteis, "
                            "['saturday','sunday'] para fins de semana, "
                            "ou uma lista customizada como ['monday','wednesday','friday']. "
                            "Para 'todos os dias', use ['sunday','monday','tuesday','wednesday','thursday','friday','saturday'] "
                            "ou omita o parâmetro."
                        )
                    },
                    "actions_list": {
                        "type": "array",
                        "description": (
                            "LISTA DE AÇÕES que a rotina deve executar. "
                            "Cada ação é um objeto com 'device_type' e parâmetros específicos. "
                            "EXEMPLOS:\n"
                            "- Ligar/desligar dispositivo: {\"device_type\": \"light\", \"location\": \"bedroom\", \"state\": \"on\"}\n"
                            "- Falar mensagem: {\"device_type\": \"tts\", \"content\": \"Bom dia! Hoje está fazendo sol.\"}\n"
                            "- Comando de voz: {\"device_type\": \"command\", \"text\": \"como está o clima\"}\n"
                            "Se o usuário pedir ações que não se encaixam em device_type conhecido, "
                            "use 'command' com o texto natural."
                        ),
                        "items": {
                            "type": "object",
                            "properties": {
                                "device_type": {
                                    "type": "string",
                                    "description": "Tipo do dispositivo/ação: 'light' (luz), 'tts' (falar), 'command' (comando de voz genérico)."
                                },
                                "location": {
                                    "type": "string",
                                    "description": "Cômodo/local (ex: 'quarto', 'sala', 'varanda', 'cozinha'). Relevante para 'light'."
                                },
                                "state": {
                                    "type": "string",
                                    "description": "Estado do dispositivo: 'on' (ligar), 'off' (desligar). Relevante para 'light'."
                                },
                                "content": {
                                    "type": "string",
                                    "description": "Texto a ser falado. Relevante para device_type='tts'."
                                },
                                "text": {
                                    "type": "string",
                                    "description": "Comando em linguagem natural. Relevante para device_type='command'."
                                }
                            }
                        }
                    },
                    "routine_id": {
                        "type": "integer",
                        "description": "ID da rotina para ação 'update' ou 'delete'. Se não souber o ID, liste as rotinas primeiro buscando na memória."
                    }
                },
                "required": ["action"]
            }
        }

    # ------------------------------------------------------------------
    # Método principal: chamado pelo router quando o Gemini invoca a tool
    # ------------------------------------------------------------------
    def execute_tool(self, kwargs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Executa ações de gerenciamento de rotinas (create/update/delete).

        Chamado pelo AgentRouter quando o Gemini decide invocar 'manage_routine'.
        """
        db = context.get("db")
        room_id = context.get("room_id")

        if not db or not room_id:
            return {"error": "Sem acesso ao banco de dados ou sala. Contexto inválido."}

        action = kwargs.get("action")
        if action not in ("create", "update", "delete"):
            return {
                "error": f"Ação '{action}' não reconhecida. Use 'create', 'update' ou 'delete'.",
                "status": "fail"
            }

        if action == "create":
            return self._criar(kwargs, db, room_id)
        elif action == "update":
            return self._atualizar(kwargs, db, room_id)
        elif action == "delete":
            return self._deletar(kwargs, db, room_id)

        return {"error": "Ação não implementada.", "status": "fail"}

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------
    def _criar(self, kwargs: Dict[str, Any], db, room_id: str) -> Dict[str, Any]:
        trigger_type = kwargs.get("trigger_type", "time")
        trigger_value = kwargs.get("trigger_value")
        recurrence = kwargs.get("recurrence")
        actions_list = kwargs.get("actions_list", [])
        name = kwargs.get("name")

        # --- Validação: trigger suportado? ---
        if trigger_type not in _TRIGGERS_SUPORTADOS:
            msg = (
                f"O gatilho do tipo '{trigger_type}' ainda não é suportado pelo sistema de "
                f"agendamento atual. Seu scheduler trabalha com horários fixos ('time'). "
                f"Para '{trigger_type}', seria necessário uma extensão no scheduler. "
                f"Por enquanto, sugiro criar a rotina com trigger_type='time' se houver um "
                f"horário associado."
            )
            logger.warning(f"Trigger não suportado: {trigger_type}")
            return {
                "error": msg,
                "unsupported_trigger": trigger_type,
                "supported_triggers": list(_TRIGGERS_SUPORTADOS),
                "status": "fail"
            }

        # --- Validação: trigger_value obrigatório ---
        if not trigger_value:
            return {
                "error": "O parâmetro 'trigger_value' é obrigatório para criar uma rotina. "
                         "Ex: '07:00', '18:30'.",
                "status": "fail"
            }

        # --- Validação: formato HH:MM para trigger_type='time' ---
        if trigger_type == "time":
            if not self._validar_horario(trigger_value):
                return {
                    "error": f"O horário '{trigger_value}' não está num formato válido. "
                             f"Use HH:MM (ex: '07:00', '18:30', '14:15').",
                    "status": "fail"
                }

        # --- Validação: pelo menos uma ação ---
        if not actions_list:
            return {
                "error": "A rotina precisa de pelo menos uma ação (ex: acender luz, falar mensagem). "
                         "O parâmetro 'actions_list' está vazio.",
                "status": "fail"
            }

        # --- Monta o nome ---
        if not name:
            name = self._gerar_nome(actions_list, trigger_value)

        # --- Converte recurrence -> days_of_week ---
        days_of_week = _mapear_dias(recurrence) if recurrence else "0,1,2,3,4,5,6"

        # --- Serializa actions_list como JSON em action_value ---
        action_value = json.dumps(actions_list, ensure_ascii=False)
        action_type = "multi_action"

        # --- Persiste ---
        try:
            nova_rotina = models.Routine(
                name=name,
                trigger_type=trigger_type,
                trigger_value=trigger_value,
                action_type=action_type,
                action_value=action_value,
                room_id=room_id,
                is_active=True,
                days_of_week=days_of_week,
            )
            db.add(nova_rotina)
            db.commit()
            db.refresh(nova_rotina)

            logger.info(
                f"Rotina criada: id={nova_rotina.id} name='{name}' "
                f"trigger={trigger_type}:{trigger_value} days={days_of_week}"
            )

            # Acorda o scheduler para recalcular o próximo disparo
            from core.services.scheduler import wakeup_scheduler
            wakeup_scheduler()

            return {
                "status": "success",
                "routine_id": nova_rotina.id,
                "direct_response": self._montar_resposta_create(
                    name, trigger_type, trigger_value, days_of_week, actions_list
                )
            }

        except Exception as e:
            logger.error(f"Erro ao criar rotina no banco: {e}")
            db.rollback()
            return {
                "error": f"Erro ao salvar a rotina no banco de dados: {str(e)}",
                "status": "fail"
            }

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------
    def _atualizar(self, kwargs: Dict[str, Any], db, room_id: str) -> Dict[str, Any]:
        routine_id = kwargs.get("routine_id")
        if not routine_id:
            return {
                "error": "Informe o 'routine_id' da rotina que deseja atualizar.",
                "status": "fail"
            }

        rotina = db.query(models.Routine).filter(
            models.Routine.id == routine_id,
            models.Routine.room_id == room_id
        ).first()

        if not rotina:
            return {
                "error": f"Rotina com id {routine_id} não encontrada nesta sala.",
                "status": "fail"
            }

        # Aplica apenas campos fornecidos
        alteracoes = []
        if "name" in kwargs and kwargs["name"]:
            rotina.name = kwargs["name"]
            alteracoes.append("nome")
        if "trigger_type" in kwargs:
            trigger_type = kwargs["trigger_type"]
            if trigger_type not in _TRIGGERS_SUPORTADOS:
                return {
                    "error": f"Gatilho '{trigger_type}' não suportado. Tipos suportados: {list(_TRIGGERS_SUPORTADOS)}.",
                    "supported_triggers": list(_TRIGGERS_SUPORTADOS),
                    "status": "fail"
                }
            rotina.trigger_type = trigger_type
            alteracoes.append("tipo de gatilho")
        if "trigger_value" in kwargs and kwargs["trigger_value"]:
            if rotina.trigger_type == "time" and not self._validar_horario(kwargs["trigger_value"]):
                return {
                    "error": f"Horário '{kwargs['trigger_value']}' inválido. Formato esperado: HH:MM.",
                    "status": "fail"
                }
            rotina.trigger_value = kwargs["trigger_value"]
            alteracoes.append("horário")
        if "recurrence" in kwargs and kwargs["recurrence"]:
            rotina.days_of_week = _mapear_dias(kwargs["recurrence"])
            alteracoes.append("dias da semana")
        if "actions_list" in kwargs and kwargs["actions_list"]:
            rotina.action_value = json.dumps(kwargs["actions_list"], ensure_ascii=False)
            alteracoes.append("ações")

        try:
            db.commit()
            logger.info(f"Rotina {routine_id} atualizada: {', '.join(alteracoes)}")

            from core.services.scheduler import wakeup_scheduler
            wakeup_scheduler()

            return {
                "status": "success",
                "routine_id": routine_id,
                "direct_response": f"Rotina '{rotina.name}' atualizada com sucesso. "
                                   f"Alterações: {', '.join(alteracoes)}."
            }
        except Exception as e:
            logger.error(f"Erro ao atualizar rotina {routine_id}: {e}")
            db.rollback()
            return {"error": f"Erro ao atualizar: {str(e)}", "status": "fail"}

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------
    def _deletar(self, kwargs: Dict[str, Any], db, room_id: str) -> Dict[str, Any]:
        routine_id = kwargs.get("routine_id")

        if not routine_id:
            # Tenta encontrar pelo nome
            name = kwargs.get("name", "").strip().lower()
            if name:
                rotina = db.query(models.Routine).filter(
                    models.Routine.room_id == room_id,
                    models.Routine.name.ilike(f"%{name}%")
                ).first()
                if not rotina:
                    return {
                        "error": f"Não encontrei nenhuma rotina com o nome '{name}'.",
                        "status": "fail"
                    }
                routine_id = rotina.id
            else:
                return {
                    "error": "Informe o 'routine_id' ou o 'name' da rotina que deseja deletar.",
                    "status": "fail"
                }

        rotina = db.query(models.Routine).filter(
            models.Routine.id == routine_id,
            models.Routine.room_id == room_id
        ).first()

        if not rotina:
            return {
                "error": f"Rotina com id {routine_id} não encontrada.",
                "status": "fail"
            }

        nome_excluido = rotina.name
        try:
            db.delete(rotina)
            db.commit()
            logger.info(f"Rotina '{nome_excluido}' (id={routine_id}) deletada.")

            from core.services.scheduler import wakeup_scheduler
            wakeup_scheduler()

            return {
                "status": "success",
                "routine_id": routine_id,
                "direct_response": f"Rotina '{nome_excluido}' removida com sucesso."
            }
        except Exception as e:
            logger.error(f"Erro ao deletar rotina {routine_id}: {e}")
            db.rollback()
            return {"error": f"Erro ao deletar: {str(e)}", "status": "fail"}

    # ------------------------------------------------------------------
    # Utilitários
    # ------------------------------------------------------------------
    @staticmethod
    def _validar_horario(valor: str) -> bool:
        """Valida se o valor está no formato HH:MM com horas 0-23 e minutos 0-59."""
        try:
            partes = valor.strip().split(":")
            if len(partes) != 2:
                return False
            hora, minuto = int(partes[0]), int(partes[1])
            return 0 <= hora <= 23 and 0 <= minuto <= 59
        except (ValueError, IndexError):
            return False

    @staticmethod
    def _gerar_nome(actions_list: List[dict], trigger_value: str) -> str:
        """Gera um nome automático para a rotina baseado nas ações."""
        acoes_resumo = []
        for acao in actions_list:
            tipo = acao.get("device_type", "")
            if tipo == "light":
                local = acao.get("location", "")
                estado = acao.get("state", "")
                if local:
                    acoes_resumo.append(f"{local} {'ligada' if estado == 'on' else 'desligada'}")
                else:
                    acoes_resumo.append(f"luz {'ligada' if estado == 'on' else 'desligada'}")
            elif tipo == "tts":
                acoes_resumo.append("mensagem de voz")
            elif tipo == "command":
                acoes_resumo.append("comando automático")
            else:
                acoes_resumo.append(tipo)

        sufixo = f" às {trigger_value}" if trigger_value else ""
        if not acoes_resumo:
            return f"Rotina{sufixo}"
        return f"{' e '.join(acoes_resumo)}{sufixo}"

    @staticmethod
    def _formatar_dias(days_of_week: str) -> str:
        """Converte '0,1,2,3,4,5,6' em texto amigável em português."""
        dias_map = {
            "0": "domingo", "1": "segunda", "2": "terça", "3": "quarta",
            "4": "quinta", "5": "sexta", "6": "sábado"
        }
        nums = [d.strip() for d in days_of_week.split(",") if d.strip()]
        nomes = [dias_map.get(n, n) for n in nums]

        if len(nomes) == 7:
            return "todos os dias"
        if nomes == ["segunda", "terça", "quarta", "quinta", "sexta"]:
            return "dias úteis"
        if nomes == ["sábado", "domingo"]:
            return "aos fins de semana"

        if len(nomes) <= 2:
            return f"{' e '.join(nomes)}"
        return f"{', '.join(nomes[:-1])} e {nomes[-1]}"

    def _montar_resposta_create(
        self, name: str, trigger_type: str, trigger_value: str,
        days_of_week: str, actions_list: List[dict]
    ) -> str:
        """Monta uma resposta em PT-BR confirmando a criação da rotina."""
        dias_texto = self._formatar_dias(days_of_week)
        acoes_texto = []
        for acao in actions_list:
            tipo = acao.get("device_type", "")
            if tipo == "light":
                local = acao.get("location", "casa")
                estado = "ligar" if acao.get("state") == "on" else "desligar"
                acoes_texto.append(f"{estado} a luz d{'o' if local in ('quarto','escritório') else 'a'} {local}")
            elif tipo == "tts":
                acoes_texto.append(f"falar '{acao.get('content', 'mensagem')}'")
            elif tipo == "command":
                acoes_texto.append(f"executar '{acao.get('text', 'comando')}'")
            else:
                acoes_texto.append(tipo)

        if not acoes_texto:
            acoes_texto.append("executar ações programadas")

        if len(acoes_texto) > 1:
            acoes_frase = ", ".join(acoes_texto[:-1]) + f" e {acoes_texto[-1]}"
        else:
            acoes_frase = acoes_texto[0]

        if trigger_type == "time":
            return (
                f"Rotina criada! {name}: {acoes_frase} às {trigger_value}, "
                f"em {dias_texto}."
            )

        return (
            f"Rotina '{name}' criada com sucesso. "
            f"Vou {acoes_frase} quando o gatilho '{trigger_type}: {trigger_value}' for ativado."
        )
