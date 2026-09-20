import unittest
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image

import utils.classifier as classifier
import utils.llm_helper as llm


class GeminiFallbackTests(unittest.TestCase):
    def test_gemini_vision_retries_supported_models(self):
        calls = []

        class FakeModel:
            def __init__(self, name):
                calls.append(name)
                if name == "gemini-3.5-flash":
                    raise RuntimeError("unsupported model")

            def generate_content(self, prompt):
                return SimpleNamespace(text='{"category":"Other","urgency":"Low","is_valid_complaint":true}')

        fake_genai = SimpleNamespace(
            configure=lambda api_key: None,
            GenerativeModel=lambda name: FakeModel(name),
        )

        with patch.object(llm, "GOOGLE_API_KEY", "test-key"):
            with patch.dict("sys.modules", {"google.generativeai": fake_genai}):
                result = llm._try_gemini_vision("prompt", "image")

        self.assertEqual(result, '{"category":"Other","urgency":"Low","is_valid_complaint":true}')
        self.assertIn("gemini-3.5-flash", calls)
        self.assertIn("gemini-3.6-flash", calls)

    def test_fire_image_falls_back_to_hazard_classification(self):
        image = Image.new("RGB", (64, 64), (255, 80, 0))
        result = classifier._heuristic_image_classify(image)
        self.assertEqual(result["category"], "Public Safety")
        self.assertEqual(result["urgency"], "High")
        self.assertTrue(result["is_valid_complaint"])

    def test_neutral_image_is_invalid(self):
        image = Image.new("RGB", (64, 64), (240, 240, 240))
        result = classifier._heuristic_image_classify(image)
        self.assertEqual(result["category"], "Other")
        self.assertFalse(result["is_valid_complaint"])


if __name__ == "__main__":
    unittest.main()
