import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Configuração simples e robusta para SQLite local (arquivo armazenado na raiz)
DB_PATH = os.path.join(os.getcwd(), "alfredo_memory.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# check_same_thread=False é necessário para FastAPI + SQLite
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependência do FastAPI para injetar o DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
