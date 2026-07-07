import asyncio
import os
import sys

# Corrige import path para rodar direto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.brain.router import AgentRouter
import core.database.database as db_module

def test_llm():
    try:
        db = next(db_module.get_db())
        router = AgentRouter()
        res = router.process_text('Oi Alfredo, me conte uma piada.', [], db, 'ROOM_LIVING')
        print('RESPOSTA LLM:', res)
    except Exception as e:
        print('ERRO:', e)

if __name__ == '__main__':
    test_llm()
