from typing import Dict, Any, Optional
from core.services.samsung_tv import SamsungTVManager
import asyncio
import concurrent.futures
import time


def _run_async(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)


# --------------------------------------------------------------------------- #
# Mapeamento de Canais da Claro TV
# --------------------------------------------------------------------------- #
CLARO_CHANNEL_MAP = {
    "globo": "501",
    "band hd": "505",
    "band": "505",
    "rede tv": "508",
    "redetv": "508",
    "sbt": "509",
    "cultura": "516",
    "record": "519",
    "polishop": "528",
    "like": "530",
    "tv brasil": "531",
    "claro recomenda": "532",
    "futura": "534",
    "off": "535",
    "sportv 3": "537",
    "sportv 2": "538",
    "sportv": "539",
    "globo news": "540",
    "globonews": "540",
    "gnt": "541",
    "multishow": "542",
    "viva": "543",
    "mais na tela": "544",
    "e": "550",
    "fashion tv": "551",
    "tlc": "552",
    "arte 1": "553",
    "food network": "554",
    "discovery home health": "555",
    "home health": "555",
    "curta": "556",
    "travel box brasil": "557",
    "fish tv": "558",
    "dogtv": "559",
    "hgtv": "560",
    "woohoo": "565",
    "espn extra": "569",
    "espn": "570",
    "espn 2": "571",
    "espn 3": "572",
    "espn 4": "573",
    "fox sports 2": "574",
    "band sports": "575",
    "jp news": "576",
    "cnn brasil": "577",
    "cnn": "577",
    "record news": "578",
    "band news": "579",
    "national geographic": "580",
    "natgeo": "580",
    "discovery": "581",
    "animal planet": "582",
    "history": "583",
    "the history channel": "583",
    "discovery turbo": "584",
    "discovery science": "585",
    "smithsonian": "590",
    "natgeo wild": "591",
    "discovery theater": "592",
    "discovery world": "593",
    "h2": "594",
    "gloobinho": "599",
    "discovery kids": "600",
    "gloob": "601",
    "disney channel": "602",
    "disney": "602",
    "nickelodeon": "603",
    "nick": "603",
    "cartoon network": "604",
    "cartoon": "604",
    "disney xd": "605",
    "disney jr": "606",
    "nick jr": "607",
    "cartoonito": "608",
    "tv ra tim bum": "609",
    "tooncast": "610",
    "baby tv": "611",
    "natgeo kids": "612",
    "zoo moo": "613",
    "bis": "620",
    "mtv": "621",
    "tv wa": "622",
    "playtv": "622",
    "music box brasil": "623",
    "trace brazuca": "624",
    "mtv 00": "625",
    "mezzo live": "626",
    "mtv live": "628",
    "universal": "630",
    "star channel": "631",
    "warner": "632",
    "sony": "633",
    "fx": "634",
    "axn": "635",
    "tbs": "636",
    "comedy central": "637",
    "ae": "638",
    "id": "639",
    "syfy": "640",
    "lifetime": "641",
    "tnt series": "643",
    "star life": "644",
    "amc": "645",
    "eurochannel": "647",
    "film arts": "648",
    "canal brasil": "650",
    "tnt": "651",
    "megapix": "652",
    "space": "654",
    "cinemax": "655",
    "prime box brazil": "656",
    "studio universal": "657",
    "paramount network": "658",
    "tcm": "659",
    "telecine premium": "661",
    "telecine action": "662",
    "telecine touch": "663",
    "telecine fun": "664",
    "telecine pipoca": "665",
    "telecine cult": "666",
    "hbo": "671",
    "hbo 2": "672",
    "hbo plus": "673",
    "hbo family": "675",
    "hbo signature": "676",
    "hbo pop": "677",
    "hbo mundi": "678",
    "hbo xtreme": "679",
    "netflix": "680",
    "star hits": "681",
    "star hits 2": "682",
    "agromais": "689",
    "cnn internacional": "700",
    "bloomberg": "701",
    "bbc world news": "702",
    "rai international": "703",
    "tv5 monde": "704",
    "tve internacional": "705",
    "dw tv": "706",
    "france 24": "710",
    "conmebol tv 1": "711",
    "conmebol tv 2": "712",
    "conmebol tv 3": "713",
    "conmebol tv 4": "714",
    "copa do nordeste 1": "715",
    "copa do nordeste 2": "716",
    "campeonato carioca 1": "717",
    "campeonato carioca 2": "718",
    "portal do futebol": "720",
    "premiere clubes": "721",
    "premiere 2": "722",
    "premiere 3": "723",
    "premiere 4": "724",
    "premiere 5": "725",
    "premiere 6": "726",
    "premiere 7": "727",
    "premiere 8": "728",
    "combate": "740",
    "playboy": "781",
    "sextreme": "782",
    "venus": "784",
    "sexy hot": "785",
    "globoplay": "831",
    "prime video": "832",
    "discovery plus": "834",
    "facebook watch": "837",
    "nordestefc": "838",
    "pluto tv": "845"
}

