# Plano: Otimizar latência, TTS e criatividade do Alfredo

## 1. Router: corrigir model_name e aumentar criatividade

**Arquivo:** `core/brain/router.py`

### 1a. Modelo síncrono (`process`) — linha ~272

**Antes:**
```python
model = genai.GenerativeModel(
    model_name='gemini-3.5-flash',
    tools=tools,
    system_instruction=system_prompt,
    generation_config=genai.GenerationConfig(temperature=0.8)
)
```

**Depois:**
```python
model = genai.GenerativeModel(
    model_name='gemini-2.5-flash',
    tools=tools,
    system_instruction=system_prompt,
    generation_config=genai.GenerationConfig(temperature=0.9)
)
```

**Mudanças:** `gemini-3.5-flash` → `gemini-2.5-flash` (modelo real e rápido), temperature 0.8 → 0.9 (mais criatividade)

### 1b. Modelo streaming (`process_stream_async`) — linha ~465

**Antes:**
```python
model = genai.GenerativeModel(
    model_name='gemini-3.5-flash',
    system_instruction=system_prompt,
    tools=tools,
    generation_config=genai.GenerationConfig(temperature=0.8)
)
```

**Depois:**
```python
model = genai.GenerativeModel(
    model_name='gemini-2.5-flash',
    system_instruction=system_prompt,
    tools=tools,
    generation_config=genai.GenerationConfig(temperature=0.9)
)
```

### 1c. System Prompt — linhas ~247-258

**Antes:**
```python
system_prompt = (
    "Você é o Alfredo, um assistente virtual ultra avançado para automação residencial. "
    "Responda sempre de forma natural, amigável e conversacional. Seja breve, no máximo 2 frases. "
    "NUNCA utilize emojis ou símbolos complexos nas suas respostas. "
    "Se o usuário pedir para traduzir algo para outro idioma, ..."
    "REGRA DO QUIZ: ..."
    "REGRA DA RECEITA: ..."
)
```

**Depois:**
```python
system_prompt = (
    "Você é o Alfredo, um assistente virtual ultra avançado para automação residencial. "
    "Responda sempre de forma natural, amigável e conversacional. "
    "Seja direto e breve em respostas utilitárias (horas, clima, timers). "
    "Em respostas criativas (piadas, histórias, conversas), pode se estender um pouco, "
    "mas sempre com ritmo e sem enrolação. "
    "NUNCA repita a mesma piada, história ou resposta criativa. Sempre traga algo novo e surpreendente. "
    "NUNCA utilize emojis ou símbolos complexos nas suas respostas. "
    "Se o usuário pedir para traduzir algo para outro idioma, ..."
    "REGRA DO QUIZ: ..."
    "REGRA DA RECEITA: ..."
)
```

---

## 2. TTS: acelerar velocidade da fala

**Arquivo:** `core/voice/tts/engine.py`

### 2a. `synthesize_wav` — linha 77

**Antes:**
```python
communicate = edge_tts.Communicate(segment_text, voice)
```

**Depois:**
```python
communicate = edge_tts.Communicate(segment_text, voice, rate='+25%')
```

### 2b. `stream_audio_generator` — linha 176

**Antes:**
```python
communicate = edge_tts.Communicate(segment_text, voice)
```

**Depois:**
```python
communicate = edge_tts.Communicate(segment_text, voice, rate='+25%')
```

### 2c. `stream_audio_from_generator` — linha 226

**Antes:**
```python
communicate = edge_tts.Communicate(segment_text, voice)
```

**Depois:**
```python
communicate = edge_tts.Communicate(segment_text, voice, rate='+25%')
```

---

## 3. Instruções de aplicação

1. Editar `core/brain/router.py`:
   - Trocar `model_name='gemini-3.5-flash'` por `model_name='gemini-2.5-flash'` (2 ocorrências)
   - Trocar `temperature=0.8` por `temperature=0.9` (2 ocorrências)
   - Substituir o system prompt conforme seção 1c acima

2. Editar `core/voice/tts/engine.py`:
   - Adicionar `, rate='+25%'` em todos os 3 `edge_tts.Communicate()` (linhas 77, 176, 226)

3. Reiniciar o servidor: `bash restart.sh`

---

## Resultado esperado

| Métrica | Antes | Depois |
|---|---|---|
| Latência total (com tool) | ~8s | ~2-4s |
| Velocidade da fala | arrastada (soletrando) | natural e rápida |
| Variedade de respostas | mesmas piadas sempre | respostas novas e criativas |
