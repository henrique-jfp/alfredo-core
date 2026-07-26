"""
API REST para a biblioteca de ebooks do Alfredo Reads.

Endpoints:
    POST   /api/library/books          — Upload de PDF/EPUB
    GET    /api/library/books           — Lista/busca livros
    GET    /api/library/books/{id}      — Detalhes + capítulos
    DELETE /api/library/books/{id}      — Remove livro e arquivos
    POST   /api/library/books/{id}/play — Inicia leitura em um cômodo
    POST   /api/library/books/{id}/pause  — Pausa leitura
    POST   /api/library/books/{id}/resume — Retoma leitura
"""
import asyncio
import json
import logging
import os
import shutil
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.brain.memory import models
from core.brain.memory.database import get_db, SessionLocal

logger = logging.getLogger("alfredo.library")

router = APIRouter(prefix="/api/library", tags=["Library"])

# Diretório base para armazenamento de ebooks
LIBRARY_DIR = os.path.join(os.getcwd(), "data", "library")
UPLOAD_DIR = os.path.join(LIBRARY_DIR, "uploads")


# ── Schemas Pydantic ─────────────────────────────────────────────────────────

class PlayRequest(BaseModel):
    room_id: str
    chapter_index: int = 0

class RoomRequest(BaseModel):
    room_id: str


# ── Upload ───────────────────────────────────────────────────────────────────

