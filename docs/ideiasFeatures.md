###   Idéias de novas funções para o assistente:

# 1. Modo Tarefa Escolar / Quiz:

- Expandir o uso da IA (ai_fallback/) para criar uma rotina de estudos interativa. O assistente pode fazer perguntas faladas de matemática ou geografia e validar as respostas, sendo uma ótima ferramenta lúdica para ajudar uma criança de 9 anos com os deveres de casa.

# 2. Assistente de Enogastronomia e Receitas:
- Uma skill que lê o passo a passo de receitas sem que você precise sujar a tela do celular. Como bônus, você pode perguntar por harmonizações (ex: "Alfredo, qual queijo combina com um vinho Carménère ou do Porto?") para planejar jantares e viagens.

# 3. DreamJournalTool (Diário de Sonhos com IA):
- o usuário fala ao satélite: "Alfredo, tive um sonho..." e descreve o que sonhou em fluxo de consciência, sem estrutura. O Alfredo transcreve via Whisper/Groq, extrai elementos-chave com o Gemini (personagens, ambientes, emoções, símbolos), salva no SQLite com data, e gera uma interpretação poética + psicológica da narrativa.

- Com o tempo, o Alfredo começa a identificar padrões: "Você sonhou com água em 4 dos últimos 7 dias, geralmente em contextos de mudança". O dashboard exibe uma linha do tempo visual dos sonhos com nuvem de palavras e frequência de temas. É uma função que nenhum outro assistente de voz doméstico tem, extremamente pessoal, e que cria um vínculo único entre o usuário e o sistema — tornando o Alfredo verdadeiramente irreplicável.

# 4. 🗣️ MemoryTool — Memória de Longo Prazo do Usuário:
- O Alfredo salva fatos relevantes que o usuário menciona: "Me lembro que você disse que trabalha até meia-noite às sextas" e usa isso para contextualizar respostas futuras. Implementado como uma tabela SQLite simples de fatos do usuário consultada via RAG simplificado antes de cada resposta.

# 5. 🎬 MediaQueryTool — Busca de Filmes/Séries
- Integre com a TMDB API (gratuita). "O que devo assistir hoje? Quero algo de ficção científica dos anos 90" → o Gemini usa a ferramenta para buscar com os filtros corretos e retorna 3 sugestões com nota, sinopse curta e onde assistir.

# 6. 10. 🌐 TranslateTool — Tradução Instantânea por Voz
- "Alfredo, como se fala 'preciso de ajuda' em japonês?" → usa a API gratuita do LibreTranslate ou diretamente o Gemini como tradutor. Pode incluir modo de estudo de idioma: "Me ensina 5 palavras em espanhol hoje". Custo zero pois o Gemini já está no pipeline.