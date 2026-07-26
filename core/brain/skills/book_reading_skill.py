"""
Skill de leitura de livros para o Alfredo.

Reconhece intenções de voz como "leia o Senhor dos Anéis", "continua a
leitura", "para de ler" e interage com a biblioteca de ebooks.

Segue o padrão de Skill existente: name, can_handle, execute, execute_tool.
Registrada no AgentRouter como "manage_book_reading".
"""
import difflib
import json
import logging
import unicodedata
from typing import Any, Dict

from core.brain.skills.base import Skill

logger = logging.getLogger("alfredo.skills.book_reading")


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

        # Dispara a leitura
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(self._trigger_play(book_id, chapter_index, room_id))
        except Exception as e:
            logger.error("Erro ao retomar leitura: %s", e)

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

    async def _trigger_play(self, book_id: int, chapter_index: int, room_id: str):
        """Dispara a preparação e streaming do áudio em background."""
        from core.brain.memory.database import SessionLocal
        from core.brain.memory import models
        from core.api.library import _ensure_chapter_ready, _stream_audio_to_satellite

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
            if chapter:
                audio_path = await _ensure_chapter_ready(chapter, db)
                await _stream_audio_to_satellite(room_id, audio_path, db)
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


def _normalize(text: str) -> str:
    """Normaliza texto para comparação fuzzy: remove acentos, lowercase."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()
