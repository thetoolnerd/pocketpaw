# Image Generation tool — generate images via Google Gemini.
# Created: 2026-02-06
# Part of Phase 1 Quick Wins

import logging
import uuid
from pathlib import Path
from typing import Any

from pocketpaw.config import get_config_dir, get_settings
from pocketpaw.tools.protocol import BaseTool

logger = logging.getLogger(__name__)


def _get_generated_dir() -> Path:
    """Get (and create) the directory for generated images."""
    d = get_config_dir() / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


class ImageGenerateTool(BaseTool):
    """Generate images using Google Gemini native image models."""

    @property
    def name(self) -> str:
        return "image_generate"

    @property
    def description(self) -> str:
        return (
            "Generate an image from a text prompt using Google Gemini image models. "
            "Returns the file path of the saved image. "
            "Model can be overridden per request (e.g. 'gemini-2.5-flash-image' or "
            "'gemini-3-pro-image-preview')."
        )

    @property
    def trust_level(self) -> str:
        return "standard"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Text description of the image to generate",
                },
                "aspect_ratio": {
                    "type": "string",
                    "description": "Aspect ratio (default: '1:1'). Options: '1:1', '16:9', '9:16'",
                    "default": "1:1",
                },
                "size": {
                    "type": "string",
                    "description": "Unused for Gemini native models. Kept for backward compatibility.",
                    "default": "",
                },
                "model": {
                    "type": "string",
                    "description": "Optional model override. Defaults to configured image_model.",
                },
            },
            "required": ["prompt"],
        }

    async def execute(
        self,
        prompt: str,
        aspect_ratio: str = "1:1",
        size: str = "",
        model: str = "",
    ) -> str:
        """Generate an image from a text prompt."""
        settings = get_settings()

        if not settings.google_api_key:
            return self._error("Google API key not configured. Set POCKETPAW_GOOGLE_API_KEY.")

        try:
            from google import genai
        except ImportError:
            return self._error(
                "google-genai package not installed. Install with: pip install 'pocketpaw[image]'"
            )

        try:
            client = genai.Client(api_key=settings.google_api_key)
            selected_model = (model or settings.image_model or "gemini-2.5-flash-image").strip()

            # Gemini native image models use generate_content, not generate_images.
            response = client.models.generate_content(
                model=selected_model,
                contents=[prompt],
            )

            image = None
            for part in getattr(response, "parts", []) or []:
                as_image = getattr(part, "as_image", None)
                if callable(as_image):
                    image = as_image()
                    if image is not None:
                        break

            if image is None:
                return self._error("No image was generated. Try a different prompt.")

            out_dir = _get_generated_dir()
            filename = f"{uuid.uuid4()}.png"
            out_path = out_dir / filename
            image.save(out_path)

            logger.info("Generated image: %s", out_path)
            return self._media_result(
                str(out_path),
                f"Image generated with {selected_model} (prompt: {prompt}, aspect ratio: {aspect_ratio})",
            )

        except Exception as e:
            return self._error(f"Image generation failed: {e}")
