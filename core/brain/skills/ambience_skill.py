"""
AmbienceSkill — Controle de som ambiente durante o TTS.

Tools:
  - set_ambient: ativa um som de fundo (chuva, floresta, café, fogo)
  - stop_ambient: desativa o som de fundo atual

A mixagem é feita no servidor: o áudio ambiente é mixado com o TTS
antes de enviar para o satélite. O satélite não precisa de nenhuma
mudança — toca o áudio já mixado como se fosse TTS normal.
"""

import logging
from typing import Dict, Any
from core.brain.skills.base import Skill
from core.voice.ambience import get_ambience_manager

logger = logging.getLogger("alfredo.skills.ambience")


class AmbienceSkill(Skill):
    @property
    def name(self) -> str:
        return "AmbienceSkill"

    def can_handle(self, intent: str, text: str) -> bool:
        return intent in ("SET_AMBIENT", "STOP_AMBIENT")

    def execute(self, text: str, context: Dict[str, Any]) -> str:
        """Método legado — não usado pelo fluxo Gemini."""
        return "Use o execute_tool para controlar o som ambiente."

    def execute_tool(self, kwargs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Roteia para set_ambient ou stop_ambient dependendo do nome da tool.
        O nome da tool é passado via kwargs['_tool_name'] pelo router.
        """
        tool_name = kwargs.get("_tool_name", "")
        ambience = get_ambience_manager()

        if tool_name == "set_ambient":
            return self._set_ambient(kwargs, ambience)
        elif tool_name == "stop_ambient":
            return self._stop_ambient(kwargs, ambience)
        else:
            return {
                "direct_response": "Não entendi qual ação de ambiente você quer.",
                "status": "error"
            }

    def _set_ambient(self, kwargs: Dict[str, Any], ambience) -> Dict[str, Any]:
        ambient_type = kwargs.get("ambient_type", "").strip().lower()
        if not ambient_type:
            opcoes = ", ".join(ambience.list_ambients())
            return {
                "direct_response": f"Qual ambiente? Opções: {opcoes}.",
                "error": "ambient_type vazio",
                "status": "error"
            }

        if ambience.set_ambient(ambient_type):
            return {
                "direct_response": f"Som de {ambient_type} ativado.",
                "status": "success"
            }
        else:
            opcoes = ", ".join(ambience.list_ambients())
            return {
                "direct_response": f"Ambiente '{ambient_type}' não encontrado. Opções: {opcoes}.",
                "error": f"unknown_ambient: {ambient_type}",
                "status": "error"
            }

    def _stop_ambient(self, kwargs: Dict[str, Any], ambience) -> Dict[str, Any]:
        if ambience.is_active:
            ambience.stop_ambient()
            return {
                "direct_response": "Som ambiente desligado.",
                "status": "success"
            }
        return {
            "direct_response": "Nenhum som ambiente estava ativo.",
            "status": "success"
            }
