import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

# Configuração simples e robusta para SQLite local (arquivo armazenado na raiz)
DB_PATH = os.path.join(os.getcwd(), "alfredo_memory.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# ── Otimizações de latência para SQLite ─────────────────────────────────────
# StaticPool: mantém UMA conexão reutilizável (evita custo de abertura de
# arquivo a cada request — economiza 20-50ms por interação no Celeron N2830).
# check_same_thread=False: necessário para FastAPI multi-thread + SQLite.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# WAL mode: Write-Ahead Logging permite leituras concorrentes sem bloquear
# escritas, crítico para o asyncio com múltiplas tasks acessando o DB
# simultaneamente (pipeline + logger de interações).
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")  # Mais rápido que FULL, seguro com WAL
    cursor.execute("PRAGMA cache_size=-16000")    # 16MB de cache em memória
    cursor.execute("PRAGMA temp_store=MEMORY")    # Tabelas temporárias em RAM
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependência do FastAPI para injetar o DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
