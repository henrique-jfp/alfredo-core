import sys
import os

# Adiciona a raiz do projeto ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from core.brain.router import get_router

def test_router():
    print("========================================")
    print(" TESTE DE INTELIGÊNCIA ALFREDO (TEXTO)  ")
    print("========================================\n")
    
    router = get_router()
    
    while True:
        try:
            texto = input("\nVocê: ")
            if texto.lower() in ['sair', 'exit', 'quit']:
                break
                
            resposta = router.process(texto, context={})
            print(f"\nAlfredo: {resposta}")
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    test_router()