# --------------------------------------------------------------------------- #
# Mapeamentos que o semantic_router.py passou a exigir (select_source,
# channel_name, app_channel_change). Ajuste os valores abaixo conforme a
# sua TV/operadora real — os comentários indicam onde eu apenas chutei um
# valor plausível e onde eu deliberadamente deixei em branco.
# --------------------------------------------------------------------------- #

# Teclas Samsung/Tizen para fontes específicas. Esse conjunto de códigos é
# razoavelmente padrão em Smart TVs Samsung, mas VARIA por modelo/ano —
# teste e ajuste se algum não funcionar na sua TV.
SOURCE_KEY_MAP = {
    "hdmi1": "KEY_HDMI1",
    "hdmi2": "KEY_HDMI2",
    "hdmi3": "KEY_HDMI3",
    "av": "KEY_AV1",
    "antena": "KEY_TV",
    "tvaberta": "KEY_TV",
}

# Canais abertos (sintonizador nativo/antena) usados pela ação "channel_name".
# Números de exemplo para o Rio de Janeiro — CONFIRA no seu bairro/operadora,
# a numeração digital pode variar de cidade pra cidade.
ANTENNA_CHANNEL_MAP = {
    "globo": "4",
    "sbt": "5",
    "record": "7",
    "band": "13",
    "redetv": "9",
    "cultura": "2",
}

# Canais dentro do app Claro tv+ (ação "app_channel_change"). A numeração do
# Claro tv+ é própria da operadora/plano e varia por região — NÃO chutei
# valores aqui de propósito, pra não trocar pro canal errado silenciosamente.
# Preencha com os números reais do seu guia de canais Claro tv+.


# IDs de app fixos conhecidos (fallback: busca dinâmica na TV se não achar aqui)
KNOWN_APP_IDS = {
    "netflix": "11101200001",
    "youtube": "111299001912",
    "spotify": "3201606009684",
    "amazon prime": "3201512006785",
    "prime video": "3201512006785",
    "prime": "3201512006785",
    "globoplay": "3201603008210",
    "disney": "3201901017640",
    "hbo": "3201807016597",
    "apple tv": "3201807016597",
    "claro tv+": "3201910019378",
    "claro tv": "3201910019378",
    "claro": "3201910019378",
}


def _resolve_app_id(tv: SamsungTVManager, app_name: str) -> Optional[str]:
    """Resolve o app_id a partir do nome: primeiro no dicionário fixo,
    depois via busca dinâmica na lista de apps instalados na TV."""
    app_name_lower = app_name.lower()
    app_id = KNOWN_APP_IDS.get(app_name_lower)
    if app_id:
        return app_id

    installed_apps = _run_async(tv.get_app_list())
    if installed_apps and isinstance(installed_apps, dict) and "data" in installed_apps:
        for app in installed_apps["data"]:
            app_real_name = app.get("name", "").lower()
            if app_name_lower == app_real_name or app_name_lower in app_real_name:
                return app.get("appId")
    return None


