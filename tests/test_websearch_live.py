"""Script para testar o WebSearchSkill no servidor."""
import sys
sys.path.insert(0, '/home/pvserver/alfredo-core')
from core.brain.skills.web_search_skill import WebSearchSkill

skill = WebSearchSkill()

# Teste 1: busca normal
result = skill.execute_tool({"query": "Brasilia capital do Brasil"}, {})
print("=== RESULTADO BUSCA ===")
print(result.get("direct_response", "")[:300])
print(f"Status: {result.get('status', 'unknown')}")

# Teste 2: query vazia
result2 = skill.execute_tool({"query": ""}, {})
print("\n=== QUERY VAZIA ===")
print(result2.get("direct_response", ""))

print("\n✅ Teste concluído!")
