import os
import json
import math
import logging
from typing import List, Optional

from core.services.key_manager import next_gemini_key, configure_genai

logger = logging.getLogger("alfredo.embedding")

def get_embedding(text: str) -> Optional[List[float]]:
    """Gera um embedding (vetor) para o texto fornecido usando o Gemini."""
    current_key, selected_key_number, total_keys = next_gemini_key()
    if not current_key:
        logger.error("Nenhuma chave Gemini disponível para gerar embedding.")
        return None

    try:
        # Pool persistente: só reconfigura se a chave mudou
        configure_genai(current_key)
        import google.generativeai as genai
        # Usando text-embedding-004 que é otimizado e mais barato/rápido
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="RETRIEVAL_DOCUMENT"
        )
        return result['embedding']
    except Exception as e:
        logger.error(f"Erro ao gerar embedding para o texto '{text}': {e}")
        return None

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calcula a similaridade do cosseno entre dois vetores."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm_a = math.sqrt(sum(a * a for a in vec1))
    norm_b = math.sqrt(sum(b * b for b in vec2))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return dot_product / (norm_a * norm_b)
