# Alfredo OS - Contexto do Projeto

## Visão Geral

Alfredo OS é um assistente doméstico pessoal baseado em arquitetura Agentic.

O servidor central apenas orquestra as requisições.

Todo processamento pesado é executado em serviços externos.

O objetivo principal do projeto é oferecer uma experiência semelhante à Alexa ou Google Home utilizando hardware extremamente simples e custo operacional praticamente zero.

---

# Filosofia

Sempre preservar estes princípios.

- Agentic First
- Modular
- Stateless
- Extensível
- Fácil manutenção
- Baixa latência
- Custo mínimo

Nunca criar arquiteturas paralelas.

Nunca duplicar funcionalidades.

Sempre seguir os padrões existentes.

---

# Stack Principal

Backend

- Python 3.11+
- FastAPI
- SQLAlchemy
- SQLite
- WebSockets

IA

- Gemini 2.5 Flash
- Gemini Tool Calling
- Groq Whisper Large V3
- Edge TTS

Frontend

- React
- Vite

Hardware

- ESP32
- Satélites de voz
- Servidor Ubuntu

---

# Arquitetura

O sistema possui quatro camadas.

## 1 Servidor

Responsável por:

- API
- Router
- Banco
- Contexto
- Skills
- Dashboard

Não faz processamento pesado de IA.

---

## 2 Router

Arquivo principal

core/brain/router.py

Responsável por:

- interpretar requests
- chamar Gemini
- selecionar Skills
- montar contexto
- executar Tool Calling

Toda nova Skill deve ser registrada em:

self.skills

e também

_get_tools_schema()

---

## 3 Skills

Cada Skill representa uma Tool disponível para o Gemini.

Toda Skill implementa:

execute_tool(arguments, context)

Context disponível:

context["db"]

context["room_id"]

Nunca criar mecanismos paralelos.

---

## 4 Satélites

Os satélites são dispositivos burros.

Eles apenas:

- capturam áudio
- detectam wake word
- enviam áudio
- reproduzem resposta

Toda inteligência pertence ao servidor.

Nunca mover lógica de negócio para os satélites.

---

# Banco

Banco oficial:

SQLite

ORM:

SQLAlchemy

O banco é a única fonte da verdade.

Nunca utilizar estado global.

Estados persistentes ficam nas tabelas.

---

# Convenções

room_id

Sempre string.

Exemplos

ROOM_LIVING

ROOM_OFFICE

ROOM_BEDROOM

Nunca utilizar IDs numéricos.

---

# Tool Calling

Gemini utiliza apenas dicionários.

Nunca utilizar:

FunctionDeclaration

Formato esperado

name

description

parameters

required

Seguir exatamente o padrão existente.

---

# Assincronismo

Todo código do servidor deve ser assíncrono.

Sempre utilizar

async

await

Quando necessário utilizar

asyncio.to_thread()

Satélites standalone são exceção.

---

# Segurança

Nunca colocar

API Keys

Tokens

Senhas

URLs privadas

no código.

Sempre utilizar

os.getenv()

---

# Organização

Diretórios principais

core/

brain/

skills/

memory/

voice/

dashboard/

devices/

firmware/

tests/

config/

deploy/

scripts/

---

# Skills existentes

SmartHome

Timer

Music

YouTube

Weather

Traffic

Calendar

List

Memory

Recipe

Quiz

Dream

News

Time

Sempre reutilizar Skills existentes antes de criar novas.

---

# Calendário

Utiliza Google Calendar.

Possui sincronização bidirecional.

Possui OAuth.

Possui lembretes.

Possui reagendamento.

Possui detecção de conflitos.

Nunca criar outro sistema de agenda.

---

# Home Assistant

Toda automação passa pelo Home Assistant.

Nunca acessar dispositivos diretamente se existir integração HA.

---

# Dashboard

Dashboard em React.

Não quebrar compatibilidade entre backend e frontend.

Sempre preservar endpoints existentes.

---

# Estilo de Código

Preferir

- funções pequenas
- tipagem
- nomes claros
- baixo acoplamento
- poucas dependências

Nunca fazer refatorações grandes sem autorização.

---

# Antes de editar

Sempre ler o código existente.

Se a alteração for estrutural:

consultar

git log --oneline -- arquivo

Preservar correções antigas.

Nunca remover comportamentos existentes sem justificar.

---

# Antes de finalizar

Executar

python3 -m py_compile

Executar testes relacionados.

Criar teste mínimo quando necessário.

---

# Commits

Sempre Conventional Commits.

Exemplos

feat(router):

fix(calendar):

refactor(memory):

test(weather):

docs(readme):

Nunca utilizar mensagens genéricas.