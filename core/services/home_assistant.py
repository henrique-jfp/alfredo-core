"""
Gerenciador de integração com Home Assistant.
Segue o mesmo padrão de SamsungTVManager em core/services/samsung_tv.py:
chamadas REST síncronas encapsuladas em métodos nomeados, com timeout curto (5s).
As credenciais (URL + token) vêm de variáveis de ambiente (HOME_ASSISTANT_URL,
HOME_ASSISTANT_TOKEN), carregadas via config/.env.

Uso típico:
    ha = HomeAssistantManager()
    ha.turn_on("light.luz_sala_1")
    ha.set_brightness("light.luz_sala_1", 80)
    ha.turn_off("fan.ventilador_quarto")
"""
import os
import logging
import requests

logger = logging.getLogger("alfredo.home_assistant")

# Carregados uma vez no módulo — podem ser sobrescritos via setter ou .env
_HOME_ASSISTANT_URL = os.getenv("HOME_ASSISTANT_URL", "").rstrip("/")
_HOME_ASSISTANT_TOKEN = os.getenv("HOME_ASSISTANT_TOKEN", "")


class HomeAssistantManager:
    """Gerencia chamadas REST à API do Home Assistant.

    As credenciais (url + token) são lidas de variáveis de ambiente na primeira
    importação do módulo, mas podem ser injetadas via construtor para testes ou
    override programático.
    """

    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
    ):
        self.base_url = (base_url or _HOME_ASSISTANT_URL).rstrip("/")
        self.token = token or _HOME_ASSISTANT_TOKEN
        self._headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        if not self.base_url:
            logger.warning(
                "HOME_ASSISTANT_URL não configurada. As chamadas REST falharão."
            )
        if not self.token:
            logger.warning(
                "HOME_ASSISTANT_TOKEN não configurado. As chamadas REST falharão."
            )

    # ── helpers internos ──────────────────────────────────────────────

    def _request(self, method: str, path: str, json_body: dict | None = None):
        """Executa uma requisição REST síncrona com timeout de 5s."""
        url = f"{self.base_url}{path}"
        try:
            resp = requests.request(
                method=method,
                url=url,
                headers=self._headers,
                json=json_body,
                timeout=5,
            )
            resp.raise_for_status()
            return resp.json() if resp.text else {}
        except requests.Timeout:
            logger.error(f"Timeout ao acessar Home Assistant: {method} {path}")
            raise
        except requests.RequestException as e:
            logger.error(f"Erro na requisição Home Assistant ({method} {path}): {e}")
            raise

    def _call_service(self, domain: str, service: str, entity_id: str, **extra):
        """Invoca um serviço do Home Assistant via
        POST /api/services/<domain>/<service>."""
        body = {"entity_id": entity_id, **extra}
        return self._request("POST", f"/api/services/{domain}/{service}", json_body=body)

    def _get_state(self, entity_id: str) -> dict | None:
        """Obtém o estado atual de uma entidade via
        GET /api/states/<entity_id>."""
        try:
            return self._request("GET", f"/api/states/{entity_id}")
        except requests.RequestException:
            return None

    # ── ações públicas ────────────────────────────────────────────────

    def turn_on(self, entity_id: str, brightness: int | None = None):
        """Liga um dispositivo. Opcionalmente define brightness (0-255) para luzes."""
        domain = entity_id.split(".")[0]
        kwargs = {}
        if brightness is not None and domain == "light":
            kwargs["brightness"] = max(0, min(255, brightness))
        logger.info(f"Ligando {entity_id} (brightness={kwargs.get('brightness')})")
        return self._call_service(domain, "turn_on", entity_id, **kwargs)

    def turn_off(self, entity_id: str):
        """Desliga um dispositivo."""
        domain = entity_id.split(".")[0]
        logger.info(f"Desligando {entity_id}")
        return self._call_service(domain, "turn_off", entity_id)

    def toggle(self, entity_id: str):
        """Alterna o estado de um dispositivo (liga se desligado, vice-versa)."""
        domain = entity_id.split(".")[0]
        logger.info(f"Alternando {entity_id}")
        return self._call_service(domain, "toggle", entity_id)

    def set_brightness(self, entity_id: str, brightness: int):
        """Define o brilho de uma luz (0-255)."""
        domain = entity_id.split(".")[0]
        b = max(0, min(255, brightness))
        logger.info(f"Definindo brilho de {entity_id} para {b}")
        if domain == "light":
            return self._call_service(domain, "turn_on", entity_id, brightness=b)
        raise ValueError(f"set_brightness não suportado para domínio '{domain}'")

    def set_speed(self, entity_id: str, speed: str):
        """Define a velocidade de um ventilador. Valores comuns:
        'off', 'low', 'medium', 'high'."""
        domain = entity_id.split(".")[0]
        logger.info(f"Definindo velocidade de {entity_id} para '{speed}'")
        if domain == "fan":
            return self._call_service(domain, "set_speed", entity_id, speed=speed)
        raise ValueError(f"set_speed não suportado para domínio '{domain}'")

    def is_connected(self) -> bool:
        """Verifica se o Home Assistant está acessível (GET /api/)."""
        if not self.base_url:
            return False
        try:
            resp = requests.get(
                f"{self.base_url}/api/",
                headers=self._headers,
                timeout=5,
            )
            return resp.status_code == 200
        except requests.RequestException:
            return False
