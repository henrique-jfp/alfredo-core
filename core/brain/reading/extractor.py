"""
Extrator de texto e metadados de PDFs e EPUBs.

Responsável pelo primeiro passo do pipeline de leitura interativa:
recebe um arquivo de ebook e extrai título, autor, e texto bruto
dividido por capítulos. Não faz anotação nem síntese — apenas extração.

Uso:
    from core.brain.reading.extractor import extract_book
    metadata = extract_book("/path/to/file.pdf")
    # metadata.title, metadata.author, metadata.chapters
"""
import os
import re
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("alfredo.reading.extractor")

# Limite de palavras por capítulo quando não há divisão natural.
# ~3000 palavras ≈ 5-6 minutos de áudio narrado.
WORDS_PER_CHAPTER = 3000


@dataclass
class ChapterData:
    """Dados brutos de um capítulo extraído."""
    index: int
    title: str | None
    text: str


@dataclass
class BookMetadata:
    """Metadados completos extraídos de um ebook."""
    title: str
    author: str | None
    chapters: list[ChapterData] = field(default_factory=list)


def extract_book(file_path: str) -> BookMetadata:
    """Extrai texto e metadados de um PDF ou EPUB.

    Args:
        file_path: Caminho absoluto do arquivo.

    Returns:
        BookMetadata com título, autor e capítulos.

    Raises:
        ValueError: Se o formato não for suportado.
    """
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        return _extract_pdf(file_path)
    elif ext == ".epub":
        return _extract_epub(file_path)
    else:
        raise ValueError(f"Formato não suportado: {ext}. Use .pdf ou .epub.")


