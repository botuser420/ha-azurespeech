"""Text-to-speech platform for azure_speech."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from custom_components.azure_speech.const import (
    AZURE_OUTPUT_FORMATS,
    CONF_AUDIO_FORMAT,
    CONF_LANGUAGE,
    CONF_PITCH,
    CONF_RATE,
    CONF_VOICE,
    DEFAULT_AUDIO_FORMAT,
    DEFAULT_LANGUAGE,
    DEFAULT_PITCH,
    DEFAULT_RATE,
    DEFAULT_VOICE,
)
from custom_components.azure_speech.data import AzureSpeechConfigEntry
from custom_components.azure_speech.entity import AzureSpeechEntity
from custom_components.azure_speech.entity_utils import generate_ssml
from homeassistant.components.tts import (
    ATTR_AUDIO_OUTPUT,
    ATTR_VOICE,
    TextToSpeechEntity,
    TTSAudioRequest,
    TTSAudioResponse,
    TtsAudioType,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
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
        return [ATTR_VOICE, CONF_PITCH, CONF_RATE, ATTR_AUDIO_OUTPUT]

    @property
    def default_options(self) -> dict[str, Any]:
        """Return default options dict."""
        return {
            ATTR_VOICE: self._entry.options.get(CONF_VOICE, DEFAULT_VOICE),
            CONF_PITCH: self._entry.options.get(CONF_PITCH, DEFAULT_PITCH),
            CONF_RATE: self._entry.options.get(CONF_RATE, DEFAULT_RATE),
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
        :param options: Optional overrides (voice, pitch, rate, audio_output).
        :return: Tuple of (audio_extension, audio_bytes).
        """
        audio_fmt, azure_output_format, ssml = self._build_request(message, language, options)

        audio_bytes = await self.coordinator.client.generate_tts_audio(
            ssml_content=ssml,
            output_format=azure_output_format,
        )

        return (audio_fmt, audio_bytes)

    @callback
    def async_supports_streaming_input(self) -> bool:
        """Return that this engine accepts streamed input (messages are joined before synthesis)."""
        return True

    async def async_stream_tts_audio(self, request: TTSAudioRequest) -> TTSAudioResponse:
        """Stream TTS audio from Azure Speech API as it is received.

        Azure needs a complete SSML document, so the whole message is collected
        first. The first audio chunk is awaited here, so errors before any audio
        arrives are raised to the caller instead of ending a silent stream.

        :param request: TTS request with language, options and message generator.
        :return: Audio response with the extension and an async chunk generator.
        :raises HomeAssistantError: If Azure returns no audio.
        """
        message = "".join([part async for part in request.message_gen])
        audio_fmt, azure_output_format, ssml = self._build_request(message, request.language, request.options)

        audio = self.coordinator.client.stream_tts_audio(
            ssml_content=ssml,
            output_format=azure_output_format,
        )
        try:
            first_chunk = await anext(audio)
        except StopAsyncIteration as err:
            raise HomeAssistantError("Azure Speech returned no audio") from err
        except BaseException:
            await audio.aclose()
            raise

        async def data_gen() -> AsyncGenerator[bytes]:
            try:
                yield first_chunk
                async for chunk in audio:
                    yield chunk
            finally:
                await audio.aclose()

        return TTSAudioResponse(audio_fmt, data_gen())

    def _build_request(
        self,
        message: str,
        language: str | None,
        options: dict[str, Any] | None,
    ) -> tuple[str, str, str]:
        """Resolve options and build the synthesis request.

        :param message: Text string or SSML XML to synthesize.
        :param language: Requested language code.
        :param options: Optional overrides (voice, pitch, rate, audio_output).
        :return: Tuple of (audio_extension, azure_output_format, ssml).
        """
        opts = options or {}
        voice = opts.get(ATTR_VOICE, self._entry.options.get(CONF_VOICE, DEFAULT_VOICE))
        pitch = opts.get(CONF_PITCH, self._entry.options.get(CONF_PITCH, DEFAULT_PITCH))
        rate = opts.get(CONF_RATE, self._entry.options.get(CONF_RATE, DEFAULT_RATE))
        audio_fmt = opts.get(ATTR_AUDIO_OUTPUT, self._entry.options.get(CONF_AUDIO_FORMAT, DEFAULT_AUDIO_FORMAT))

        azure_output_format = AZURE_OUTPUT_FORMATS.get(audio_fmt, AZURE_OUTPUT_FORMATS[DEFAULT_AUDIO_FORMAT])

        ssml = generate_ssml(
            text=message,
            voice=voice,
            language=language or self.default_language,
            pitch=pitch,
            rate=rate,
        )

        return (audio_fmt, azure_output_format, ssml)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AzureSpeechConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Azure Speech TTS platform."""
    async_add_entities([AzureSpeechTTSEntity(entry)])
