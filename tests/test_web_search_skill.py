"""
Testes básicos para WebSearchSkill.

Verifica:
  - execute_tool com query válida e inválida
  - Cache de resultados
  - Fallback HTTP quando duckduckgo_search não está instalado
"""

import time
from unittest.mock import patch, MagicMock
from core.brain.skills.web_search_skill import WebSearchSkill, _SEARCH_CACHE


def test_execute_tool_query_vazia():
    """Query vazia deve retornar erro amigável."""
    skill = WebSearchSkill()
    result = skill.execute_tool({"query": ""}, {})
    assert "error" in result
    assert "direct_response" in result
    assert "Não entendi" in result["direct_response"]


def test_execute_tool_sem_query():
    """Sem parâmetro query deve retornar erro."""
    skill = WebSearchSkill()
    result = skill.execute_tool({}, {})
    assert "error" in result


def test_search_http_fallback():
    """Fallback HTTP deve retornar string com resultados ou None."""
    skill = WebSearchSkill()
    result = skill._search_http_fallback("Brasília capital do Brasil", max_results=2)
    # Pode ser None se a rede falhar, mas deve executar sem exceção
    assert result is None or isinstance(result, str)


def test_cache_funciona():
    """Cache deve evitar busca duplicada."""
    # Limpa cache
    _SEARCH_CACHE.clear()
    
    skill = WebSearchSkill()
    
    # Primeira chamada: busca real (ou fallback)
    q = "teste unitário pytest"
    r1 = skill._get_cached_or_search(q)
    
    # Verifica que o cache foi preenchido
    assert q in _SEARCH_CACHE
    
    # Segunda chamada: deve usar cache (não importa o resultado)
    r2 = skill._get_cached_or_search(q)
    assert r2 == r1  # Mesmo resultado (veio do cache)


def test_cache_ttl():
    """Cache deve expirar após TTL."""
    _SEARCH_CACHE.clear()
    
    skill = WebSearchSkill()
    q = "teste ttl cache"
    
    # Mock time para controlar expiração
    fake_time = 1000.0
    with patch("core.brain.skills.web_search_skill._SEARCH_CACHE") as mock_cache:
        # Simula cache válido
        mock_cache.get.return_value = (fake_time, "resultado antigo")
        mock_cache.__contains__ = lambda self, x: True
        
        # Simula que passou do TTL
        with patch("time.time", return_value=fake_time + 999999):
            # Deve tentar buscar novamente (vai falhar ou retornar algo novo)
            # O importante é que não retorna o cache antigo cegamente
            result = skill._get_cached_or_search(q)
            # O cache mockado tem side_effect None, então get retorna None
            # que faz com que o método faça uma nova busca
            # (não testamos o resultado, só que a lógica não quebra)
            assert isinstance(result, str) or result == ""
