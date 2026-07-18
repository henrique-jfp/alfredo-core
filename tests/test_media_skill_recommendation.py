import unittest
from unittest.mock import patch, MagicMock

from core.brain.skills.media_skill import MediaSkill

class TestMediaSkillRecommendation(unittest.TestCase):
    def setUp(self):
        self.skill = MediaSkill()

    @patch('core.services.media_service.discover_media')
    def test_enrich_response_with_synopsis_and_where_to_watch(self, mock_discover):
        # Mock response from discover_media
        mock_result = {
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
        mock_discover.return_value = mock_result

        kwargs = {
            "media_type": "movie",
            "genre": "ficção científica",
            "decade_or_year": "1990"
        }
        context = {}

        result = self.skill.execute_tool(kwargs, context)

        # Verify that direct_response was set and contains expected fields
        self.assertIn("direct_response", result)
        response = result["direct_response"]
        self.assertIn("Inception - Nota: 8.8", response)
        self.assertIn("Sinopse: Um ladrão que entra nos sonhos das pessoas para roubar segredos.", response)
        self.assertIn("Onde assistir: Netflix", response)

        # Verify that both movies are included
        self.assertIn("The Matrix", response)
        self.assertIn("Nota: 8.3", response)

if __name__ == '__main__':
    unittest.main()