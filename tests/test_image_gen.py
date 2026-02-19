# Tests for ImageGenerateTool

import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from pocketpaw.tools.builtin.image_gen import ImageGenerateTool


@pytest.fixture
def tool():
    return ImageGenerateTool()


class TestImageGenerateTool:
    def test_name(self, tool):
        assert tool.name == "image_generate"

    def test_trust_level(self, tool):
        assert tool.trust_level == "standard"

    def test_parameters_schema(self, tool):
        params = tool.parameters
        assert "prompt" in params["properties"]
        assert "aspect_ratio" in params["properties"]
        assert "size" in params["properties"]
        assert "model" in params["properties"]
        assert "prompt" in params["required"]

    @patch("pocketpaw.tools.builtin.image_gen.get_settings")
    async def test_missing_api_key(self, mock_settings, tool):
        mock_settings.return_value = MagicMock(google_api_key=None)
        result = await tool.execute(prompt="a cat")
        assert "Error" in result
        assert "Google API key" in result

    @patch("pocketpaw.tools.builtin.image_gen.get_settings")
    async def test_missing_genai_package(self, mock_settings, tool):
        mock_settings.return_value = MagicMock(
            google_api_key="test-key",
            image_model="gemini-2.5-flash-image",
        )

        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "google" or name.startswith("google."):
                raise ImportError("No module named 'google'")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", side_effect=mock_import):
            result = await tool.execute(prompt="a cat")

        assert "Error" in result
        assert "google-genai" in result

    @patch("pocketpaw.tools.builtin.image_gen._get_generated_dir")
    @patch("pocketpaw.tools.builtin.image_gen.get_settings")
    async def test_image_generation_success_uses_default_model(self, mock_settings, mock_dir, tool):
        mock_settings.return_value = MagicMock(
            google_api_key="test-key",
            image_model="gemini-2.5-flash-image",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_dir.return_value = Path(tmpdir)

            mock_image = MagicMock()
            mock_part = MagicMock()
            mock_part.as_image.return_value = mock_image
            mock_response = SimpleNamespace(parts=[mock_part])

            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response

            mock_genai = SimpleNamespace(
                Client=MagicMock(return_value=mock_client),
            )
            mock_google = SimpleNamespace(genai=mock_genai)

            with patch.dict("sys.modules", {"google": mock_google, "google.genai": mock_genai}):
                result = await tool.execute(prompt="a cat on a skateboard", aspect_ratio="16:9")

            assert "Image generated with gemini-2.5-flash-image" in result
            mock_client.models.generate_content.assert_called_once_with(
                model="gemini-2.5-flash-image",
                contents=["a cat on a skateboard"],
            )
            mock_image.save.assert_called_once()

    @patch("pocketpaw.tools.builtin.image_gen._get_generated_dir")
    @patch("pocketpaw.tools.builtin.image_gen.get_settings")
    async def test_image_generation_success_with_model_override(self, mock_settings, mock_dir, tool):
        mock_settings.return_value = MagicMock(
            google_api_key="test-key",
            image_model="gemini-2.5-flash-image",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_dir.return_value = Path(tmpdir)

            mock_image = MagicMock()
            mock_part = MagicMock()
            mock_part.as_image.return_value = mock_image
            mock_response = SimpleNamespace(parts=[mock_part])

            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response

            mock_genai = SimpleNamespace(
                Client=MagicMock(return_value=mock_client),
            )
            mock_google = SimpleNamespace(genai=mock_genai)

            with patch.dict("sys.modules", {"google": mock_google, "google.genai": mock_genai}):
                result = await tool.execute(
                    prompt="cinematic skyline",
                    model="gemini-3-pro-image-preview",
                )

            assert "Image generated with gemini-3-pro-image-preview" in result
            mock_client.models.generate_content.assert_called_once_with(
                model="gemini-3-pro-image-preview",
                contents=["cinematic skyline"],
            )
            mock_image.save.assert_called_once()

    @patch("pocketpaw.tools.builtin.image_gen._get_generated_dir")
    @patch("pocketpaw.tools.builtin.image_gen.get_settings")
    async def test_no_images_generated(self, mock_settings, mock_dir, tool):
        mock_settings.return_value = MagicMock(
            google_api_key="test-key",
            image_model="gemini-2.5-flash-image",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_dir.return_value = Path(tmpdir)

            mock_part = MagicMock()
            mock_part.as_image.return_value = None
            mock_response = SimpleNamespace(parts=[mock_part])

            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response

            mock_genai = SimpleNamespace(
                Client=MagicMock(return_value=mock_client),
            )
            mock_google = SimpleNamespace(genai=mock_genai)

            with patch.dict("sys.modules", {"google": mock_google, "google.genai": mock_genai}):
                result = await tool.execute(prompt="a cat")

            assert "Error: No image was generated" in result

    def test_generated_dir_creation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pocketpaw.tools.builtin.image_gen.get_config_dir") as mock_config:
                mock_config.return_value = Path(tmpdir)
                from pocketpaw.tools.builtin.image_gen import _get_generated_dir

                d = _get_generated_dir()
                assert d.exists()
                assert d.name == "generated"
