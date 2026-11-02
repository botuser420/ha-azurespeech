"""Text-to-speech platform for azure_speech."""

from __future__ import annotations

from typing import Any

from custom_components.azure_speech.const import (
    AZURE_OUTPUT_FORMATS,
    CONF_AUDIO_FORMAT,
    CONF_LANGUAGE,
    CONF_PITCH,
    CONF_RATE,
    CONF_STYLE,
    CONF_VOICE,
    DEFAULT_AUDIO_FORMAT,
    DEFAULT_LANGUAGE,
    DEFAULT_PITCH,
    DEFAULT_RATE,
    DEFAULT_STYLE,
    DEFAULT_VOICE,
)
from custom_components.azure_speech.data import AzureSpeechConfigEntry
from custom_components.azure_speech.entity import AzureSpeechEntity
from custom_components.azure_speech.entity_utils import generate_ssml
from homeassistant.components.tts import ATTR_AUDIO_OUTPUT, ATTR_VOICE, TextToSpeechEntity, TtsAudioType
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback


class AzureSpeechTTSEntity(TextToSpeechEntity, AzureSpeechEntity):
    """Azure Speech Text-to-Speech entity implementation."""

    def __init__(
        self,
        entry: AzureSpeechConfigEntry,
    ) -> None:
        """Initialize Azure Speech TTS entity."""
        coordinator = entry.runtime_data.coordinator
        description = EntityDescription(
            key="tts",
            name="Azure Speech TTS",
        )
        super().__init__(coordinator, description)
        self._entry = entry

    @property
    def supported_languages(self) -> list[str]:
        """Return list of supported languages from cached voices."""
        voices = self.coordinator.voices
        if voices:
            locales = {v.get("Locale") for v in voices if v.get("Locale")}
            if locales:
                return sorted(locales)
        return [DEFAULT_LANGUAGE]

    @property
    def default_language(self) -> str:
        """Return default language setting from options or fallback."""
        return self._entry.options.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)

    @property
    def supported_options(self) -> list[str]:
        """Return list of supported options in TTS call."""
        return [ATTR_VOICE, CONF_PITCH, CONF_RATE, CONF_STYLE, ATTR_AUDIO_OUTPUT]

    @property
    def default_options(self) -> dict[str, Any]:
        """Return default options dict."""
        return {
            ATTR_VOICE: self._entry.options.get(CONF_VOICE, DEFAULT_VOICE),
            CONF_PITCH: self._entry.options.get(CONF_PITCH, DEFAULT_PITCH),
            CONF_RATE: self._entry.options.get(CONF_RATE, DEFAULT_RATE),
            CONF_STYLE: self._entry.options.get(CONF_STYLE, DEFAULT_STYLE),
            ATTR_AUDIO_OUTPUT: self._entry.options.get(CONF_AUDIO_FORMAT, DEFAULT_AUDIO_FORMAT),
        }

    async def async_get_tts_audio(
        self,
        message: str,
        language: str,
        options: dict[str, Any] | None = None,
    ) -> TtsAudioType:
        """Load TTS audio bytes from Azure Speech API.

        :param message: Text string or SSML XML to synthesize.
        :param language: Requested language code.
        :param options: Optional overrides (voice, pitch, rate, style, audio_output).
        :return: Tuple of (audio_extension, audio_bytes).
        """
        opts = options or {}
        voice = opts.get(ATTR_VOICE, self._entry.options.get(CONF_VOICE, DEFAULT_VOICE))
        pitch = opts.get(CONF_PITCH, self._entry.options.get(CONF_PITCH, DEFAULT_PITCH))
        rate = opts.get(CONF_RATE, self._entry.options.get(CONF_RATE, DEFAULT_RATE))
        style = opts.get(CONF_STYLE, self._entry.options.get(CONF_STYLE, DEFAULT_STYLE))
        audio_fmt = opts.get(ATTR_AUDIO_OUTPUT, self._entry.options.get(CONF_AUDIO_FORMAT, DEFAULT_AUDIO_FORMAT))

        azure_output_format = AZURE_OUTPUT_FORMATS.get(audio_fmt, AZURE_OUTPUT_FORMATS[DEFAULT_AUDIO_FORMAT])

        ssml = generate_ssml(
            text=message,
            voice=voice,
            language=language or self.default_language,
            pitch=pitch,
            rate=rate,
            style=style,
        )

        audio_bytes = await self.coordinator.client.generate_tts_audio(
            ssml_content=ssml,
            output_format=azure_output_format,
        )

        return (audio_fmt, audio_bytes)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AzureSpeechConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Azure Speech TTS platform."""
    async_add_entities([AzureSpeechTTSEntity(entry)])
