# Guia de Instalação do Servidor Alfredo

Este documento descreve como instalar e provisionar um novo servidor central do Alfredo (ex: Raspberry Pi 5 ou Mini PC Ubuntu) do zero, para um novo cliente/família.

## Pré-requisitos
- Sistema Operacional Linux baseado em Debian/Ubuntu (Ubuntu Server 24.04 recomendado).
- Acesso à internet para download de pacotes e modelos.
- Chaves de API do Groq e Gemini (gratuitas).

## Passos para Instalação

1. **Clonar o Repositório:**
   Acesse a máquina de destino via SSH e clone este repositório no diretório home:
   ```bash
   git clone https://github.com/SEU_USER/alfredo-core.git
   cd alfredo-core
   ```

2. **Executar o Script Automático:**
   Dê permissão de execução e rode o script de instalação.
   ```bash
   chmod +x deploy/install.sh
   ./deploy/install.sh
   ```
   O script irá:
   - Instalar dependências de sistema (Python3, pip, venv).
   - Criar o ambiente virtual e instalar as bibliotecas (`requirements.txt`).
   - Baixar os modelos offline de STT (Vosk) e TTS (Piper).
   - Iniciar o prompt interativo para o arquivo `.env`.
   - Registrar o serviço do Alfredo no `systemd`.

3. **Configuração Fina (.env):**
   Abra o arquivo `config/.env` e preencha as variáveis que faltam (cidade, chaves de API, token do satélite). NENHUMA variável de ambiente deve ficar vazia se o serviço depender dela.
   ```bash
   nano config/.env
   ```

4. **Iniciando o Sistema:**
   Após configurar o `.env`, inicie o serviço:
   ```bash
   sudo systemctl start alfredo.service
   ```

5. **Verificação de Sanidade:**
   Cheque os logs para garantir que a API subiu na porta 10001 sem erros.
   ```bash
   sudo journalctl -u alfredo.service -f
   ```

> **Nota para Atualizações:** Sempre que houver nova versão, basta executar `./deploy/update.sh` para puxar o código do git, atualizar dependências e reiniciar o serviço.
