"""
Anotador de capítulos via LLM (Gemini).

Recebe texto bruto de um capítulo e retorna uma lista de segmentos anotados
com efeitos sonoros e estilos de voz. O resultado é chamado UMA ÚNICA VEZ
por capítulo e persistido em BookChapter.annotation_json — nunca reprocessa.

Uso:
    from core.brain.reading.annotator import annotate_chapter
    segments = annotate_chapter("Ele caminhou até a porta. Um raio caiu.")
"""
import json
import logging
import re
from dataclasses import dataclass

logger = logging.getLogger("alfredo.reading.annotator")

# ── Vocabulário fechado ──────────────────────────────────────────────────────
# Esses são os ÚNICOS valores válidos. O prompt do LLM recebe essa lista,
# e qualquer valor fora dela é ignorado silenciosamente.

VALID_EFFECTS = frozenset({
    "thunder",        # Trovão distante
    "wind",           # Vento soprando
    "door_creak",     # Porta rangendo
    "footsteps",      # Passos
    "rain",           # Chuva
    "fire_crackle",   # Fogo crepitando
    "bell",           # Sino / campainha
    "suspense",       # Tom tenso de suspense
})

VALID_VOICE_STYLES = frozenset({
    "normal",         # Voz padrão, sem alteração
    "whisper",        # Sussurro: rate=-30%, volume=-40%, pitch=-5Hz
    "dramatic",       # Dramático: rate=-15%, pitch=+3Hz
    "fast",           # Rápido/urgente: rate=+25%
})


@dataclass
class Segment:
    """Um segmento anotado de texto com estilo de voz e efeito opcional."""
    text: str
    effect: str | None = None
    voice_style: str = "normal"


def annotate_chapter(chapter_text: str) -> list[Segment]:
    """Anota um capítulo inteiro via Gemini, retornando segmentos.

    Args:
        chapter_text: Texto bruto do capítulo.

    Returns:
        Lista de Segment com anotações de voz e efeitos.

    Raises:
        RuntimeError: Se não houver chave Gemini disponível ou a resposta
                      do LLM não puder ser parseada.
    """
    from core.services.key_manager import next_gemini_key, configure_genai, mark_gemini_cooldown
    import google.generativeai as genai

    # Trunca capítulos muito longos para caber no contexto do LLM
    max_chars = 15000
    if len(chapter_text) > max_chars:
        logger.warning(
            "Capítulo com %d chars excede %d — truncando para anotação",
            len(chapter_text), max_chars,
        )
        chapter_text = chapter_text[:max_chars]

    prompt = _build_annotation_prompt(chapter_text)

    # Tenta até 3 chaves diferentes em caso de rate limit
    last_error = None
    for attempt in range(3):
        key, key_num, total = next_gemini_key()
        if not key:
            raise RuntimeError("Nenhuma chave Gemini disponível para anotação de ebook")

        configure_genai(key)
        try:
            model = genai.GenerativeModel("gemini-3.1-flash-lite")
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.3,
                    response_mime_type="application/json",
                ),
            )
            raw = response.text.strip()
            segments = _parse_annotation_response(raw)
            logger.info(
                "Anotação concluída: %d segmentos (chave %d/%d, tentativa %d)",
                len(segments), key_num, total, attempt + 1,
            )
            return segments

        except Exception as e:
            last_error = e
            error_str = str(e)
            if "429" in error_str or "ResourceExhausted" in type(e).__name__:
                mark_gemini_cooldown(key, seconds=60)
                logger.warning("Rate limit na chave %d — tentando próxima", key_num)
            else:
                logger.error("Erro na anotação (tentativa %d): %s", attempt + 1, e)
                break

    raise RuntimeError(f"Falha na anotação após 3 tentativas: {last_error}")


def segments_to_json(segments: list[Segment]) -> str:
    """Serializa lista de segmentos para JSON string (para salvar no banco)."""
    return json.dumps(
        [{"text": s.text, "effect": s.effect, "voice_style": s.voice_style} for s in segments],
        ensure_ascii=False,
    )


