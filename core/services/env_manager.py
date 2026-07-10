import os
import re
import logging

logger = logging.getLogger("alfredo.env")

ENV_PATH = os.path.join(os.getcwd(), ".env")


def get_env_path() -> str:
    return ENV_PATH


def set_env_var(key: str, value: str) -> bool:
    """Atualiza ou adiciona uma variável no .env e no os.environ."""
    if not os.path.exists(ENV_PATH):
        logger.error(f"Arquivo .env não encontrado em {ENV_PATH}")
        return False

    try:
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        logger.error(f"Erro ao ler .env: {e}")
        return False

    key_upper = key.upper()
    pattern = re.compile(rf'^{re.escape(key_upper)}\s*=\s*.*', re.IGNORECASE)
    found = False
    new_lines = []

    for line in lines:
        if pattern.match(line.strip()):
            new_lines.append(f"{key_upper}={value}\n")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"\n{key_upper}={value}\n")

    try:
        with open(ENV_PATH, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    except Exception as e:
        logger.error(f"Erro ao escrever .env: {e}")
        return False

    # Atualiza environment da sessão atual
    os.environ[key_upper] = value
    logger.info(f"Variável {key_upper} atualizada no .env")
    return True


def get_env_var(key: str, default: str = "") -> str:
    """Lê variável do .env (ou os.environ como fallback)."""
    return os.getenv(key, default)


def sync_env_to_db():
    """Lê variáveis do .env e retorna dict para ser salvo no DB."""
    return {
        "SPOTIFY_CLIENT_ID": os.getenv("SPOTIFY_CLIENT_ID", ""),
        "SPOTIFY_CLIENT_SECRET": os.getenv("SPOTIFY_CLIENT_SECRET", ""),
        "GOOGLE_CLIENT_ID": os.getenv("GOOGLE_CLIENT_ID", ""),
        "GOOGLE_CLIENT_SECRET": os.getenv("GOOGLE_CLIENT_SECRET", ""),
        "PUBLIC_URL": os.getenv("PUBLIC_URL", ""),
    }
