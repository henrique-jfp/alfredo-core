import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import QueuePool

# Configuração simples e robusta para SQLite local (arquivo armazenado na raiz)
DB_PATH = os.path.join(os.getcwd(), "alfredo_memory.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# ── Otimizações de latência para SQLite ─────────────────────────────────────
# QueuePool: cria conexões sob demanda em vez de reutilizar uma única.
# StaticPool causava crashes de concorrência (thread pool do asyncio +
# asyncio.to_thread acessando a mesma conexão simultaneamente).
# check_same_thread=False: necessário para FastAPI multi-thread + SQLite.
# pool_pre_ping: verifica se a conexão ainda está viva antes de usar.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=QueuePool,
    pool_size=2,
    max_overflow=2,
    pool_pre_ping=True,
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
    cursor.execute("PRAGMA busy_timeout=5000")    # 5s timeout se DB ocupado
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
