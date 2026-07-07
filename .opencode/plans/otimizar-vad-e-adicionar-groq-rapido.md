# Plano: Acelerar Alfredo para ~2s (nível Alexa)

## Mudança 1: Reduzir VAD de 1.5s → 0.5s

**Arquivo:** `scripts/local_satellite.py`

### Linha 345

**Antes:**
```python
max_silence = int(1.5 * RATE / 160)
```

**Depois:**
```python
max_silence = int(0.5 * RATE / 160)
```

**Efeito:** O satélite espera 0.5s de silêncio (em vez de 1.5s) antes de considerar que você terminou de falar. Economia: **~1s por interação**.

---

## Mudança 2: Rota rápida com Groq para queries sem tool

**Arquivo:** `core/brain/router.py`

### Contexto

O Gemini 2.5 Flash tem TTFT (time to first token) de ~936ms (benchmark real). O Groq com Llama 3.1 8B tem TTFT de ~114ms. Para queries que **não precisam de ferramentas** (piadas, conversa, perguntas gerais), podemos usar Groq como rota expressa.

### 2a. Adicionar cliente Groq no __init__ do AgentRouter

**Após linha 34 (skills dict):**
```python
from groq import Groq as GroqClient
groq_key = os.getenv("GROQ_API_KEY")
self.groq_client = GroqClient(api_key=groq_key) if groq_key else None
```

**Import no topo do arquivo (linha 4-5):**
```python
from groq import Groq as GroqClient
```

### 2b. Método `_is_simple_query` para detectar queries sem tool

**Antes do método `process` (após `_get_tools_schema`):**
```python
def _is_simple_query(self, text: str) -> bool:
    """Retorna True se a query provavelmente não precisa de ferramentas."""
    simple_keywords = [
        "piada", "conte", "conta", "história", "historia",
        "fale", "diga", "o que você", "como você", "quem é",
        "obrigado", "brigado", "valeu", "tchau", "oi", "olá",
        "bom dia", "boa tarde", "boa noite", "e aí", "e ai",
    ]
    text_lower = text.lower().strip()
    if any(text_lower.startswith(kw) or text_lower == kw for kw in simple_keywords):
        return True
    return False
```

### 2c. Novo método `_process_fast` para rota Groq

```python
def _process_fast(self, text: str, context: Dict[str, Any]) -> str:
    """Rota expressa via Groq para queries simples (sem tool calling)."""
    if not self.groq_client:
        return None
    
    system = "Você é o Alfredo, assistente residencial amigável. Responda de forma natural e breve, no máximo 2 frases. NUNCA use emojis."
    
    db = context.get("db")
    room_id = context.get("room_id")
    if db and room_id:
        from core.brain.memory import models
        memory_facts = db.query(models.MemoryFact).filter(models.MemoryFact.room_id == room_id).all()
        if memory_facts:
            memories = "\n".join([f"- {m.fact}" for m in memory_facts])
            system += f"\n\nFatos sobre o usuário:\n{memories}"
    
    try:
        completion = self.groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": text}
            ],
            temperature=0.8,
            max_tokens=150
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"Groq fast path falhou: {e}")
        return None
```

### 2d. Modificar `process` para tentar rota rápida primeiro

**No início do método `process`, após configurar keys mas antes de chamar o Gemini:**

```python
# Fast path: Groq para queries simples sem ferramenta
if self._is_simple_query(text):
    fast_result = self._process_fast(text, context)
    if fast_result:
        logger.info(f"Rota rápida Groq: {fast_result[:50]}...")
        return fast_result
```

### 2e. Modificar `process_stream_async` similarmente

**No início do método, antes de criar o modelo Gemini:**
```python
# Fast path: Groq para queries simples
if self._is_simple_query(text):
    fast_result = self._process_fast(text, context)
    if fast_result:
        logger.info(f"Rota rápida Groq (stream): {fast_result[:50]}...")
        yield fast_result
        return
```

---

## Mudança 3: Adicionar `groq` como dependência (já existe)

O `groq` já está no `requirements.txt`. Só precisamos garantir que `GROQ_API_KEY` está configurada (e já está, pois é usada pelo STT).

---

## Resultado esperado após as 2 mudanças

| Cenário | Alexa | Antes | Depois |
|---|---|---|---|
| "Conta uma piada" (rota rápida Groq) | ~2s | ~4.5s | **~1.5-2.5s** |
| "Que horas são?" (tool direta) | ~1.5s | ~4s | **~2.5-3s** |
| "Adicionar pão na lista" (tool sem direct_response) | ~2s | ~6s | **~5s** |
| "Clima hoje?" (tool com direct_response) | ~1.5s | ~4.5s | **~3s** |

**Ganho principal:** Queries que não usam ferramentas (piadas, conversa, perguntas) caem de ~4.5s para ~2s — **nível Alexa**.

---

## Instruções de aplicação

1. Editar `scripts/local_satellite.py`: mudar `1.5` para `0.5` na linha 345
2. Editar `core/brain/router.py`: adicionar rota Groq + método `_is_simple_query` + `_process_fast`
3. Reiniciar o servidor