def save_chapters_to_disk(
    book_id: int,
    chapters: list[ChapterData],
    base_dir: str = "data/library",
) -> list[str]:
    """Salva o texto de cada capítulo em disco.

    Args:
        book_id: ID do livro no banco de dados.
        chapters: Lista de capítulos extraídos.
        base_dir: Diretório base da biblioteca.

    Returns:
        Lista de caminhos relativos dos arquivos salvos.
    """
    chapter_dir = os.path.join(base_dir, str(book_id), "chapters")
    os.makedirs(chapter_dir, exist_ok=True)

    paths = []
    for ch in chapters:
        filename = f"{ch.index}.txt"
        filepath = os.path.join(chapter_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(ch.text)
        rel_path = os.path.join(str(book_id), "chapters", filename)
        paths.append(rel_path)
        logger.debug("Capítulo %d salvo em %s (%d chars)", ch.index, filepath, len(ch.text))

    return paths


# ── PDF ──────────────────────────────────────────────────────────────────────

# Padrões para detectar início de capítulo em PDFs sem estrutura
_CHAPTER_PATTERNS = [
    re.compile(r"^(?:cap[íi]tulo|chapter)\s+\d+", re.IGNORECASE),
    re.compile(r"^(?:cap[íi]tulo|chapter)\s+[IVXLCDM]+", re.IGNORECASE),
    re.compile(r"^PARTE\s+\d+", re.IGNORECASE),
]


def _extract_pdf(file_path: str) -> BookMetadata:
    """Extrai texto de PDF usando PyMuPDF (fitz)."""
    import fitz

    doc = fitz.open(file_path)
    metadata = doc.metadata or {}

    title = metadata.get("title", "") or Path(file_path).stem
    author = metadata.get("author", None)

    # Extrai texto de todas as páginas
    full_text = ""
    for page in doc:
        page_text = page.get_text() or ""
        full_text += page_text + "\n"

    full_text = full_text.strip()
    if not full_text:
        logger.warning("PDF vazio ou sem texto extraível: %s", file_path)
        return BookMetadata(title=title, author=author, chapters=[
            ChapterData(index=0, title="Conteúdo", text="(Conteúdo não extraível)")
        ])

    # Tenta dividir por padrões de capítulo
    chapters = _split_by_chapter_patterns(full_text)

    # Se não encontrou divisão natural, divide por número de palavras
    if len(chapters) <= 1:
        chapters = _split_by_word_count(full_text, WORDS_PER_CHAPTER)

    logger.info("PDF extraído: '%s' por %s — %d capítulo(s)", title, author, len(chapters))
    return BookMetadata(title=title, author=author, chapters=chapters)


def _split_by_chapter_patterns(text: str) -> list[ChapterData]:
    """Tenta dividir texto por padrões de início de capítulo."""
    lines = text.split("\n")
    split_points: list[tuple[int, str]] = []  # (line_index, title)

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        for pattern in _CHAPTER_PATTERNS:
            if pattern.match(stripped):
                split_points.append((i, stripped))
                break

    if not split_points:
        return [ChapterData(index=0, title=None, text=text)]

    chapters: list[ChapterData] = []
    for idx, (start_line, chapter_title) in enumerate(split_points):
        end_line = split_points[idx + 1][0] if idx + 1 < len(split_points) else len(lines)
        chapter_text = "\n".join(lines[start_line:end_line]).strip()
        
        if chapter_text:
            # Se o texto for muito curto (ex: linha de sumário) e já existir um capítulo,
            # mescla este texto no capítulo anterior em vez de criar um novo.
            if len(chapter_text) < 500 and chapters:
                chapters[-1].text += "\n\n" + chapter_text
            else:
                chapters.append(ChapterData(
                    index=len(chapters),
                    title=chapter_title,
                    text=chapter_text,
                ))

    return chapters if chapters else [ChapterData(index=0, title=None, text=text)]


def _split_by_word_count(text: str, max_words: int) -> list[ChapterData]:
    """Divide texto em blocos de ~max_words palavras, quebrando em parágrafos."""
    paragraphs = re.split(r"\n\s*\n", text)
    chapters: list[ChapterData] = []
    current_text = ""
    current_words = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        para_words = len(para.split())
        if current_words + para_words > max_words and current_text:
            chapters.append(ChapterData(
                index=len(chapters),
                title=f"Parte {len(chapters) + 1}",
                text=current_text.strip(),
            ))
            current_text = para + "\n\n"
            current_words = para_words
        else:
            current_text += para + "\n\n"
            current_words += para_words

    if current_text.strip():
        chapters.append(ChapterData(
            index=len(chapters),
            title=f"Parte {len(chapters) + 1}" if len(chapters) > 0 else None,
            text=current_text.strip(),
        ))

    return chapters if chapters else [ChapterData(index=0, title=None, text=text)]


# ── EPUB ─────────────────────────────────────────────────────────────────────

# Palavras-chave que indicam front matter (dedicatória, prefácio, etc.)
# em português e inglês — itens cujo título contém estes termos serão pulados.
_FRONT_MATTER_KEYWORDS = (
    "dedicatór", "agradecimento", "prefácio", "prefacio", "apresentação",
    "apresentacao", "nota do autor", "nota do tradutor", "introdução",
    "introducao", "sobre o autor", "copyright", "créditos", "creditos",
    "índice", "indice", "sumário", "sumario",
    # Inglês
    "dedication", "acknowledgment", "acknowledgement", "foreword",
    "preface", "introduction", "about the author", "copyright",
    "table of contents", "prologue", "prelude",
)

# Palavras no texto que indicam front matter (mesmo sem título explícito)
_FRONT_MATTER_TEXT_PATTERNS = (
    "todos os direitos reservados",
    "all rights reserved",
    "nenhuma parte desta publicação",
    "no part of this publication",
    "este livro foi publicado",
    "this book was published",
    "dedico este livro",
    "para meus pais",
    "com amor para",
    "obra publicada originalmente",
    "originally published",
    "edição",
    "ediçao",
    "publicado no brasil",
    "published in brazil",
    "isbn",
)


def _is_front_matter(item, soup, text: str, chapter_title: str | None) -> bool:
    """Verifica se um item do EPUB é front matter (deve ser ignorado).

    Checa nome do arquivo, título do capítulo e conteúdo textual.
    """
    # 1. Nome do arquivo ou href
    href = getattr(item, "file_name", "") or ""
    href_lower = href.lower()
    front_file_patterns = (
        "dedication", "copyright", "title_page", "titlepage",
        "foreword", "preface", "introduction", "about",
        "acknowledgment", "colophon", "toc", "contents",
    )
    for pat in front_file_patterns:
        if pat in href_lower:
            return True

    # 2. Título do capítulo
    if chapter_title:
        title_lower = chapter_title.lower().strip()
        for kw in _FRONT_MATTER_KEYWORDS:
            if title_lower.startswith(kw):
                return True

    # 3. Texto curto (menos de 80 palavras) COM padrão de front matter
    word_count = len(text.split())
    if word_count < 80:
        # Se for curto e não tem um título claro de capítulo, é suspeito
        if not chapter_title:
            return True

    # 4. Conteúdo textual: verifica padrões de front matter nas primeiras linhas
    first_lines = "\n".join(text.split("\n")[:10]).lower()
    for pat in _FRONT_MATTER_TEXT_PATTERNS:
        if pat in first_lines:
            return True

    return False


def _extract_epub(file_path: str) -> BookMetadata:
    """Extrai texto de EPUB usando ebooklib + BeautifulSoup."""
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup

    book = epub.read_epub(file_path, options={"ignore_ncx": True})

    title = book.get_metadata("DC", "title")
    title = title[0][0] if title else Path(file_path).stem

    author = book.get_metadata("DC", "creator")
    author = author[0][0] if author else None

    raw_chapters: list[ChapterData] = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        content = item.get_content().decode("utf-8", errors="replace")
        soup = BeautifulSoup(content, "html.parser")
        text = soup.get_text(separator="\n", strip=True)

        # Ignora itens muito curtos (capa, copyright, etc.)
        word_count = len(text.split())
        if word_count < 50:
            continue

        # Tenta extrair título do capítulo do HTML
        chapter_title = None
        for tag in ("h1", "h2", "h3"):
            heading = soup.find(tag)
            if heading:
                chapter_title = heading.get_text(strip=True)
                break

        # Pula front matter (dedicatória, prefácio, copyright, etc.)
        item_name = getattr(item, "file_name", "") or item.get_name() or ""
        if _is_front_matter(item, soup, text, chapter_title):
            logger.debug("Pulando front matter: %s (%s)", chapter_title or "(sem título)", item_name)
            continue

        raw_chapters.append(ChapterData(
            index=len(raw_chapters),
            title=chapter_title,
            text=text,
        ))

    if not raw_chapters:
        logger.warning("EPUB sem capítulos extraíveis: %s", file_path)
        raw_chapters = [ChapterData(index=0, title="Conteúdo", text="(Conteúdo não extraível)")]

    # Se capítulos forem muito grandes, subdivide
    final_chapters: list[ChapterData] = []
    for ch in raw_chapters:
        word_count = len(ch.text.split())
        if word_count > WORDS_PER_CHAPTER * 2:
            sub_chapters = _split_by_word_count(ch.text, WORDS_PER_CHAPTER)
            for sub in sub_chapters:
                sub.index = len(final_chapters)
                sub.title = f"{ch.title} ({sub.index + 1})" if ch.title else sub.title
                final_chapters.append(sub)
        else:
            ch.index = len(final_chapters)
            final_chapters.append(ch)

    logger.info("EPUB extraído: '%s' por %s — %d capítulo(s)", title, author, len(final_chapters))
    return BookMetadata(title=title, author=author, chapters=final_chapters)
