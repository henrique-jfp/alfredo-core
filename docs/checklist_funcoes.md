# Capacidades do Alfredo Home OS

O Alfredo Home OS é um assistente virtual focado em processamento local com habilidades de automação residencial, integrações com APIs externas e processamento de linguagem natural (NLP). 

Aqui está um mapeamento completo de **tudo o que ele já consegue fazer** até o momento (Versão 2.0), incluindo os motores de inteligência e os testes práticos que você pode falar no microfone para validar.

---

## 🗣️ Motor de Voz e Inteligência (Core)

O coração do Alfredo funciona num pipeline de 4 etapas:
1. **Ouvir (STT)**: Usa Vosk offline para transcrever o áudio localmente e com privacidade total.
2. **Entender (NLP)**: Usa Spacy (com fallback para Regex) para identificar a *Intent* (intenção) da sua frase.
3. **Agir (Skills)**: Executa o código Python específico daquela intenção. Se ele não souber, cai no **Fallback**.
4. **Falar (TTS)**: Usa Piper TTS (Voz Faber) para sintetizar a resposta localmente.

### Habilidade 0: Bate-papo Inteligente (Fallback LLM)
Se você perguntar algo que não é uma automação de casa programada (como uma curiosidade ou puxar papo), o Alfredo percebe que não tem uma *Skill* local para aquilo e envia sua frase para a **nuvem (Groq Llama-3 ou Gemini)**, com o contexto das suas últimas conversas na sala.
* **Teste Prático:** `"Me conte uma piada sobre pinguins."`
* **Teste Prático:** `"Qual a capital da Austrália?"`
* **Teste Prático:** `"O que você acha de inteligência artificial?"`

---

## ⏰ Habilidades de Tempo e Agenda

### 1. Relógio e Calendário (`TimeSkill`)
Responde horas, datas e o dia atual.
* **Teste Prático (Hora):** `"Que horas são?"`
* **Teste Prático (Data):** `"Que dia é hoje?"` ou `"Qual a data de hoje?"`

### 2. Despertadores e Timers (`TimerSkill`)
Cria alarmes pontuais e contagens regressivas. Quando o tempo acaba, ele te avisa usando voz ou som na sala.
* **Teste Prático (Timer):** `"Me avise daqui a 2 minutos para olhar o forno."`
* **Teste Prático (Timer Rápido):** `"Inicie um cronômetro de 30 segundos."`
* **Teste Prático (Alarme):** `"Me acorde amanhã às 7 da manhã."`

### 3. Agenda de Compromissos (`CalendarSkill`)
Salva e lê eventos num banco de dados atrelado à sala atual.
* **Teste Prático (Criar):** `"Adicione dentista amanhã às 14 horas."`
* **Teste Prático (Criar 2):** `"Marque reunião hoje às 16."`
* **Teste Prático (Ler):** `"Quais os meus compromissos de amanhã?"`
* **Teste Prático (Ler 2):** `"O que eu tenho na agenda hoje?"`

---

## 🏠 Habilidades de Utilidade

### 4. Previsão do Tempo (`WeatherSkill`)
Consulta a temperatura, umidade e a descrição climática baseada na Cidade cadastrada nas *Configurações do Dashboard*.
* **Teste Prático:** `"Como está o clima hoje?"`
* **Teste Prático:** `"Qual a temperatura agora?"`
* **Teste Prático:** `"Vai chover hoje?"`

### 5. Notícias (`NewsSkill`)
Lê as 3 principais manchetes do momento de um feed RSS (por padrão, o portal G1, configurável no Dashboard).
* **Teste Prático:** `"Quais as notícias de hoje?"`
* **Teste Prático:** `"O que está acontecendo no mundo?"`
* **Teste Prático:** `"Me diga as manchetes."`

### 6. Trânsito para o Trabalho (`TrafficSkill`)
Calcula a distância e o tempo estimado de viagem da sua *Casa* até o seu *Trabalho*. (Puxa os endereços das *Localizações Salvas* no Dashboard). Se a chave da API do Google Maps estiver configurada, leva o congestionamento real em consideração; se não, usa a API livre do OSRM.
* **Teste Prático:** `"Como está o trânsito para o trabalho?"`
* **Teste Prático:** `"Quanto tempo eu levo até o trabalho hoje?"`

### 7. Listas de Compras e Tarefas (`ListSkill`)
Permite ler, adicionar, remover ou esvaziar itens das suas listas de compras e tarefas do dia a dia.
* **Teste Prático (Adicionar Tarefa):** `"Anote comprar pão."`
* **Teste Prático (Adicionar Compra):** `"Coloque leite na minha lista de compras."`
* **Teste Prático (Ler):** `"O que tem na minha lista de compras?"`
* **Teste Prático (Remover):** `"Risque o pão da lista."` ou `"Apague leite da lista de compras."`
* **Teste Prático (Esvaziar):** `"Esvazie a lista de tarefas."`

---

## 🎵 Habilidades de Entretenimento

### 8. Controle de Música (Spotify) (`MusicSkill`)
Busca músicas e artistas, dá play, pause e pula faixas nos seus dispositivos do Spotify conectados (computador, Alexa, celular). Exige vínculo pelo *Dashboard*.
* **Teste Prático (Tocar Música Específica):** `"Toque Bohemian Rhapsody no Spotify."`
* **Teste Prático (Tocar Artista):** `"Toca músicas do Michael Jackson."`
* **Teste Prático (Pausar/Play):** `"Pare a música."` ou `"Retomar música."`
* **Teste Prático (Pular):** `"Próxima música."` ou `"Pular faixa."`

### 9. YouTube e Lives (`YouTubeSkill`)
Extrai o áudio de vídeos ou de transmissões ao vivo e toca nos alto-falantes do satélite local!
* **Teste Prático (Vídeo Gravado):** `"Toque o último vídeo do Jovem Nerd no YouTube."`
* **Teste Prático (Live/Ao Vivo):** `"Coloque a live da CazéTV."` ou `"Ao vivo GloboNews no YouTube."`

---

## ⚙️ Dashboard e Rotinas

Além da voz, você interage com o Alfredo pelo Painel Web.
* **Rotinas:** Você pode automatizar as habilidades acima. Por exemplo, uma rotina todo dia às `07:30` que simula o comando `"Como está o clima"`. O Alfredo vai te falar o tempo automaticamente sem você precisar perguntar.
* **Múltiplos Endereços:** Pode salvar latitudes e longitudes para a casa, escritório, casa da mãe, etc.
* **Múltiplas Vozes:** Dá pra alterar se ele terá uma voz mais grave, mais suave ou se terá sotaque português de Portugal.