def _open_app_by_name(tv: SamsungTVManager, app_name: str) -> bool:
    app_id = _resolve_app_id(tv, app_name)
    if app_id:
        _run_async(tv.open_app(app_id, app_name=app_name))
        return True
    return False


def _send_channel_digits(tv: SamsungTVManager, channel: Any) -> None:
    for digit in str(channel):
        _run_async(tv.send_key(f"KEY_{digit}"))
    time.sleep(0.5)
    _run_async(tv.send_key("KEY_ENTER"))


class TVSkill:
    def execute_tool(self, arguments: Dict[str, Any], context: Dict[str, Any]) -> str:
        # Suporta tanto o novo schema (actions) quanto o antigo (action único)
        actions = arguments.get("actions", [])
        if not actions and "action" in arguments:
            actions = [arguments]

        if not actions:
            return "Nenhuma ação fornecida para a TV."

        # Pega target_room do root ou do primeiro item
        target_room = arguments.get("target_room") or actions[0].get("target_room")

        db = context.get("db")
        room_id = context.get("room_id")

        if not db:
            return "Erro: banco de dados não disponível."

        from core.brain.memory import models
        from sqlalchemy import or_

        config = None

        # Se o usuário especificou um cômodo, procura por ele na descrição ou id
        if target_room:
            t_room = target_room.lower()
            if "sala" in t_room:
                config = db.query(models.TVConfig).filter(or_(models.TVConfig.room_id == "ROOM_SALA", models.TVConfig.room_id == "sala")).first()
            elif "quarto" in t_room:
                config = db.query(models.TVConfig).filter(or_(models.TVConfig.room_id == "ROOM_BEDROOM", models.TVConfig.room_id == "quarto")).first()
            elif "escritorio" in t_room or "escritório" in t_room:
                config = db.query(models.TVConfig).filter(or_(models.TVConfig.room_id == "ROOM_OFFICE", models.TVConfig.room_id == "escritorio")).first()
            else:
                config = db.query(models.TVConfig).filter(models.TVConfig.room_id.ilike(f"%{t_room}%")).first()

        # Se não especificou ou não achou com o nome, tenta o cômodo atual do satélite
        if not config and room_id:
            config = db.query(models.TVConfig).filter(models.TVConfig.room_id == room_id).first()

        # Fallback: Se não achou de nenhum jeito, pega a primeira TV que existir configurada
        if not config:
            config = db.query(models.TVConfig).filter(models.TVConfig.ip_address != None).first()

        if not config or not config.ip_address:
            return "Não encontrei nenhuma TV configurada na rede. Por favor, configure o IP da TV no painel de controle."

        tv = SamsungTVManager(
            ip=config.ip_address,
            mac=config.mac_address,
            smartthings_pat=config.smartthings_pat,
            smartthings_device_id=config.smartthings_device_id
        )

        # 1. Faz a checagem de status UMA ÚNICA VEZ antes do lote de ações
        tv_info = _run_async(tv.get_status())
        power_state = tv_info.get("device", {}).get("PowerState", "unknown")

        is_on = power_state == "on"
        is_offline = tv_info.get("status") == "offline"

        # avisos não-fatais (ex: canal não mapeado) — reportados no final,
        # sem interromper as outras ações do lote
        warnings = []

        # 2. Processa as ações em lote
        for idx, op in enumerate(actions):
            action = op.get("action")
            app_name = op.get("app_name")
            volume = op.get("volume")

            if action == "power_on":
                if not is_on:
                    powered_on_absolute = _run_async(tv.power_on())
                    if not powered_on_absolute and not is_offline:
                        _run_async(tv.send_key("KEY_POWER"))

                    is_on = True  # Assume que ligou com sucesso

                    # Se há mais comandos na fila (ex: abrir app) e a TV estava desligada,
                    # aguarda o Tizen iniciar a rede WebSocket
                    if idx < len(actions) - 1:
                        # Em TVs Samsung, a rede pode demorar até 10-15s após ligar.
                        for _ in range(15):
                            time.sleep(1)
                            # Tenta checar se já está online
                            check = _run_async(tv.get_status())
                            if check.get("status") != "offline":
                                time.sleep(2)  # Dá mais 2s pra estabilizar
                                break

            elif action == "power_off":
                if not is_offline and power_state != "standby":
                    _run_async(tv.power_off())
                    is_on = False

            elif action == "mute":
                _run_async(tv.set_mute(True))

            elif action == "unmute":
                _run_async(tv.set_mute(False))

            elif action == "volume_up":
                for _ in range(3):
                    _run_async(tv.send_key("KEY_VOLUP"))

            elif action == "volume_down":
                for _ in range(3):
                    _run_async(tv.send_key("KEY_VOLDOWN"))

            elif action == "set_volume" or action == "volume_set":
                vol = volume or op.get("level")
                if vol:
                    _run_async(tv.set_volume(int(vol)))

            elif action == "media_play":
                _run_async(tv.send_key("KEY_PLAY"))

            elif action == "media_pause":
                _run_async(tv.send_key("KEY_PAUSE"))

            elif action == "media_stop":
                _run_async(tv.send_key("KEY_STOP"))

            elif action == "media_next":
                _run_async(tv.send_key("KEY_FF"))

            elif action == "media_previous":
                _run_async(tv.send_key("KEY_REWIND"))

            elif action == "channel_number":
                channel = op.get("channel")
                if channel:
                    _send_channel_digits(tv, channel)

            elif action == "channel_name":
                # canal do sintonizador nativo (antena), pedido por nome
                # ("coloca o canal do globo")
                channel_name = op.get("channel_name")
                channel = ANTENNA_CHANNEL_MAP.get(channel_name) if channel_name else None
                if channel:
                    _send_channel_digits(tv, channel)
                else:
                    warnings.append(
                        f"Canal '{channel_name}' não está em ANTENNA_CHANNEL_MAP."
                    )

            elif action == "app_channel_change":
                # troca de canal DENTRO de um app (ex: Claro tv+), diferente
                # do sintonizador nativo. Garante que o app esteja aberto
                # antes de mandar os números do canal.
                target_app = app_name or "claro tv+"
                opened = _open_app_by_name(tv, target_app)
                if not opened:
                    warnings.append(f"Não encontrei o app '{target_app}' na TV.")
                else:
                    time.sleep(10)  # tempo pro app carregar antes de aceitar teclas

                channel = op.get("channel")
                if not channel:
                    channel_name = op.get("channel_name")
                    channel = CLARO_CHANNEL_MAP.get(channel_name) if channel_name else None
                    if channel_name and not channel:
                        warnings.append(
                            f"Canal '{channel_name}' não está em CLARO_CHANNEL_MAP "
                            f"(preencha com o número real do seu guia Claro tv+)."
                        )

                if channel:
                    _send_channel_digits(tv, channel)

            elif action == "select_source":
                source = (op.get("source") or "").replace(" ", "")
                key = SOURCE_KEY_MAP.get(source)
                if key:
                    _run_async(tv.send_key(key))
                else:
                    # sem tecla direta mapeada pra essa fonte: abre o menu
                    # de fontes e deixa a seleção final por conta do usuário
                    warnings.append(
                        f"Fonte '{source}' sem tecla direta mapeada; abri o menu de fontes."
                    )
                    _run_async(tv.send_key("KEY_SOURCE"))

            elif action == "open_app":
                if app_name and not _open_app_by_name(tv, app_name):
                    warnings.append(f"App '{app_name}' não encontrado na TV.")

        if warnings:
            return "Ok, mas com avisos: " + " ".join(warnings)
        return "Ok!"