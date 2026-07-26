"""
Testes para o filtro de front matter do extrator de EPUB.

Verifica se páginas de dedicatória, copyright, prefácio etc. são
corretamente ignoradas durante a extração de capítulos.
"""
import pytest
from core.brain.reading.extractor import _is_front_matter


class FakeItem:
    """Simula um item de documento do EPUB (ebooklib.ITEM_DOCUMENT)."""
    def __init__(self, file_name: str = ""):
        self.file_name = file_name

    def get_name(self) -> str:
        return self.file_name


class FakeSoup:
    """Simula uma BeautifulSoup tag mínima."""
    def __init__(self, title: str = ""):
        self._title = title

    def find(self, tag: str):
        if self._title:
            return type("FakeTag", (), {"get_text": lambda self, strip=True: self._title})()
        return None


# ── Front matter detectável por nome de arquivo ──────────────────────────────

@pytest.mark.parametrize("filename,title,text", [
    ("dedication.xhtml", "", "À minha família, com amor e gratidão..."),
    ("copyright.xhtml", "", "Todos os direitos reservados..."),
    ("title_page.xhtml", "", "O Senhor dos Anéis"),
    ("foreword.xhtml", "", "É com grande prazer que apresento..."),
    ("preface.xhtml", "", "Este livro nasceu de uma conversa..."),
    ("introduction.xhtml", "", "Nesta introdução, exploraremos..."),
    ("acknowledgments.xhtml", "", "Gostaria de agradecer a todos..."),
])
def test_front_matter_by_filename(filename, title, text):
    """Itens com nomes de arquivo suspeitos devem ser identificados."""
    item = FakeItem(file_name=filename)
    soup = FakeSoup(title=title)
    assert _is_front_matter(item, soup, text, title or None), (
        f"{filename} deveria ser front matter"
    )


# ── Front matter detectável por título ───────────────────────────────────────

@pytest.mark.parametrize("filename,title,text", [
    ("chapter01.xhtml", "Dedicatória", "Dedico este livro a todos os meus amigos..."),
    ("chapter02.xhtml", "Agradecimentos", "Agradeço profundamente a..."),
    ("chapter03.xhtml", "Prefácio", "Este prefácio foi escrito por..."),
    ("chapter04.xhtml", "Introdução", "Bem-vindo a esta introdução..."),
    ("chapter05.xhtml", "Nota do Autor", "Uma nota sobre o processo criativo..."),
])
def test_front_matter_by_title(filename, title, text):
    """Itens com título de front matter devem ser identificados."""
    item = FakeItem(file_name=filename)
    soup = FakeSoup(title=title)
    assert _is_front_matter(item, soup, text, title), (
        f"'{title}' deveria ser front matter"
    )


# ── Conteúdo que NÃO é front matter ──────────────────────────────────────────

@pytest.mark.parametrize("filename,title,text", [
    ("chapter01.xhtml", "Capítulo 1", "Era uma vez, em uma terra distante..."),
    ("chapter02.xhtml", "O Despertar", "Ela abriu os olhos lentamente..."),
    ("part1.xhtml", "", "Começa aqui a primeira parte da jornada... (texto com mais de oitenta palavras para passar no filtro de comprimento mínimo) " + "palavra " * 80),
    ("ch01.xhtml", "O Condenado", "Numa noite fria de outono, o vento uivava..."),
])
def test_not_front_matter(filename, title, text):
    """Itens com conteúdo de capítulo NÃO devem ser identificados como front matter."""
    item = FakeItem(file_name=filename)
    soup = FakeSoup(title=title)
    assert not _is_front_matter(item, soup, text, title or None), (
        f"'{title or filename}' NÃO deveria ser front matter"
    )


# ── Texto curto sem título = front matter ────────────────────────────────────

def test_short_text_without_title_is_front_matter():
    """Texto com menos de 80 palavras e sem título deve ser front matter."""
    item = FakeItem(file_name="unknown.xhtml")
    soup = FakeSoup(title="")
    text = "Texto curto sem título com menos de oitenta palavras."
    assert _is_front_matter(item, soup, text, None), (
        "Texto curto sem título deveria ser front matter"
    )


# ── Texto contendo padrões de copyright ──────────────────────────────────────

def test_copyright_pattern_in_text():
    """Texto contendo 'todos os direitos reservados' deve ser front matter."""
    item = FakeItem(file_name="page007.xhtml")
    soup = FakeSoup(title="")
    text = """Copyright © 2024 por John Doe.\nTodos os direitos reservados.\nNenhuma parte desta publicação pode ser reproduzida..."""
    assert _is_front_matter(item, soup, text, None), (
        "Texto com cláusula de copyright deveria ser front matter"
    )


# ── Capítulo real com bastante texto ─────────────────────────────────────────

def test_long_chapter_not_front_matter():
    """Capítulo longo com título claro NÃO deve ser front matter."""
    item = FakeItem(file_name="capitulo01.xhtml")
    soup = FakeSoup(title="Capítulo 1 — O Começo")
    text = " ".join(["palavra"] * 200)  # 200 palavras
    assert not _is_front_matter(item, soup, text, "Capítulo 1 — O Começo"), (
        "Capítulo longo com título de capítulo não deveria ser front matter"
    )
