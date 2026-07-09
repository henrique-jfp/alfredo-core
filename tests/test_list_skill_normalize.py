"""
Testes para o fix de normalização de list_type no ListSkill —
evita que listas com tipo inventado pelo Gemini (ex: 'churrasco')
sumam silenciosamente do Dashboard.
"""
import sys
import os
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.brain.skills.list_skill import ListSkill


class TestListTypeNormalization(unittest.TestCase):

    def setUp(self):
        self.skill = ListSkill()

    def test_valid_types_pass_through_unchanged(self):
        self.assertEqual(self.skill._normalize_list_type("compras"), "compras")
        self.assertEqual(self.skill._normalize_list_type("tarefas"), "tarefas")

    def test_invalid_type_with_shopping_keyword_maps_to_compras(self):
        self.assertEqual(self.skill._normalize_list_type("churrasco de compras"), "compras")
        self.assertEqual(self.skill._normalize_list_type("mercado"), "compras")

    def test_invalid_type_without_keyword_falls_back_to_tarefas(self):
        self.assertEqual(self.skill._normalize_list_type("churrasco"), "tarefas")
        self.assertEqual(self.skill._normalize_list_type(""), "tarefas")
        self.assertEqual(self.skill._normalize_list_type(None), "tarefas")

    def test_case_insensitive(self):
        self.assertEqual(self.skill._normalize_list_type("COMPRAS"), "compras")
        self.assertEqual(self.skill._normalize_list_type("  Tarefas  "), "tarefas")


if __name__ == "__main__":
    unittest.main()