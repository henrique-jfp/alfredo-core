import unittest
from unittest.mock import patch, MagicMock

from core.brain.skills.media_skill import MediaSkill, resolve_intent
from core.services.media_service import get_genre_id


class TestMediaSkillRecommendation(unittest.TestCase):
    def setUp(self):
        self.skill = MediaSkill()

    @patch('core.services.media_service.discover_media')
    def test_enrich_response_with_synopsis_and_where_to_watch(self, mock_discover):
        """Verifica que o direct_response inclui título, nota, sinopse e onde assistir."""
        mock_discover.return_value = {
            "results": [
                {
                    "title": "Inception",
                    "rating": 8.8,
                    "synopsis": "Um ladrão que entra nos sonhos das pessoas para roubar segredos.",
                    "where_to_watch": "Netflix"
                },
                {
                    "title": "The Matrix",
                    "rating": 8.3,
                    "synopsis": "Um hacker descobre a verdade sobre a realidade simulada.",
                    "where_to_watch": "Netflix"
                }
            ]
        }

        result = self.skill.execute_tool(
            {"media_type": "movie", "genre": "ficção científica", "decade_or_year": "1990"},
            {}
        )

        self.assertIn("direct_response", result)
        response = result["direct_response"]
        self.assertIn("Inception - Nota: 8.8", response)
        self.assertIn("Sinopse: Um ladrão que entra nos sonhos das pessoas para roubar segredos.", response)
        self.assertIn("Onde assistir: Netflix", response)
        self.assertIn("The Matrix", response)
        self.assertIn("Nota: 8.3", response)

    @patch('core.services.media_service.discover_media')
    def test_fallback_to_overview_when_no_synopsis(self, mock_discover):
        """Verifica que overview é usado como fallback quando synopsis não existe."""
        mock_discover.return_value = {
            "results": [
                {
                    "title": "Dune",
                    "rating": 7.9,
                    "overview": "Uma saga épica de deserto e poder.",
                    "where_to_watch": "HBO Max"
                }
            ]
        }

        result = self.skill.execute_tool({"media_type": "movie", "genre": "ficção científica"}, {})

        self.assertIn("direct_response", result)
        self.assertIn("Sinopse: Uma saga épica de deserto e poder.", result["direct_response"])

    @patch('core.services.media_service.discover_media')
    def test_where_to_watch_fallback_when_empty(self, mock_discover):
        """Verifica o fallback quando nenhuma plataforma de streaming é encontrada."""
        mock_discover.return_value = {
            "results": [
                {
                    "title": "Filme Raro",
                    "rating": 6.5,
                    "synopsis": "Um filme difícil de encontrar.",
                    "where_to_watch": ""
                }
            ]
        }

        result = self.skill.execute_tool({"media_type": "movie"}, {})

        self.assertIn("direct_response", result)
        # where_to_watch vazio → fallback para "Não informado"
        self.assertIn("Onde assistir: Não informado", result["direct_response"])

    @patch('core.services.media_service.discover_media')
    def test_empty_results_returns_message(self, mock_discover):
        """Verifica que nenhum resultado retorna mensagem adequada."""
        mock_discover.return_value = {"message": "Nenhum resultado encontrado para os filtros."}

        result = self.skill.execute_tool({"media_type": "movie", "genre": "action"}, {})

        self.assertIn("direct_response", result)
        self.assertEqual(result["direct_response"], "Nenhum resultado encontrado para os filtros.")

    @patch('core.services.media_service.discover_media')
    def test_api_error_returns_error_key(self, mock_discover):
        """Verifica que erros de API são propagados corretamente."""
        mock_discover.side_effect = Exception("Connection timeout")

        result = self.skill.execute_tool({"media_type": "movie"}, {})

        self.assertIn("error", result)
        self.assertIn("Connection timeout", result["error"])