def segments_from_json(json_str: str) -> list[Segment]:
    """Deserializa JSON string do banco para lista de Segment."""
    data = json.loads(json_str)
    segments = []
    for item in data:
        effect = item.get("effect")
        if effect and effect not in VALID_EFFECTS:
            effect = None
        voice_style = item.get("voice_style", "normal")
        if voice_style not in VALID_VOICE_STYLES:
            voice_style = "normal"
        segments.append(Segment(
            text=item["text"],
            effect=effect,
            voice_style=voice_style,
        ))
    return segments


# ── Prompt builder ───────────────────────────────────────────────────────────

def _build_annotation_prompt(chapter_text: str) -> str:
    effects_list = ", ".join(sorted(VALID_EFFECTS))
    styles_list = ", ".join(sorted(VALID_VOICE_STYLES))

    return f"""Você é um diretor de áudio criativo. Seu trabalho é anotar trechos de um livro
para uma narração imersiva com efeitos sonoros e variações de voz.

REGRAS ESTRITAS:
1. Divida o texto em segmentos naturais (frases ou grupos de 1-3 frases curtas).
2. Para cada segmento, atribua:
   - "text": o texto exato do trecho (sem alterar nenhuma palavra do original)
   - "effect": um efeito sonoro OU null. VALORES VÁLIDOS: {effects_list}
   - "voice_style": o estilo de narração. VALORES VÁLIDOS: {styles_list}
3. NÃO invente efeitos ou estilos fora das listas acima.
4. Use efeitos com MODERAÇÃO — no máximo 1 a cada 3-5 segmentos. A maioria dos
   segmentos deve ter effect=null e voice_style="normal".
5. Use "whisper" quando alguém sussurra ou fala baixo.
6. Use "dramatic" para momentos tensos, revelações, ou falas intensas.
7. Use "fast" para falas urgentes ou ação rápida.
8. O texto de TODOS os segmentos concatenados deve ser IDÊNTICO ao texto original.
   Não omita, adicione, nem altere nenhuma palavra.

Retorne APENAS um array JSON. Exemplo:
[
  {{"text": "Ele caminhou até a porta.", "effect": null, "voice_style": "normal"}},
  {{"text": "Um raio caiu perto da janela.", "effect": "thunder", "voice_style": "dramatic"}},
  {{"text": "\\"Silêncio\\", ela sussurrou.", "effect": null, "voice_style": "whisper"}}
]

TEXTO DO CAPÍTULO:
---
{chapter_text}
---

Retorne SOMENTE o array JSON, sem markdown, sem explicações."""


def _parse_annotation_response(raw_text: str) -> list[Segment]:
    """Parseia a resposta JSON do LLM em lista de Segment."""
    # Remove possíveis wrappers de markdown
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error("Falha ao parsear JSON da anotação: %s\nResposta bruta: %s", e, raw_text[:500])
        raise RuntimeError(f"Resposta do LLM não é JSON válido: {e}")

    if not isinstance(data, list):
        raise RuntimeError(f"Resposta do LLM não é uma lista: {type(data)}")

    segments: list[Segment] = []
    for item in data:
        if not isinstance(item, dict) or "text" not in item:
            continue

        text = item["text"].strip()
        if not text:
            continue

        effect = item.get("effect")
        if effect and effect not in VALID_EFFECTS:
            logger.debug("Efeito inválido '%s' ignorado", effect)
            effect = None

        voice_style = item.get("voice_style", "normal")
        if voice_style not in VALID_VOICE_STYLES:
            logger.debug("Estilo inválido '%s' ignorado, usando 'normal'", voice_style)
            voice_style = "normal"

        segments.append(Segment(text=text, effect=effect, voice_style=voice_style))

    if not segments:
        raise RuntimeError("Anotação retornou 0 segmentos válidos")

    logger.debug(
        "Parsed %d segmentos (%d com efeito, %d não-normal)",
        len(segments),
        sum(1 for s in segments if s.effect),
        sum(1 for s in segments if s.voice_style != "normal"),
    )
    return segments
