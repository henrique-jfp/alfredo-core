import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the parent directory to sys.path so we can import core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.brain.memory.models import Device

def clean_ghosts():
    DB_PATH = os.path.join(os.getcwd(), 'alfredo_memory.db')
    if not os.path.exists(DB_PATH):
        print(f"Banco de dados não encontrado em {DB_PATH}.")
        print("Por favor, rode este script a partir da pasta raiz do alfredo-core ONDE O SERVIDOR PRINCIPAL ESTÁ RODANDO.")
        sys.exit(1)

    print(f"Conectando ao banco de dados: {DB_PATH}")
    engine = create_engine(f'sqlite:///{DB_PATH}')
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        devices = db.query(Device).all()
        deleted = 0
        for d in devices:
            # Manter apenas os que sabemos que são reais:
            # linux-server-satellite (Servidor) e SAT_BEDROOM (M21s Atual)
            if d.device_id not in ['linux-server-satellite', 'SAT_BEDROOM']:
                print(f"Deletando satélite fantasma: {d.device_id} (Sala: {d.room_id})")
                db.delete(d)
                deleted += 1

        if deleted > 0:
            db.commit()
            print(f"\nSucesso! {deleted} satélites fantasmas foram apagados permanentemente.")
        else:
            print("\nNenhum satélite fantasma encontrado. O banco de dados já está limpo.")
            
    except Exception as e:
        print(f"Erro ao acessar o banco de dados: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    clean_ghosts()
