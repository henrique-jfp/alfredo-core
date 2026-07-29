"""
Skill de leitura de livros para o Alfredo.

Reconhece intenções de voz como "leia o Senhor dos Anéis", "continua a
leitura", "para de ler" e interage com a biblioteca de ebooks.

Segue o padrão de Skill existente: name, can_handle, execute, execute_tool.
Registrada no AgentRouter como "manage_book_reading".
"""
import asyncio
import difflib
import json
import logging
import unicodedata
from typing import Any, Dict

from core.brain.skills.base import Skill

logger = logging.getLogger("alfredo.skills.book_reading")

# ── Mapeamento gênero → ambiente ────────────────────────────────────────
# Palavras-chave que indicam o gênero do livro. O sistema ativa o ambiente
# automaticamente quando a leitura começa.
_GENRE_KEYWORDS: dict[str, list[str]] = {
    "forest": [
        "floresta", "fada", "drago", "magia", "feiticeir", "elf", "orcs",
        "senhor dos anéis", "senhor dos aneis", "harry potter", "castel",
        "reino", "espada", "trono", "guerra dos tronos", "game of thrones",
        "fantasia", "mago", "aventura", "heroi", "heroi", "cavaleir",
        "bruxo", "bruxa", "encantado", "profecia", "reino", "dragao",
        "torre", "jornada", "reino", "reino", "reino",
    ],
    "rain": [
        "terror", "suspense", "horror", "assombrad", "fantasma", "crime",
        "misterio", "sombr", "escuro", "trevas", "morte", "grito",
        "vinganc", "serial killer", "investigac", "thriller", "nevoa",
        "neblina", "macabro", "assassino", "morto", "sangue", "medo",
        "psicologico", "psicopata", "obscuro", "noite", "lua",
        "stephen king", "king", "it a coisa", "coisa", "iluminado",
        "cemiterio", "carrie", "misery", "sobrenatural", "oculto",
        "assombracao", "assombração", "zumbi", "vampiro", "lobo",
        "lobisomem", "demonio", "exorcista", "possessao",
        "agatha christie", "sherlock holmes", "conan doyle",
        "negra", "nevoento", "sombrio", "pesadelo", "insano",
    ],
    "cafe": [
        "romance", "amor", "coraca", "paixa", "casamento", "encontro",
        "namoro", "cafe", "cha", "conversa", "amizade", "sentimental",
        "comedia romantica", "comédia romântica", "romantico", "romantico",
        "coração", "paixão", "beijo", "abraco", "sentimento", "almoca",
        "jantar", "restaurante", "presente", "surpresa", "carinho",
    ],
    "fire": [
        "inverno", "frio", "neve", "lareira", "aconchego", "casa",
        "lar", "fogao", "fogueira", "acampamento", "cabana", "refugio",
        "drama", "familia", "emocionante", "emocao", "lagrima",
        "perda", "superacao", "conforto", "quent", "abrigo",
    ],
}

# Ambientes padrão para gêneros não detectados (fallback consistente)
_FALLBACK_AMBIENT = "forest"


