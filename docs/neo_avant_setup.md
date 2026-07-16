# 📦 Guia de Instalação — Lâmpadas Neo Avant + Alfredo OS

**Controle 100% local, sem nuvem, sem depender de internet.**

> **Tempo estimado:** ~2h (fazendo com calma)
> **Dependência de internet necessária:** Apenas para baixar os programas. Após configurado, **zero internet** para funcionar.

---

## Índice

1. [Abrindo a caixa — o que vem nas lâmpadas](#-etapa-1--abrindo-a-caixa)
2. [Instalar Home Assistant no servidor](#-etapa-2--instalar-o-home-assistant)
3. [Instalar HACS + Local Tuya](#-etapa-3--instalar-hacs--local-tuya)
4. [Parear as lâmpadas no WiFi](#-etapa-4--parear-as-lâmpadas-no-wifi-da-sua-casa)
5. [Configurar Local Tuya no Home Assistant](#-etapa-5--configurar-local-tuya)
6. [Cadastrar as lâmpadas no Alfredo](#-etapa-6--cadastrar-lâmpadas-no-alfredo)
7. [Testar comando de voz](#-etapa-7--testar-comando-de-voz)
8. [Expandir no futuro](#-etapa-8--expandir-no-futuro)

---

## 🟢 ETAPA 1 — Abrindo a caixa

Dentro da caixa de cada lâmpada Neo Avant vem:

- ✅ 1 lâmpada LED Pera (E27)
- ✅ 1 folheto com instruções

**NÃO jogue o folheto fora** — ele tem o código QR para parear no app.

> ⚠️ **Antes de rosquear:** anote o nome da lâmpada (ex: "Luz Sala", "Luz Escritório") num papel. Você vai usar esse nome no cadastro.

---

## 🟢 ETAPA 2 — Instalar o Home Assistant no servidor

O Home Assistant é o **tradutor universal** entre o Alfredo e as lâmpadas. Ele não tem IA, não pesa no servidor.

### 2.1 Acesse o servidor via SSH

```bash
ssh alfredo@192.168.15.100
```

### 2.2 Instale o Docker (se ainda não tiver)

```bash
curl -fsSL https://get.docker.com | sudo bash
sudo usermod -aG docker $USER
```

> Faz login de novo pra aplicar: `exit` e `ssh` de volta.

### 2.3 Crie a pasta de configuração e suba o container

```bash
mkdir -p ~/ha_config

docker run -d \
  --name homeassistant \
  --restart unless-stopped \
  --network host \
  -v ~/ha_config:/config \
  ghcr.io/home-assistant/home-assistant:stable
```

### 2.4 Verifique se está rodando

```bash
docker logs homeassistant --tail 20
```

Você deve ver algo como:

```
Starting Home Assistant
...
Waiting for someone to create the owner...
```

### 2.5 Acesse o Home Assistant

Abra no navegador do seu celular/PC:

```
http://192.168.15.100:8123
```

> ⚠️ Se estiver no mesmo servidor (sem display), acesse de outro dispositivo na mesma rede.

### 2.6 Crie a conta de administrador

| Campo | Valor sugerido |
|-------|---------------|
| Nome | `admin` |
| Usuário | `admin` |
| Senha | Escolha uma forte e **guarde** |
| Localização | Brasil / Sua cidade |

Após criar a conta, o Home Assistant vai pedir para configurar dispositivos. **Ignore por enquanto** — vamos fazer manualmente.

---

## 🟢 ETAPA 3 — Instalar HACS + Local Tuya

O **HACS** (Home Assistant Community Store) é a "lojinha" de plugins da comunidade. O **Local Tuya** é o plugin que permite controlar as lâmpadas **sem passar pela nuvem da China**.

### 3.1 Conecte-se ao servidor e instale o HACS

```bash
ssh alfredo@192.168.15.100

# Entra no container do Home Assistant
docker exec -it homeassistant bash

# Baixa e instala o HACS
wget -O - https://get.hacs.xyz | bash -

# Sai do container
exit
```

### 3.2 Reinicie o Home Assistant

```bash
docker restart homeassistant
sleep 10
```

### 3.3 Ative o HACS na interface

1. Abra `http://192.168.15.100:8123`
2. Vá em **Configurações → Dispositivos e Serviços**
3. Clique em **"Adicionar Integração"**
4. Busque por **"HACS"**
5. Siga as instruções (vai aparecer um QR code / link pra autenticar no GitHub)
6. Aceite os termos

### 3.4 Instale o Local Tuya pelo HACS

1. No Home Assistant, vá em **HACS → Integrações**
2. Clique nos **3 pontinhos (canto superior direito) → Repositórios Personalizados**
3. Adicione:
   - **URL:** `https://github.com/rospogrigio/localtuya`
   - **Categoria:** Integração
4. Clique em **"Adicionar"**
5. Agora procure por **"Local Tuya"** no HACS
6. Clique em **"Download"** e depois **"Instalar"**
7. Reinicie o Home Assistant:

```bash
docker restart homeassistant
```

---

## 🟢 ETAPA 4 — Parear as lâmpadas no WiFi da sua casa

Cada lâmpada Neo Avant precisa ser pareada uma única vez. O pareamento diz pra lâmpada: *"seu WiFi é esse, sua senha é essa"*.

### Modo de pareamento

1. Rosqueie a lâmpada em um **bocal ligado**
2. **Liga e desliga o interruptor 3 vezes** (ou 5 vezes, dependendo do modelo):
   - Liga (3s) → Desliga (3s) → Liga (3s) → Desliga (3s) → Liga
3. A lâmpada vai começar a **piscar rapidamente** (modo Smart Config / AP)

> Se não piscar, tente: liga/desliga rapidamente umas 7 vezes seguidas.

### Baixe o app **Smart Life** no celular

- Android: Play Store
- iOS: App Store

### Configure pelo app Smart Life

> **Importante:** Use a **rede 2.4 GHz** do seu roteador (lâmpadas WiFi não funcionam em 5 GHz).

1. Abra o app Smart Life
2. Crie uma conta (e-mail + senha) — **anote esses dados**, vamos usar depois
3. Toque em **"Adicionar Dispositivo"** (ou o **+** no canto)
4. O app vai detectar a lâmpada piscando
5. Selecione sua rede WiFi 2.4 GHz e digite a senha
6. Aguarde o pareamento (~30s)
7. Dê um nome pra lâmpada (ex: "Luz da Sala", "Luz do Escritório")

> 🔁 **Repita para cada lâmpada:** rosqueia, liga, pareia pelo app, dá nome.

---

## 🟢 ETAPA 5 — Extrair as chaves locais (Local Tuya)

Agora vem a parte mais crítica: extrair as **chaves de controle local** de cada lâmpada. Sem essas chaves, o Home Assistant não consegue controlá-las sem internet.

### 5.1 Crie uma conta no Tuya IoT Platform

1. Acesse: https://iot.tuya.com
2. Clique em **"Sign Up"** (criar conta)
3. Use o **mesmo e-mail** que você usou no app Smart Life
4. Complete o cadastro

### 5.2 Crie um projeto na nuvem

1. Faça login no Tuya IoT Platform
2. Vá em **"Cloud" → "Development"**
3. Clique em **"Create Cloud Project"**
4. Preencha:

| Campo | Valor |
|-------|-------|
| Project Name | `Alfredo OS` |
| Description | `Controle local das lampadas` |
| Industry | `Smart Home` |
| Data Center | Escolha o mais próximo de você (`Central Europe` se estiver em dúvida) |
| Development Method | `Custom` |

5. Clique em **"Create"**

### 5.3 Vincule o app Smart Life ao projeto

1. Dentro do projeto, vá em **"Devices"** (aba lateral)
2. Clique em **"Link Tuya App"** → **"Add App Account"**
3. Um QR code vai aparecer
4. Abra o app **Smart Life** no celular
5. Vá em **"Eu"** (perfil) → **"Central de Controle"** → **"Conta Vinculada"**
6. Escaneie o QR code
7. Confirme a vinculação

### 5.4 Pegue as credenciais do projeto (Authorization)

1. No projeto, vá em **"Overview"**
2. Anote os seguintes valores (vamos usar já já):

| Campo | Exemplo | Chame de |
|-------|---------|----------|
| **Access ID** | `abc123...` | `TUYA_ACCESS_ID` |
| **Access Secret** | `xyz789...` | `TUYA_ACCESS_SECRET` |

### 5.5 Descubra os `local_key` de cada lâmpada

Agora no servidor:

```bash
ssh alfredo@192.168.15.100

# Instala o tiny tuya (só pra fazer a descoberta)
pip install tinytuya

# Entra no Python e descobre os devices na rede
python3 << 'EOF'
import tinytuya

# Descobre lâmpadas na rede local
devices = tinytuya.deviceScan()

for ip, info in devices.items():
    print(f"\n=== Lâmpada encontrada ===")
    print(f"  IP:      {ip}")
    print(f"  ID:      {info.get('gwId', 'N/A')}")
    print(f"  Versão:  {info.get('version', 'N/A')}")
    print(f"  Produto: {info.get('productKey', 'N/A')}")
EOF
```

Este comando vai listar todas as lâmpadas na rede.

### 5.6 Use o Tuya CLI pra baixar as chaves

Ainda no servidor:

```bash
# Configura o tinytuya com suas credenciais da nuvem
python3 -m tinytuya wizard
```

O `wizard` vai pedir:

1. **Tuya Access ID** → cole o `Access ID` do passo 5.4
2. **Tuya Access Secret** → cole o `Access Secret` do passo 5.4
3. **País** → digite `55` (Brasil)

Ele vai gerar um arquivo `device.json` com todas as lâmpadas. Veja o resultado:

```bash
cat device.json | python3 -m json.tool
```

Para cada lâmpada, você verá algo como:

```json
{
    "name": "Luz da Sala",
    "id": "bfa2e7f...",
    "key": "a1b2c3d4e5f6g7h8",
    "ip": "192.168.15.50",
    "version": 3.3
}
```

Anote em uma tabela:

| Lâmpada | IP | Device ID | Local Key | Versão |
|---------|-----|-----------|-----------|--------|
| Luz da Sala | 192.168.15.50 | bfa2e7f... | a1b2c3d4... | 3.3 |
| Luz do Escritório | 192.168.15.51 | cfa3e8g... | h9i0j1k2... | 3.3 |

> 🔐 **Essas chaves são o segredo.** Sem elas as lâmpadas só funcionam pela nuvem da Tuya. Com elas, o controle é 100% local.

---

## 🟢 ETAPA 6 — Configurar Local Tuya no Home Assistant

### 6.1 Adicione a integração Local Tuya

1. No Home Assistant, vá em **Configurações → Dispositivos e Serviços**
2. Clique em **"Adicionar Integração"**
3. Busque por **"Local Tuya"**
4. Preencha para **cada lâmpada**:

| Campo | Valor |
|-------|-------|
| Name | `Luz da Sala` (o nome amigável) |
| Host | `192.168.15.50` (o IP da lâmpada) |
| Device ID | `bfa2e7f...` (o ID do passo 5.6) |
| Local Key | `a1b2c3d4...` (a chave do passo 5.6) |
| Protocol Version | `3.3` (a versão do passo 5.6) |
| Device Type | Selecione `light` |

5. Clique em **"Submit"**

### 6.2 Verifique o `entity_id`

Após adicionar, o Home Assistant cria uma entidade pra lâmpada.

1. Vá em **Configurações → Dispositivos e Serviços → Entidades**
2. Filtre por `light.` ou pelo nome da lâmpada
3. Anote o **`entity_id`** (ex: `light.luz_da_sala`)

Você também pode testar: clique no botão **ligar/desligar** na interface do HA pra ver se funciona.

---

## 🟢 ETAPA 7 — Cadastrar as lâmpadas no Alfredo

### 7.1 Configure o arquivo `.env`

No servidor:

```bash
cd ~/alfredo-core
nano .env
```

Adicione ou edite:

```env
HOME_ASSISTANT_URL=http://192.168.15.100:8123
HOME_ASSISTANT_TOKEN=
```

Gere o token de acesso:

1. No Home Assistant, clique no seu **usuário** (canto inferior esquerdo)
2. Vá em **"Tokens de Acesso Longo"**
3. Crie um com nome `Alfredo OS`
4. **Copie o token** (só aparece uma vez!) e cole no `.env`:

```env
HOME_ASSISTANT_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ...
```

### 7.2 Popule os cômodos no banco

```bash
cd ~/alfredo-core
python scripts/seed_rooms.py
```

Saída esperada:

```
=== Seed de Cômodos ===
  ✅ Criado cômodo: ROOM_LIVING → Sala
  ✅ Criado cômodo: ROOM_OFFICE → Escritório
```

### 7.3 Cadastre cada lâmpada

Substitua os valores pelos `entity_id` que você anotou no passo 6.2:

```bash
# Exemplo: Luz da Sala
curl -X POST http://localhost:10001/api/smart-devices \
  -H "Content-Type: application/json" \
  -d '{
    "entity_id": "light.luz_da_sala",
    "friendly_name": "Luz da Sala",
    "device_type": "light",
    "room_id": "ROOM_LIVING"
  }'

# Exemplo: Luz do Escritório
curl -X POST http://localhost:10001/api/smart-devices \
  -H "Content-Type: application/json" \
  -d '{
    "entity_id": "light.luz_do_escritorio",
    "friendly_name": "Luz do Escritório",
    "device_type": "light",
    "room_id": "ROOM_OFFICE"
  }'
```

> 🔁 **Repita para cada lâmpada que você comprou.**

### 7.4 Verifique se está tudo cadastrado

```bash
curl http://localhost:10001/api/smart-devices | python3 -m json.tool
```

Debe retornar a lista de todas as suas lâmpadas.

---

## 🟢 ETAPA 8 — TESTAR COMANDO DE VOZ

### Pelo Dashboard (teste rápido sem satélite)

1. Abra o Dashboard do Alfredo: `http://192.168.15.100:10001`
2. Na caixa de texto, digite:

```
Acende a luz da sala
```

3. A resposta deve ser:

```
Liguei Luz da Sala.
```

4. Teste outros comandos:

| Comando | Ação esperada |
|---------|---------------|
| `Apaga a luz da sala` | Desliga |
| `Luz do escritório em 50%` | Ajusta brilho |
| `Apaga todas as luzes` | Desliga todas do cômodo atual |
| `Acende a luz do escritório` | Liga a do outro cômodo |

### Pelo satélite físico

Se o satélite já estiver funcionando, basta falar:

> *"Alfredo, acende a luz da sala"*

O fluxo completo em ~800ms:

```
🗣️ "Alfredo, acende a luz da sala"
   ↓
🎤 Satélite captura o áudio
   ↓
🖥️ Servidor faz STT + Gemini
   ↓
🧠 Gemini entende: manage_smart_device(action=turn_on, device_type=light, ...)
   ↓
🔌 Skill resolve cômodo → busca dispositivo no banco → chama HA
   ↓
💡 Home Assistant → Local Tuya → UDP → Lâmpada ASCENDE (<300ms)
   ↓
🔊 "Liguei Luz da Sala." (TTS)
```

---

## 🟢 ETAPA 9 — Expandir no futuro

### Comprar mais lâmpadas (mesmo modelo)

1. Rosqueia e pareia pelo app Smart Life
2. Roda `python3 -m tinytuya wizard` pra pegar a nova local_key
3. Adiciona a integração no Home Assistant
4. Cadastra no Alfredo com `curl POST /api/smart-devices`

### Adicionar novo cômodo

```bash
# Cria o cômodo
curl -X POST http://localhost:10001/api/rooms \
  -H "Content-Type: application/json" \
  -d '{"room_id":"ROOM_BEDROOM","name":"Quarto"}'

# Cadastra a lâmpada
curl -X POST http://localhost:10001/api/smart-devices \
  -H "Content-Type: application/json" \
  -d '{
    "entity_id": "light.luz_quarto",
    "friendly_name": "Luz do Quarto",
    "device_type": "light",
    "room_id": "ROOM_BEDROOM"
  }'
```

Pronto. O Alfredo já reconhece: *"Acende a luz do quarto"* sem nenhuma alteração no código.

### Hub IR RF (ventilador, ar-condicionado)

Quando chegar o hub IR RF (Broadlink, por exemplo):

1. Conecta o hub no Home Assistant (integração oficial Broadlink)
2. Aprende os comandos do controle pelo HA
3. O dispositivo aparece como `switch.ventilador_sala` ou `fan.ventilador`
4. Cadastra no Alfredo com `device_type: "fan"` ou `"switch"`
5. Pronto: *"Liga o ventilador"*, *"Velocidade alta do ventilador"*

---

## 🆘 Solução de problemas

| Problema | Causa provável | Solução |
|----------|---------------|---------|
| Lâmpada não aparece no `deviceScan()` | Lâmpada em rede 5 GHz | Use rede 2.4 GHz |
| `local_key` errada | Expirou na nuvem Tuya | Vincula de novo o app Smart Life no IoT Platform |
| Home Assistant não responde | Container parou | `docker start homeassistant` |
| Alfredo responde "não encontrei" | Dispositivo não cadastrado | `curl GET /api/smart-devices` pra listar |
| Comando funciona no HA mas não no Alfredo | Token expirou | Gera novo token no perfil do HA |
| Lâmpada não obedece mesmo com HA funcionando | IP mudou (DHCP) | Configure IP fixo no roteador pra cada lâmpada |

### Recomendação: IP fixo pra cada lâmpada

No seu roteador, configure **reserva de IP (DHCP estático)** para cada lâmpada:

| Dispositivo | IP sugerido |
|------------|-------------|
| Luz da Sala | 192.168.15.50 |
| Luz do Escritório | 192.168.15.51 |
| (futuras) | 192.168.15.52+ |

Assim o IP nunca muda e você não precisa reconfigurar o Local Tuya.

---

## 📊 Resumo do que foi instalado

| Componente | Função | Onde roda | Peso |
|-----------|--------|-----------|------|
| **Home Assistant** | Tradutor de comandos | Servidor (Docker) | ~300 MB RAM |
| **Local Tuya** (HACS) | Plugin de controle local Tuya | Dentro do HA | ~20 MB |
| **Lâmpadas Neo Avant** | Dispositivo final | Na rede WiFi | 0 (são as lâmpadas) |
| **Alfredo OS** | Assistente de voz | Servidor (FastAPI) | ~150 MB RAM |

**Consumo total no servidor:** ~500 MB de RAM, menos de 5% de CPU.

**Zero dependência de internet para funcionar.**

---

> **Próximos passos sugeridos:**
> - Criar rotinas ("Todo dia às 18h acende a luz da sala")
> - Configurar o sensor de presença pra acender luz automaticamente
> - Integrar o hub IR RF quando chegar