@router.post("/books")
async def upload_book(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload de PDF/EPUB. Extrai texto e metadados, cria Book + BookChapters."""
    if not file.filename:
        raise HTTPException(400, "Arquivo sem nome")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".pdf", ".epub"):
        raise HTTPException(400, f"Formato não suportado: {ext}. Use .pdf ou .epub.")

    # Salva o arquivo em disco
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    upload_path = os.path.join(UPLOAD_DIR, file.filename)
    content = await file.read()
    with open(upload_path, "wb") as f:
        f.write(content)

    logger.info("Arquivo recebido: %s (%d bytes)", file.filename, len(content))

    try:
        from core.brain.reading.extractor import extract_book, save_chapters_to_disk

        metadata = extract_book(upload_path)

        # Cria o registro do livro
        book = models.Book(
            title=metadata.title,
            author=metadata.author,
            source_filename=file.filename,
            format=ext.lstrip("."),
            total_chapters=len(metadata.chapters),
        )
        db.add(book)
        db.flush()  # Gera o ID

        # Salva texto dos capítulos em disco
        text_paths = save_chapters_to_disk(book.id, metadata.chapters, LIBRARY_DIR)

        # Cria registros dos capítulos
        for ch, text_path in zip(metadata.chapters, text_paths):
            chapter = models.BookChapter(
                book_id=book.id,
                index=ch.index,
                title=ch.title,
                raw_text_path=text_path,
            )
            db.add(chapter)

        db.commit()
        db.refresh(book)

        logger.info("Livro criado: id=%d, '%s', %d capítulos", book.id, book.title, book.total_chapters)

        return {
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "format": book.format,
            "total_chapters": book.total_chapters,
            "source_filename": book.source_filename,
        }

    except Exception as e:
        logger.error("Erro ao processar upload: %s", e)
        # Limpa arquivo em caso de erro
        if os.path.exists(upload_path):
            os.remove(upload_path)
        raise HTTPException(500, f"Erro ao processar ebook: {e}")


# ── Listagem e Busca ─────────────────────────────────────────────────────────

@router.get("/books")
def list_books(q: Optional[str] = None, db: Session = Depends(get_db)):
    """Lista livros da biblioteca, com busca opcional por título/autor."""
    query = db.query(models.Book).order_by(models.Book.added_at.desc())
    if q:
        search = f"%{q}%"
        query = query.filter(
            models.Book.title.ilike(search) | models.Book.author.ilike(search)
        )
    books = query.all()
    return [
        {
            "id": b.id,
            "title": b.title,
            "author": b.author,
            "added_at": b.added_at.isoformat() if b.added_at else None,
            "source_filename": b.source_filename,
            "format": b.format,
            "total_chapters": b.total_chapters,
            "cover_path": b.cover_path,
        }
        for b in books
    ]


@router.get("/books/{book_id}")
def get_book(book_id: int, db: Session = Depends(get_db)):
    """Detalhes de um livro + lista de capítulos com status."""
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(404, "Livro não encontrado")

    chapters = (
        db.query(models.BookChapter)
        .filter(models.BookChapter.book_id == book_id)
        .order_by(models.BookChapter.index)
        .all()
    )

    return {
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "added_at": book.added_at.isoformat() if book.added_at else None,
        "source_filename": book.source_filename,
        "format": book.format,
        "total_chapters": book.total_chapters,
        "cover_path": book.cover_path,
        "chapters": [
            {
                "id": ch.id,
                "book_id": ch.book_id,
                "index": ch.index,
                "title": ch.title,
                "has_annotation": ch.annotation_json is not None,
                "has_audio": ch.audio_path is not None,
            }
            for ch in chapters
        ],
    }


# ── Remoção ──────────────────────────────────────────────────────────────────

@router.delete("/books/{book_id}")
def delete_book(book_id: int, db: Session = Depends(get_db)):
    """Remove livro, capítulos, e todos os arquivos associados."""
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(404, "Livro não encontrado")

    # Remove arquivos do disco
    book_dir = os.path.join(LIBRARY_DIR, str(book_id))
    if os.path.exists(book_dir):
        shutil.rmtree(book_dir, ignore_errors=True)

    # Remove do banco (cascade deleta capítulos)
    db.delete(book)
    db.commit()

    logger.info("Livro removido: id=%d, '%s'", book_id, book.title)
    return {"status": "deleted"}


# ── Reprodução ───────────────────────────────────────────────────────────────

@router.post("/books/{book_id}/play")
async def play_book(book_id: int, req: PlayRequest, db: Session = Depends(get_db)):
    """Inicia a leitura de um capítulo em um cômodo.

    Garante que o capítulo esteja anotado e sintetizado antes de tocar.
    Inicia anotação/síntese do próximo capítulo em background.
    """
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(404, "Livro não encontrado")

    chapter = (
        db.query(models.BookChapter)
        .filter(
            models.BookChapter.book_id == book_id,
            models.BookChapter.index == req.chapter_index,
        )
        .first()
    )
    if not chapter:
        raise HTTPException(404, f"Capítulo {req.chapter_index} não encontrado")

    # Garante anotação e síntese
    audio_path = await _ensure_chapter_ready(chapter, db)

    # Salva estado da sessão
    _update_session(db, req.room_id, book_id, req.chapter_index, "playing")

    # Envia áudio para o satélite
    asyncio.create_task(_stream_audio_to_satellite(req.room_id, audio_path, db))

    # Pré-processa o próximo capítulo em background
    next_index = req.chapter_index + 1
    if next_index < book.total_chapters:
        asyncio.create_task(_preprocess_next_chapter(book_id, next_index))

    return {
        "status": "playing",
        "book_id": book_id,
        "chapter_index": req.chapter_index,
        "chapter_title": chapter.title,
    }


@router.post("/books/{book_id}/pause")
def pause_book(book_id: int, req: RoomRequest, db: Session = Depends(get_db)):
    """Pausa a leitura no cômodo."""
    session = (
        db.query(models.SessionState)
        .filter(models.SessionState.room_id == req.room_id)
        .first()
    )
    if session and session.skill_name == "manage_book_reading":
        state = json.loads(session.state_data) if session.state_data else {}
        state["status"] = "paused"
        session.state_data = json.dumps(state)
        db.commit()

    # Enviar comando de parar áudio para o satélite
    asyncio.create_task(_send_stop_to_satellite(req.room_id))

    return {"status": "paused"}


@router.post("/books/{book_id}/resume")
async def resume_book(book_id: int, req: RoomRequest, db: Session = Depends(get_db)):
    """Retoma a leitura de onde parou."""
    session = (
        db.query(models.SessionState)
        .filter(models.SessionState.room_id == req.room_id)
        .first()
    )
    if not session or session.skill_name != "manage_book_reading":
        raise HTTPException(400, "Nenhuma leitura ativa neste cômodo")

    state = json.loads(session.state_data) if session.state_data else {}
    chapter_index = state.get("chapter_index", 0)

    chapter = (
        db.query(models.BookChapter)
        .filter(
            models.BookChapter.book_id == book_id,
            models.BookChapter.index == chapter_index,
        )
        .first()
    )
    if not chapter:
        raise HTTPException(404, f"Capítulo {chapter_index} não encontrado")

    audio_path = await _ensure_chapter_ready(chapter, db)
    state["status"] = "playing"
    session.state_data = json.dumps(state)
    db.commit()

    asyncio.create_task(_stream_audio_to_satellite(req.room_id, audio_path, db))

    return {"status": "playing", "chapter_index": chapter_index}


# ── Helpers internos ─────────────────────────────────────────────────────────

async def _ensure_chapter_ready(chapter: models.BookChapter, db: Session) -> str:
    """Garante que o capítulo está anotado e sintetizado. Retorna o audio_path."""
    from core.brain.reading.annotator import annotate_chapter, segments_to_json, segments_from_json
    from core.brain.reading.synthesizer import synthesize_chapter

    # 1. Anotação (se necessário)
    if chapter.annotation_json is None:
        text_path = os.path.join(LIBRARY_DIR, chapter.raw_text_path) if chapter.raw_text_path else None
        if text_path and os.path.exists(text_path):
            with open(text_path, "r", encoding="utf-8") as f:
                chapter_text = f.read()
        else:
            logger.warning("Texto do capítulo %d não encontrado", chapter.index)
            chapter_text = "(Texto não disponível)"

        logger.info("Anotando capítulo %d do livro %d...", chapter.index, chapter.book_id)
        segments = annotate_chapter(chapter_text)
        chapter.annotation_json = segments_to_json(segments)
        db.commit()
    else:
        segments = segments_from_json(chapter.annotation_json)

    # 2. Síntese (se necessário)
    if chapter.audio_path is None or not os.path.exists(
        os.path.join(LIBRARY_DIR, "..", chapter.audio_path) if chapter.audio_path else ""
    ):
        logger.info("Sintetizando capítulo %d do livro %d...", chapter.index, chapter.book_id)
        audio_path = await synthesize_chapter(chapter.book_id, chapter.index, segments)
        chapter.audio_path = audio_path
        db.commit()
    else:
        audio_path = chapter.audio_path

    return audio_path


async def _preprocess_next_chapter(book_id: int, chapter_index: int):
    """Pré-processa o próximo capítulo em background (anotação + síntese)."""
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
        if chapter and chapter.audio_path is None:
            logger.info("Pré-processando capítulo %d do livro %d em background...", chapter_index, book_id)
            await _ensure_chapter_ready(chapter, db)
    except Exception as e:
        logger.error("Erro no pré-processamento do capítulo %d: %s", chapter_index, e)
    finally:
        db.close()


async def _stream_audio_to_satellite(room_id: str, audio_path: str, db: Session):
    """Envia o arquivo de áudio para o satélite do cômodo via WebSocket."""
    from core.api.satellite import manager

    # Encontra o device_id ativo neste room
    device = db.query(models.Device).filter(models.Device.room_id == room_id).first()
    if not device:
        logger.warning("Nenhum device encontrado para room_id=%s", room_id)
        return

    ws = manager.active_satellites.get(device.device_id)
    if not ws:
        logger.warning("Satélite %s não está online", device.device_id)
        return

    try:
        if not os.path.exists(audio_path):
            logger.error("Arquivo de áudio não encontrado: %s", audio_path)
            return

        file_size = os.path.getsize(audio_path)
        logger.info("Streaming %d bytes para %s (%s)...", file_size, device.device_id, room_id)

        # Lê e envia em chunks de 8KB (mesmo padrão do TTS streaming)
        total_sent = 0
        import time
        t_start = time.time()

        with open(audio_path, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                await ws.send_bytes(chunk)
                total_sent += len(chunk)

        # Calcula delay (48kbps = 6000 bytes/s)
        expected_duration = total_sent / 6000.0
        elapsed = time.time() - t_start
        delay = expected_duration - elapsed + 0.5

        if delay > 0:
            logger.info(
                "[BOOK AUDIO] bytes=%d, dur=%.1fs, delay=%.1fs",
                total_sent, expected_duration, delay,
            )
            await asyncio.sleep(delay)

        # Sinaliza fim do áudio
        await ws.send_text(json.dumps({"type": "tts_end"}))
        logger.info("Áudio do livro enviado com sucesso para %s", device.device_id)

    except Exception as e:
        logger.error("Erro ao enviar áudio para %s: %s", device.device_id, e)


async def _send_stop_to_satellite(room_id: str):
    """Envia comando de parar áudio para o satélite."""
    from core.api.satellite import manager

    db = SessionLocal()
    try:
        device = db.query(models.Device).filter(models.Device.room_id == room_id).first()
        if device:
            await manager.send_command_to_satellite(device.device_id, "tts_end")
    except Exception as e:
        logger.error("Erro ao enviar stop para %s: %s", room_id, e)
    finally:
        db.close()


def _update_session(db: Session, room_id: str, book_id: int, chapter_index: int, status: str):
    """Cria ou atualiza o SessionState para a leitura do livro."""
    from datetime import datetime, timezone

    existing = (
        db.query(models.SessionState)
        .filter(models.SessionState.room_id == room_id)
        .first()
    )

    state_data = json.dumps({
        "book_id": book_id,
        "chapter_index": chapter_index,
        "status": status,
    })

    if existing:
        existing.skill_name = "manage_book_reading"
        existing.state_data = state_data
        existing.updated_at = datetime.now(timezone.utc)
    else:
        new_session = models.SessionState(
            room_id=room_id,
            skill_name="manage_book_reading",
            state_data=state_data,
        )
        db.add(new_session)

    db.commit()
