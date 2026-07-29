"""
WebSearchSkill — Pesquisa na web usando DuckDuckGo (gratuito, sem API key).

Permite que o Gemini responda perguntas factuais em tempo real:
  - "Onde assistir o jogo do Fluminense hoje?"
  - "Qual o valor do dólar?"
  - "Pesquise sobre fotossíntese"
  - "Quem ganhou a eleição?"

Usa a biblioteca duckduckgo_search (pip install duckduckgo_search).
Fallback para requisição HTTP direta se a biblioteca não estiver disponível.
"""

import logging
import re
import warnings
from typing import Dict, Any, Optional, List, Tuple
from core.brain.skills.base import Skill

logger = logging.getLogger("alfredo.skills.web_search")

# Cache simples: evita pesquisar a mesma coisa repetidas vezes
_SEARCH_CACHE: Dict[str, Tuple[float, str]] = {}
CACHE_TTL = 120  # 2 minutos


class WebSearchSkill(Skill):
    @property
    def name(self) -> str:
        return "WebSearchSkill"

    def can_handle(self, intent: str, text: str) -> bool:
        return intent == "WEB_SEARCH"

    # ------------------------------------------------------------------
    # Mecanismos de busca (tentativa: duckduckgo_search → fallback HTTP)
    # ------------------------------------------------------------------
    def _search_duckduckgo(self, query: str, max_results: int = 5) -> Optional[str]:
        """Tenta buscar usando a biblioteca duckduckgo_search (instalação opcional)."""
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message=".*renamed to.*")
                from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
            if not results:
                return None

            lines = []
            for r in results:
                title = r.get("title", "").strip()
                snippet = r.get("body", "").strip()
                if title and snippet:
                    lines.append(f"{title}: {snippet}")
                elif snippet:
                    lines.append(snippet)
            return " | ".join(lines[:max_results]) if lines else None
        except ImportError:
            logger.info("duckduckgo_search não instalado — tentando fallback HTTP")
            return None
        except Exception as e:
            logger.warning("Erro no duckduckgo_search: %s", e)
            return None

    def _search_http_fallback(self, query: str, max_results: int = 5) -> Optional[str]:
        """Fallback: busca via HTML scraping do DuckDuckGo (sem API key)."""
        import urllib.parse
        import urllib.request
        import json

        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as resp:
                html = resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            logger.warning("Fallback HTTP falhou: %s", e)
            return None

        # Extrai resultados do HTML (links com classe "result__a" e snippets "result__snippet")
        snippets = []
        # Padrão: <a class="result__a" ...>TÍTULO</a>
        for match in re.finditer(
            r'<a[^>]*class="result__a"[^>]*>(.*?)</a>',
            html, re.IGNORECASE
        ):
            title = re.sub(r"<[^>]+>", "", match.group(1)).strip()
            # Pula resultados de navegação interna do DuckDuckGo
            if not title or "duckduckgo" in title.lower():
                continue

            # Pega o snippet seguinte (classe result__snippet)
            after = html[match.end():]
            snippet_match = re.search(
                r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
                after, re.IGNORECASE
            )
            snippet = ""
            if snippet_match:
                snippet = re.sub(r"<[^>]+>", "", snippet_match.group(1)).strip()

            if title:
                parts = title
                if snippet:
                    parts += ": " + snippet
                snippets.append(parts)

            if len(snippets) >= max_results:
                break

        return " | ".join(snippets) if snippets else None

    def _search(self, query: str, max_results: int = 5) -> Optional[str]:
        """Tenta duckduckgo_search primeiro, depois fallback HTTP."""
        result = self._search_duckduckgo(query, max_results)
        if result:
            return result
        return self._search_http_fallback(query, max_results)

    # ------------------------------------------------------------------
    # Execução
    # ------------------------------------------------------------------
    def _get_cached_or_search(self, query: str) -> str:
        """Retorna resultado do cache (se válido) ou faz nova busca."""
        now = __import__("time").time()
        cached = _SEARCH_CACHE.get(query)
        if cached and (now - cached[0]) < CACHE_TTL:
            logger.info("Usando cache de busca para: '%s'", query[:60])
            return cached[1]

        result = self._search(query)
        if result:
            _SEARCH_CACHE[query] = (now, result)
            return result
        return ""

    def execute(self, text: str, context: Dict[str, Any]) -> str:
        """Método legado — não usado pelo fluxo Gemini; mantido para compatibilidade."""
        return "Use o execute_tool para buscas na web."

    def _enrich_query_with_date(self, query: str) -> str:
        """
        Enriquece a query com a data atual se mencionar 'hoje', 'amanhã', etc.
        Exemplo: "jogo do Fluminense hoje" → "jogo do Fluminense 26/07/2026"
        """
        from datetime import datetime, timedelta
        now = datetime.now()
        today_str = now.strftime("%d/%m/%Y")
        tomorrow_str = (now + timedelta(days=1)).strftime("%d/%m/%Y")
        yesterday_str = (now - timedelta(days=1)).strftime("%d/%m/%Y")

        # Substitui referências temporais por datas reais
        enriched = query
        # "hoje" → data de hoje (se for referência temporal, não "hoje" em outro contexto)
        enriched = re.sub(r'\bhoje\b', today_str, enriched, flags=re.IGNORECASE)
        enriched = re.sub(r'\bamanh[ãa]\b', tomorrow_str, enriched, flags=re.IGNORECASE)
        enriched = re.sub(r'\bontem\b', yesterday_str, enriched, flags=re.IGNORECASE)

        # Se a query original tinha "hoje" e foi substituída, mantém a original
        # mas adiciona a data para contexto
        if enriched != query:
            logger.info("Query enriquecida com data: '%s' → '%s'", query, enriched)
        return enriched

    def execute_tool(self, kwargs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executa uma busca na web.

        Espera do Gemini:
          - query (string, obrigatório): a pergunta/pesquisa do usuário

        Retorna:
          - direct_response: texto com resultados (ou erro amigável)
          - query: a query original usada
          - enriched_query: a query com data (se alterada)
          - status: "success" ou "no_results"
        """
        query = kwargs.get("query", "").strip()
        if not query:
            return {
                "direct_response": "Não entendi o que você quer pesquisar. Pode repetir?",
                "error": "query vazia"
            }

        # Enriquece query com data atual para buscas mais precisas
        search_query = self._enrich_query_with_date(query)

        logger.info("Pesquisando na web: '%s'", search_query)
        result_text = self._get_cached_or_search(search_query)

        if result_text:
            from datetime import datetime
            now = datetime.now()
            # Adiciona data atual no resultado para o Gemini saber o contexto temporal
            result_text = f"[Data atual: {now.strftime('%d/%m/%Y %H:%M')}] {result_text}"
            # Retorna SEM direct_response para que o Gemini receba o resultado
            # como function_response e produza uma resposta NATURAL em vez de
            # apenas ler o resultado bruto da busca em voz alta.
            return {
                "search_results": result_text,
                "query": query,
                "enriched_query": search_query if search_query != query else None,
                "status": "success"
            }

        # Se não achou nada, retorna um aviso — o Gemini pode tentar responder do conhecimento interno
        return {
            "direct_response": f"Não encontrei resultados para '{query}'. Use seu conhecimento geral para responder.",
            "query": query,
            "enriched_query": search_query if search_query != query else None,
            "status": "no_results"
        }
