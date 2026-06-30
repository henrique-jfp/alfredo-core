# Checklist de Onboarding de Cliente

Siga este checklist durante o setup inicial para garantir que o assistente Alfredo fique perfeitamente adaptado à casa do novo cliente.

## 1. Setup Físico e Rede
- [ ] Conectar Raspberry Pi 5 / Mini PC à rede via cabo Ethernet (se possível) ou configurar Wi-Fi.
- [ ] Fixar IP estático no roteador local para o servidor.
- [ ] Configurar Cloudflare Tunnel (ou similar) se acesso remoto seguro for contratado.

## 2. Instalação de Software (Servidor)
- [ ] Clonar repositório e rodar `./deploy/install.sh`.
- [ ] Preencher as variáveis interativas no script (`FAMILY_NAME`, `ADMIN_NAME`).

## 3. Configuração de Contas e APIs (.env)
- [ ] Coletar/Gerar Chave da API do **Groq**. Colar no `.env`.
- [ ] Coletar/Gerar Chave da API do **Gemini** (Google AI Studio). Colar no `.env`.
- [ ] Inserir coordenadas exatas da residência para precisão do clima (Open-Meteo).
- [ ] Gerar Token de Segurança para os satélites (`openssl rand -hex 32`). Colar em `SATELLITE_AUTH_TOKEN`.

## 4. Mapeamento de Cômodos e Satélites
- [ ] Definir os nomes lógicos de cada satélite e registrar no `.env` (Ex: `ROOM_ID_LIVING_ROOM=LIVING`).
- [ ] Para cada Satélite (ESP32-S3):
  - [ ] Compilar e dar flash do firmware baseando-se no Token e IP recém criados.
  - [ ] Validar a conexão Wi-Fi do satélite.
  - [ ] Instalar fisicamente no cômodo (garantir fonte USB adequada).

## 5. Testes Finais na Casa do Cliente
- [ ] Validar Wake-word no cômodo principal.
- [ ] Testar intenções locais ("Que horas são?", "Qual a previsão do tempo?").
- [ ] Testar IA de Fallback ("Explique buracos negros de forma simples").
- [ ] Ajustar volume físico do satélite se necessário.

## 6. Handover
- [ ] Explicar ao administrador (cliente) o que a IA pode e não pode fazer (Privacidade Local vs Fallback).
- [ ] Entregar acesso ao dashboard local (caso aplicável).
