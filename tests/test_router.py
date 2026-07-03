import os
import asyncio
from dotenv import load_dotenv
load_dotenv()
from core.brain.router import get_router
from core.brain.memory.database import SessionLocal
from core.brain.memory import models

def run_tests():
    router = get_router()
    db = SessionLocal()
    
    # Vamos usar um device e room fictícios para o teste
    test_device = "TEST_DEVICE"
    test_room = "TEST_ROOM"
    
    context = {
        "device_id": test_device,
        "room_id": test_room,
        "db": db,
        "ws_tasks": []
    }
    
    print("Iniciando bateria de testes do Cérebro Alfredo (Gemini 2.5 Flash)...\n")
    
    interacoes = [
        "Que horas são?",
        "Crie uma lista de compras e adicione bananas nela.",
        "Adicione maçãs também, por favor.", # Teste de contexto!
        "Qual é a previsão do tempo para São Paulo hoje?",
        "E para amanhã?", # Teste de contexto 2!
        "Me lembre de tirar o lixo daqui a 1 minuto.",
        "Lê a minha lista de compras."
    ]
    
    for msg in interacoes:
        print(f"👤 Usuário: {msg}")
        
        # O histórico real precisa estar no BD para o contexto funcionar
        # O painel faria isso, então vamos injetar no BD
        interaction = models.Interaction(
            device_id=test_device,
            room_id=test_room,
            input_text=msg,
            output_text=None
        )
        db.add(interaction)
        db.commit()
        
        # Processa
        try:
            resposta = router.process(msg, context)
            
            # Atualiza o output
            interaction.output_text = resposta
            db.commit()
            
            print(f"🤖 Alfredo: {resposta}\n")
        except Exception as e:
            print(f"❌ Erro ao processar: {e}\n")

if __name__ == "__main__":
    run_tests()