class TestResolveIntent(unittest.TestCase):
    """Testa a função resolve_intent com diferentes temas em PT-BR."""

    def test_western_theme(self):
        media_type, genre, year = resolve_intent("quero um faroeste clássico")
        self.assertEqual(media_type, "movie")
        self.assertEqual(genre, "western")
        self.assertIsNone(year)

    def test_horror_theme(self):
        media_type, genre, year = resolve_intent("me indica um filme de terror")
        self.assertEqual(media_type, "movie")
        self.assertEqual(genre, "horror")

    def test_comedy_theme(self):
        media_type, genre, year = resolve_intent("quero uma comédia boa")
        self.assertEqual(media_type, "movie")
        self.assertEqual(genre, "comedy")

    def test_comedy_no_accent(self):
        media_type, genre, year = resolve_intent("quero uma comedia")
        self.assertEqual(genre, "comedy")

    def test_sci_fi_theme(self):
        media_type, genre, year = resolve_intent("quero ficção científica")
        self.assertEqual(genre, "science fiction")

    def test_romance_theme(self):
        media_type, genre, year = resolve_intent("um filme romântico por favor")
        self.assertEqual(genre, "romance")

    def test_action_theme(self):
        media_type, genre, year = resolve_intent("filme de ação")
        self.assertEqual(genre, "action")

    def test_animation_desenho(self):
        media_type, genre, year = resolve_intent("quero um desenho animado")
        self.assertEqual(genre, "animation")

    def test_crime_policial(self):
        media_type, genre, year = resolve_intent("série policial boa")
        self.assertEqual(genre, "crime")

    def test_war_theme(self):
        media_type, genre, year = resolve_intent("algum filme de guerra")
        self.assertEqual(genre, "war")

    def test_decade_extraction(self):
        """Verifica extração de década nos anos 80."""
        media_type, genre, year = resolve_intent("um filme de ação dos anos 80")
        self.assertEqual(genre, "action")
        self.assertIsNotNone(year)
        self.assertIn("80", year)

    def test_specific_year_extraction(self):
        """Verifica extração de ano específico."""
        media_type, genre, year = resolve_intent("terror de 1994")
        self.assertEqual(genre, "horror")
        self.assertEqual(year, "1994")

    def test_serie_media_type(self):
        """Verifica que 'série' mapeia para tv_series."""
        media_type, genre, year = resolve_intent("quero uma série boa")
        self.assertEqual(media_type, "tv_series")

    def test_documentary_media_type(self):
        """Verifica que 'documentário' mapeia para tv_series."""
        media_type, genre, _ = resolve_intent("me indica um documentário")
        self.assertEqual(media_type, "tv_series")
        self.assertEqual(genre, "documentary")

    def test_generic_fallback(self):
        """Verifica fallback quando nenhum tema é reconhecido."""
        media_type, genre, year = resolve_intent("alguma coisa legal para ver")
        self.assertEqual(media_type, "movie")
        self.assertEqual(genre, "any")
        self.assertIsNone(year)


class TestGetGenreId(unittest.TestCase):
    """Testa get_genre_id sem depender de API key (usa mapa estático)."""

    def test_action_from_static_map(self):
        self.assertEqual(get_genre_id("action"), 28)

    def test_comedy_from_static_map(self):
        self.assertEqual(get_genre_id("comedy"), 35)

    def test_horror_from_static_map(self):
        self.assertEqual(get_genre_id("horror"), 27)

    def test_western_from_static_map(self):
        self.assertEqual(get_genre_id("western"), 37)

    def test_animation_from_static_map(self):
        self.assertEqual(get_genre_id("animation"), 16)

    def test_crime_from_static_map(self):
        self.assertEqual(get_genre_id("crime"), 80)

    def test_fantasy_from_static_map(self):
        self.assertEqual(get_genre_id("fantasy"), 14)

    def test_music_from_static_map(self):
        self.assertEqual(get_genre_id("music"), 10402)

    def test_science_fiction_from_static_map(self):
        self.assertEqual(get_genre_id("science fiction"), 878)

    def test_none_for_unknown_genre_without_api_key(self):
        """Sem API key e gênero desconhecido → None."""
        with patch('core.services.media_service.TMDB_API_KEY', None):
            result = get_genre_id("genero_inexistente")
        self.assertIsNone(result)

    def test_none_for_empty_genre(self):
        self.assertIsNone(get_genre_id(""))

    def test_none_for_none_genre(self):
        self.assertIsNone(get_genre_id(None))

    def test_case_insensitive(self):
        """Verifica que a busca é case-insensitive."""
        self.assertEqual(get_genre_id("ACTION"), 28)
        self.assertEqual(get_genre_id("Comedy"), 35)


if __name__ == '__main__':
    unittest.main()