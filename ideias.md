# Backlog de Grandes Melhorias — Alfredo OS 🧠

Este é o nosso backlog mental (e oficial) que fica guardado no repositório do projeto no arquivo `ideias.md`. Aqui estão as próximas grandes evoluções que farão o Alfredo passar de um ótimo assistente para um **Mordomo Virtual Verdadeiramente Inteligente**.

> [!TIP]
> Você pode abrir, editar e adicionar mais coisas diretamente no arquivo `ideias.md` na raiz do seu projeto!

---

## 🎵 1. Dashboard Interativo de Mídia (Spotify/YouTube)
*Adicionado hoje a pedido do usuário*

**O Problema Atual:** O Dashboard apenas observa passivamente a mídia (mostrando a capa do álbum do Spotify quando toca). Para escolher música, o usuário depende da voz ou de apps externos.
**A Visão:**
- **Barra de Busca Universal:** Uma barra no painel (aba de Integrações ou Visão Geral) que pesquisa em tempo real diretamente nas APIs do YouTube e Spotify.
- **Seletor de Destino (Satélites):** Encontrou a música? Um menu dropdown pergunta: "Onde tocar?". O usuário seleciona `Quarto`, `Sala`, ou `Modo Festa (Todos)`.
- **Backend Orquestrador:** O Alfredo despacha os URIs corretos (Websocket/MQTT) ordenando que as instâncias locais de cada cômodo comecem o playback instantaneamente.

## 📅 2. O Assistente Pessoal de Agenda Completo
O objetivo é que o Alfredo pareça um gerente de agenda humano, e não apenas um CRUD de calendário.

**A Visão:**
- **Eventos Recorrentes Complexos:** Suporte nativo a regras dinâmicas como *"Toda primeira sexta do mês"* ou *"A cada duas semanas"*, abandonando a ideia de apenas duplicar eventos no banco de dados.
- **Cancelamento Inteligente:** O Alfredo sabe contextualizar. Se você disser *"Cancela o médico"*, ele não vai bugar se houver três consultas médicas diferentes. Ele perguntará: *"Você quer cancelar a consulta oftalmológica de hoje ou o pediatra de quinta?"*.
- **Reagendamento Fluido por Voz:** *"Alfredo, adia o dentista em 30 minutos"* ou *"Mova minha reunião de hoje para quinta no mesmo horário"* (O sistema recalcula conflitos e avisa).

## 📍 3. Inteligência Geográfica e de Trânsito
O Alfredo precisa entender não só o *quando*, mas o *onde* e o *como*.

**A Visão:**
- **Salvar Locais Específicos:** O usuário registra *"Hospital Copa D'Or"*. 
- **Alerta Proativo de Deslocamento:** O Alfredo cruza o local com a API de trânsito (Google Maps/OSRM) e notifica espontaneamente no satélite: *"Henrique, há trânsito intenso. Recomendo sair em 25 minutos para chegar ao compromisso no horário."*
- **Avisos Climáticos Contextuais:** *"Há previsão de chuva forte na hora da sua saída, não esqueça o guarda-chuva."*

## 🔊 4. Presença e Localização Indoor (Multi-room Inteligente)
O Alfredo já entende de qual satélite a voz está vindo (ex: `sala-001`). O próximo passo é o sistema ser proativo em relação a isso.

**A Visão:**
- **Notificações Direcionadas:** Se um alarme toca e o Alfredo detectou sua presença (voz) na Cozinha há 1 minuto, o alarme toca apenas no satélite da Cozinha, não acordando quem está no Quarto.
- **Contexto Contínuo:** Se você pede para ligar a TV na sala, e vai para o quarto, ao dizer *"Alfredo, aumenta o volume"*, ele sabe que no Quarto a TV não está ligada, mas o abajur sim, e ajusta a interpretação do comando.

---

> [!IMPORTANT]
> A API de status offline/online de satélites que implementamos agora há pouco já é o primeiro passo arquitetural para a funcionalidade Multi-room (item 4)!
