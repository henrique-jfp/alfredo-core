import os
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, Any
from core.brain.skills.base import Skill

logger = logging.getLogger("alfredo.skills.safety")

class SafetySkill(Skill):
    @property
    def name(self) -> str:
        return "SafetySkill"

    def can_handle(self, intent: str, text: str) -> bool:
        return intent == "CHECK_INCIDENTS"

    def execute(self, text: str, context: Dict[str, Any]) -> str:
        return "Verificação de incidentes não suportada via comando direto (apenas tool calling)."

    def execute_tool(self, kwargs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        areas_input = kwargs.get("areas", "")
        if isinstance(areas_input, str):
            areas = [a.strip() for a in areas_input.split(",") if a.strip()]
        elif isinstance(areas_input, list):
            areas = areas_input
        else:
            areas = []
            
        if not areas:
            # Se o LLM não extraiu área, a gente checa a cidade toda ou avisa
            return {"status": "ok", "direct_response": "Nenhuma área específica fornecida para verificação de segurança, tente especificar o nome da via ou bairro."}

        logger.info(f"Checando incidentes de segurança nas áreas: {areas}")
        
        # Consultar APIs
        fc_incidents = self._check_fogo_cruzado(areas)
        cor_incidents = self._check_cor(areas)

        response_text = ""
        
        # Relatar Fogo Cruzado
        if fc_incidents:
            response_text += f"Atenção: Foram detectados {len(fc_incidents)} alertas recentes de segurança ou tiroteio no trajeto (Fogo Cruzado). "
        else:
            response_text += "Não há alertas recentes de tiroteios no seu caminho. "

        # Relatar Centro de Operações Rio
        if cor_incidents:
            joined_cor = ", ".join(cor_incidents[:3])
            if len(cor_incidents) > 3:
                joined_cor += " e outros."
            response_text += f"O Centro de Operações Rio relata os seguintes incidentes: {joined_cor}. "
        else:
            response_text += "Também não há interdições ou incidentes graves reportados pelo Centro de Operações Rio."

        return {
            "areas_checked": areas,
            "fogo_cruzado_count": len(fc_incidents),
            "cor_rio_count": len(cor_incidents),
            "direct_response": response_text
        }

    def _check_fogo_cruzado(self, areas: list) -> list:
        email = os.getenv("FOGO_CRUZADO_EMAIL")
        password = os.getenv("FOGO_CRUZADO_PASSWORD")
        if not email or not password:
            logger.warning("Credenciais do Fogo Cruzado não configuradas. Pulando verificação.")
            return []

        try:
            auth_resp = requests.post("https://api-service.fogocruzado.org.br/auth/login", json={"email": email, "password": password}, timeout=5)
            if auth_resp.status_code == 201:
                token = auth_resp.json().get("data", {}).get("accessToken")
                if token:
                    headers = {"Authorization": f"Bearer {token}"}
                    # Puxar dados das últimas 12 horas
                    start = (datetime.now() - timedelta(hours=12)).isoformat() + "Z"
                    resp = requests.get(f"https://api-service.fogocruzado.org.br/occurrences?initialDate={start}", headers=headers, timeout=5)
                    
                    if resp.status_code == 200:
                        data = resp.json().get("data", [])
                        matched = []
                        for occurrence in data:
                            address = str(occurrence.get("address", "")).lower()
                            city = str(occurrence.get("city", {}).get("name", "")).lower()
                            neighborhood = str(occurrence.get("neighborhood", {}).get("name", "")).lower()
                            
                            for area in areas:
                                area_l = str(area).lower()
                                if area_l in address or area_l in city or area_l in neighborhood:
                                    matched.append(occurrence)
                                    break
                        return matched
        except Exception as e:
            logger.error(f"Erro ao consultar Fogo Cruzado: {e}")
        
        return []

    def _check_cor(self, areas: list) -> list:
        try:
            # Endpoint oficial de ocorrências abertas do COR
            resp = requests.get("https://api.dados.rio/v2/ocorrencias/", timeout=5)
            if resp.status_code == 200:
                data = resp.json().get("eventos", [])
                matched = []
                for event in data:
                    if event.get("status") != "Aberto":
                        continue
                        
                    desc = str(event.get("descricao", "")).lower()
                    bairro = str(event.get("bairro", "")).lower()
                    
                    for area in areas:
                        area_l = str(area).lower()
                        if area_l in desc or area_l in bairro:
                            matched.append(event.get("descricao", "Incidente"))
                            break
                return matched
        except Exception as e:
            logger.error(f"Erro ao consultar Centro de Operações Rio: {e}")
            
        return []