def _normalize(text: str) -> str:
    """Normaliza texto para comparação fuzzy: remove acentos, lowercase."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def _detect_genre(title: str, author: str = "") -> str:
    """Detecta o genero do livro baseado no titulo + autor.

    Retorna o nome do ambiente mais compativel: 'forest', 'rain', 'cafe', 'fire'.
    Usa 'forest' como fallback se nenhum genero for claramente identificado.
    """
    text = _normalize(f"{title} {author}")
    scores = {genre: 0 for genre in _GENRE_KEYWORDS}

    for genre, keywords in _GENRE_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                scores[genre] += 1

    best = max(scores, key=lambda g: (
        scores[g],
        max((len(kw) for kw in _GENRE_KEYWORDS[g] if kw in text), default=0)
    ))

    if scores[best] == 0:
        return _FALLBACK_AMBIENT

    logger.info("Genero detectado: '%s' (scores: %s) para '%s'", best, scores, title)
    return best


class BookReadingSkill(Skill):

    @property
    def name(self) -> str:
        return "BookReadingSkill"

    def can_handle(self, intent: str, text: str) -> bool:
        return intent == "BOOK_READING"

    def execute(self, text: str, context: Dict[str, Any]) -> str:
        return "Para ouvir um livro, diga o título. Posso também listar os livros da biblioteca."

    def execute_tool(self, kwargs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        action = kwargs.get("action", "play")
        title = kwargs.get("title", "").strip()
        chapter_index = kwargs.get("chapter_index")
        room_id = context.get("room_id", "ROOM_LIVING")
        db = context.get("db")

        if not db:
            return {"direct_response": "Erro interno: banco de dados não disponível.", "status": "fail"}

        if action == "list":
            return self._list_books(db)
        elif action == "play":
            return self._play_book(title, chapter_index, room_id, db, context)
        elif action == "pause" or action == "stop":
            return self._stop_reading(room_id, db)
        elif action == "resume":
            return self._resume_reading(room_id, db, context)
        elif action == "next":
            return self._next_chapter(room_id, db, context)
        elif action == "previous":
            return self._previous_chapter(room_id, db, context)
        else:
            return {"direct_response": f"Ação '{action}' não reconhecida.", "status": "fail"}

    def _list_books(self, db) -> Dict[str, Any]:
        """Lista livros disponíveis na biblioteca."""
        from core.brain.memory import models

        books = db.query(models.Book).order_by(models.Book.added_at.desc()).all()
        if not books:
            return {
                "direct_response": "A biblioteca está vazia. Você pode adicionar livros pelo Dashboard.",
                "status": "success",
            }

        lines = ["Livros na biblioteca:"]
        for b in books:
            author_str = f", de {b.author}" if b.author else ""
            lines.append(f"  • {b.title}{author_str} ({b.total_chapters} capítulos)")

        return {
            "direct_response": "\n".join(lines),
            "status": "success",
        }

    def _play_book(self, title: str, chapter_index, room_id: str, db, context) -> Dict[str, Any]:
        """Inicia a leitura de um livro."""
        from core.brain.memory import models

        if not title:
            # Verifica se há uma sessão ativa para retomar
            session = (
                db.query(models.SessionState)
                .filter(models.SessionState.room_id == room_id)
                .first()
            )
            if session and session.skill_name == "manage_book_reading":
                return self._resume_reading(room_id, db, context)

            return {
                "direct_response": "Qual livro você gostaria de ouvir? Diga o título.",
                "status": "fail",
            }

        # Busca livro por fuzzy match no título
        books = db.query(models.Book).all()
        if not books:
            return {
                "direct_response": "A biblioteca está vazia. Adicione livros pelo Dashboard primeiro.",
                "status": "fail",
            }

        book = self._fuzzy_find_book(title, books)
        if not book:
            return {
                "direct_response": f"Não encontrei nenhum livro parecido com '{title}' na biblioteca.",
                "status": "fail",
            }

        ch_idx = chapter_index if chapter_index is not None else 0

        # Cria sessão e retorna instrução para o LLM responder ao usuário
        session = {
            "params": {
                "book_id": book.id,
                "chapter_index": ch_idx,
                "status": "playing",
            }
        }

        # Dispara a leitura de forma assíncrona via API interna
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(self._trigger_play(book.id, ch_idx, room_id))
            else:
                loop.run_until_complete(self._trigger_play(book.id, ch_idx, room_id))
        except Exception as e:
            logger.error("Erro ao disparar leitura: %s", e)

        chapter_info = ""
        if ch_idx > 0:
            chapter = (
                db.query(models.BookChapter)
                .filter(
                    models.BookChapter.book_id == book.id,
                    models.BookChapter.index == ch_idx,
                )
                .first()
            )
            if chapter and chapter.title:
                chapter_info = f", capítulo '{chapter.title}'"

        author_str = f", de {book.author}" if book.author else ""

        # ── Ativa som ambiente automaticamente baseado no gênero do livro ──
        try:
            from core.voice.ambience import get_ambience_manager
            genre_ambient = _detect_genre(book.title, book.author or "")
            ambience = get_ambience_manager()
            if ambience.set_ambient(genre_ambient):
                logger.info("Ambiente '%s' ativado para leitura de '%s'", genre_ambient, book.title)
        except Exception as e:
            logger.warning("Erro ao ativar ambiente para leitura: %s", e)

        return {
            "direct_response": (
                f"Iniciando a leitura de '{book.title}'{author_str}{chapter_info}. "
                f"O áudio está sendo preparado e será reproduzido em instantes. "
                f"Para pausar, diga 'pare de ler'."
            ),
            "status": "success",
            "session": session,
        }

    def _stop_reading(self, room_id: str, db) -> Dict[str, Any]:
        """Para a leitura ativa no cômodo."""
        self._send_stop_to_room(room_id)
        # Desativa som ambiente ao pausar leitura
        try:
            from core.voice.ambience import get_ambience_manager
            ambience = get_ambience_manager()
            if ambience.is_active:
                ambience.stop_ambient()
                logger.info("Ambiente desativado ao pausar leitura")
        except Exception as e:
            logger.warning("Erro ao desativar ambiente: %s", e)
        return {
            "direct_response": "Leitura pausada. Para continuar, diga 'continue a leitura'.",
            "status": "success",
            "session": {"end": True},
        }

    def _resume_reading(self, room_id: str, db, context) -> Dict[str, Any]:
        """Retoma a leitura de onde parou."""
        from core.brain.memory import models

        session = (
            db.query(models.SessionState)
            .filter(models.SessionState.room_id == room_id)
            .first()
        )
        if not session or session.skill_name != "manage_book_reading":
            return {
                "direct_response": "Não há nenhuma leitura em andamento para retomar.",
                "status": "fail",
            }

        state = json.loads(session.state_data) if session.state_data else {}
        book_id = state.get("book_id")
        chapter_index = state.get("chapter_index", 0)

        book = db.query(models.Book).filter(models.Book.id == book_id).first()
        if not book:
            return {
                "direct_response": "O livro que estava sendo lido foi removido da biblioteca.",
                "status": "fail",
                "session": {"end": True},
            }

        # Pára áudio atual antes de retomar
        self._send_stop_to_room(room_id)

        # Dispara a leitura
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(self._trigger_play(book_id, chapter_index, room_id))
            else:
                loop.run_until_complete(self._trigger_play(book_id, chapter_index, room_id))
        except Exception as e:
            logger.error("Erro ao retomar leitura: %s", e)

        # Reativa ambiente ao retomar leitura
        try:
            from core.voice.ambience import get_ambience_manager
            genre_ambient = _detect_genre(book.title, book.author or "")
            ambience = get_ambience_manager()
            if ambience.set_ambient(genre_ambient):
                logger.info("Ambiente '%s' reativado ao retomar '%s'", genre_ambient, book.title)
        except Exception as e:
            logger.warning("Erro ao reativar ambiente: %s", e)

        new_session = {
            "params": {
                "book_id": book_id,
                "chapter_index": chapter_index,
                "status": "playing",
            }
        }

        return {
            "direct_response": (
                f"Retomando a leitura de '{book.title}', "
                f"capítulo {chapter_index + 1} de {book.total_chapters}."
            ),
            "status": "success",
            "session": new_session,
        }

    def _next_chapter(self, room_id: str, db, context) -> Dict[str, Any]:
        """Avança para o próximo capítulo do livro ativo."""
        from core.brain.memory import models

        session = (
            db.query(models.SessionState)
            .filter(models.SessionState.room_id == room_id)
            .first()
        )
        if not session or session.skill_name != "manage_book_reading":
            return {
                "direct_response": "Não há nenhuma leitura em andamento para avançar.",
                "status": "fail",
            }

        state = json.loads(session.state_data) if session.state_data else {}
        book_id = state.get("book_id")
        current_index = state.get("chapter_index", 0)

        book = db.query(models.Book).filter(models.Book.id == book_id).first()
        if not book:
            return {
                "direct_response": "O livro que estava sendo lido foi removido da biblioteca.",
                "status": "fail",
                "session": {"end": True},
            }

        next_index = current_index + 1
        if next_index >= book.total_chapters:
            return {
                "direct_response": (
                    f"Você já está no último capítulo de '{book.title}'."
                ),
                "status": "fail",
            }

        # Pára o áudio atual antes de iniciar o próximo
        self._send_stop_to_room(room_id)

        # Dispara o próximo capítulo
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(self._trigger_play(book_id, next_index, room_id))
            else:
                loop.run_until_complete(self._trigger_play(book_id, next_index, room_id))
        except Exception as e:
            logger.error("Erro ao disparar próximo capítulo: %s", e)

        return {
            "direct_response": (
                f"Avançando para o capítulo {next_index + 1} de {book.total_chapters} de '{book.title}'."
            ),
            "status": "success",
            "session": {
                "params": {
                    "book_id": book_id,
                    "chapter_index": next_index,
                    "status": "playing",
                }
            },
        }

    def _previous_chapter(self, room_id: str, db, context) -> Dict[str, Any]:
        """Volta para o capítulo anterior do livro ativo."""
        from core.brain.memory import models

        session = (
            db.query(models.SessionState)
            .filter(models.SessionState.room_id == room_id)
            .first()
        )
        if not session or session.skill_name != "manage_book_reading":
            return {
                "direct_response": "Não há nenhuma leitura em andamento para voltar.",
                "status": "fail",
            }

        state = json.loads(session.state_data) if session.state_data else {}
        book_id = state.get("book_id")
        current_index = state.get("chapter_index", 0)

        book = db.query(models.Book).filter(models.Book.id == book_id).first()
        if not book:
            return {
                "direct_response": "O livro que estava sendo lido foi removido da biblioteca.",
                "status": "fail",
                "session": {"end": True},
            }

        prev_index = current_index - 1
        if prev_index < 0:
            return {
                "direct_response": (
                    f"Você já está no primeiro capítulo de '{book.title}'."
                ),
                "status": "fail",
            }

        # Pára o áudio atual antes de iniciar o anterior
        self._send_stop_to_room(room_id)

        # Dispara o capítulo anterior
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(self._trigger_play(book_id, prev_index, room_id))
            else:
                loop.run_until_complete(self._trigger_play(book_id, prev_index, room_id))
        except Exception as e:
            logger.error("Erro ao disparar capítulo anterior: %s", e)

        return {
            "direct_response": (
                f"Voltando para o capítulo {prev_index + 1} de {book.total_chapters} de '{book.title}'."
            ),
            "status": "success",
            "session": {
                "params": {
                    "book_id": book_id,
                    "chapter_index": prev_index,
                    "status": "playing",
                }
            },
        }

    @staticmethod
    def _send_stop_to_room(room_id: str):
        """Envia comando de parar áudio para o satélite do cômodo."""
        try:
            from core.api.satellite import manager
            from core.brain.memory.database import SessionLocal
            from core.brain.memory import models

            db = SessionLocal()
            try:
                device = (
                    db.query(models.Device)
                    .filter(models.Device.room_id == room_id)
                    .first()
                )
                if device:
                    ws = manager.active_satellites.get(device.device_id)
                    if ws:
                        import asyncio
                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                asyncio.ensure_future(
                                    manager.send_command_to_satellite(device.device_id, "tts_end")
                                )
                        except Exception as e:
                            logger.warning("Erro ao enviar stop: %s", e)
            finally:
                db.close()
        except Exception as e:
            logger.warning("Não foi possível parar áudio no cômodo %s: %s", room_id, e)

    async def _trigger_play(self, book_id: int, chapter_index: int, room_id: str):
        """Dispara a preparação e streaming do áudio em background.

        Para o áudio atual do cômodo, prepara o capítulo (anotação + síntese)
        com timeout e envia o áudio para o satélite.

        Erros são logados e não propagados (fire-and-forget).
        """
        from core.brain.memory.database import SessionLocal
        from core.brain.memory import models
        from core.api.library import _ensure_chapter_ready, _stream_audio_to_satellite, _update_session

        db = SessionLocal()
        try:
            chapter = (
                db.query(models.BookChapter)
                .filter(
                    models.BookChapter.book_id == book_id,
                    models.BookChapter.index == chapter_index,
                )
                .first()
            )
            if not chapter:
                logger.error("Capítulo %d do livro %d não encontrado", chapter_index, book_id)
                return

            # Timeout total para preparação (anotação + síntese)
            # Capítulos muito longos podem travar o pipeline
            audio_path = await asyncio.wait_for(
                _ensure_chapter_ready(chapter, db),
                timeout=300.0,  # 5 minutos
            )

            # Atualiza sessão antes de tocar
            _update_session(db, room_id, book_id, chapter_index, "playing")

            # Envia áudio para o satélite com timeout
            await asyncio.wait_for(
                _stream_audio_to_satellite(room_id, audio_path, db),
                timeout=600.0,  # 10 minutos para streaming
            )
        except asyncio.TimeoutError:
            logger.error(
                "Timeout ao preparar/transmitir capítulo %d do livro %d",
                chapter_index, book_id,
            )
        except Exception as e:
            logger.error("Erro no _trigger_play: %s", e)
        finally:
            db.close()

    @staticmethod
    def _fuzzy_find_book(query: str, books) -> "models.Book | None":
        """Busca fuzzy por título do livro."""
        query_normalized = _normalize(query)

        # Primeiro: match exato case-insensitive
        for book in books:
            if _normalize(book.title) == query_normalized:
                return book

        # Segundo: substring match
        for book in books:
            if query_normalized in _normalize(book.title):
                return book

        # Terceiro: fuzzy match com difflib
        titles = [_normalize(b.title) for b in books]
        matches = difflib.get_close_matches(query_normalized, titles, n=1, cutoff=0.5)
        if matches:
            for book in books:
                if _normalize(book.title) == matches[0]:
                    return book

        return None
