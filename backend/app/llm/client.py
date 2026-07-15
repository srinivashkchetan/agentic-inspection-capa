"""Anthropic client wrapper — the ONLY sanctioned path to the model (PRD §5.2).

Uses the official `anthropic` SDK with Claude Opus 4.8 and adaptive thinking.
Structured output is enforced via `messages.parse(output_format=...)` so the
model returns exactly the CAPA schema. When no API key is configured the caller
should use the offline stub instead of this client.
"""

from __future__ import annotations

from app.config import get_settings
from app.models import GeneratedCapa


class CapaLLM:
    def __init__(self) -> None:
        # Imported lazily so the package works without the SDK installed / no key.
        import anthropic

        settings = get_settings()
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._model = settings.capa_model

    def draft(self, system: str, user: str) -> GeneratedCapa:
        """Generate a structured CAPA draft. Raises on refusal or API error."""
        response = self._client.messages.parse(
            model=self._model,
            max_tokens=4096,
            thinking={"type": "adaptive"},
            system=system,
            messages=[{"role": "user", "content": user}],
            output_format=GeneratedCapa,
        )
        if response.stop_reason == "refusal":  # PRD §7.2 abstention path
            raise RuntimeError("Model refused to generate the CAPA draft.")
        if response.parsed_output is None:
            raise RuntimeError("Model returned no parseable CAPA draft.")
        return response.parsed_output
