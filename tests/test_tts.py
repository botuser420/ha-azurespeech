"""Tests for Azure Speech TTS platform."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.azure_speech.api import (
    AzureSpeechApiClientAuthenticationError,
    AzureSpeechApiClientCommunicationError,
    AzureSpeechApiClientError,
    AzureSpeechApiClientRateLimitError,
)
from custom_components.azure_speech.tts import AzureSpeechTTSEntity
from homeassistant.components.tts import TTSAudioRequest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError


async def test_tts_properties_and_audio(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api_client: AsyncMock,
) -> None:
    """Test TTS entity properties and async_get_tts_audio method."""
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.azure_speech.AzureSpeechApiClient",
        return_value=mock_api_client,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        tts_entity = AzureSpeechTTSEntity(mock_config_entry)
        assert tts_entity.default_language == "en-US"
        assert "en-US" in tts_entity.supported_languages

        audio_format, audio_bytes = await tts_entity.async_get_tts_audio(
            message="Hello world",
            language="en-US",
        )
        assert audio_format == "mp3"
        assert audio_bytes == b"mock_mp3_audio_bytes"


TTS_URL = "https://eastus.tts.speech.microsoft.com/cognitiveservices/v1"
VOICES_URL = "https://eastus.tts.speech.microsoft.com/cognitiveservices/voices/list"
API_KEY = "test_secret_api_key_12345"


async def _setup_entity(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    mock_voices_list: list[dict],
) -> AzureSpeechTTSEntity:
    """Set up the integration with Azure mocked at HTTP level and return the TTS entity."""
    aioclient_mock.get(VOICES_URL, json=mock_voices_list)
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    return AzureSpeechTTSEntity(mock_config_entry)


async def _message_gen(*parts: str) -> AsyncGenerator[str]:
    """Yield message parts like a streamed LLM answer."""
    for part in parts:
        yield part


def _request(*parts: str, options: dict | None = None) -> TTSAudioRequest:
    """Build a streaming TTS request."""
    return TTSAudioRequest(language="en-US", options=options or {}, message_gen=_message_gen(*parts))


def _tts_calls(aioclient_mock: AiohttpClientMocker) -> list:
    """Return the recorded synthesis calls."""
    return [call for call in aioclient_mock.mock_calls if call[0] == "POST" and str(call[1]) == TTS_URL]


async def test_stream_tts_audio_returns_chunks_in_order(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    mock_voices_list: list[dict],
) -> None:
    """Streamed audio has the right extension, Azure format, SSML and headers."""
    entity = await _setup_entity(hass, mock_config_entry, aioclient_mock, mock_voices_list)
    aioclient_mock.post(TTS_URL, content=b"chunk-1|chunk-2|chunk-3")

    response = await entity.async_stream_tts_audio(_request("Hello ", "streamed ", "world"))

    assert response.extension == "mp3"
    audio = [chunk async for chunk in response.data_gen]
    assert b"".join(audio) == b"chunk-1|chunk-2|chunk-3"

    calls = _tts_calls(aioclient_mock)
    assert len(calls) == 1
    _, _, data, headers = calls[0]
    assert headers["X-Microsoft-OutputFormat"] == "audio-24khz-48kbitrate-mono-mp3"
    assert headers["Content-Type"] == "application/ssml+xml"
    assert b"Hello streamed world" in data
    assert b"<speak" in data


async def test_stream_tts_audio_uses_requested_format(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    mock_voices_list: list[dict],
) -> None:
    """The audio_output option selects the Azure format and the extension."""
    entity = await _setup_entity(hass, mock_config_entry, aioclient_mock, mock_voices_list)
    aioclient_mock.post(TTS_URL, content=b"RIFFwav")

    response = await entity.async_stream_tts_audio(_request("Hi", options={"audio_output": "wav"}))
    audio = b"".join([chunk async for chunk in response.data_gen])

    assert response.extension == "wav"
    assert audio == b"RIFFwav"
    assert _tts_calls(aioclient_mock)[0][3]["X-Microsoft-OutputFormat"] == "riff-24khz-16bit-mono-pcm"


@pytest.mark.parametrize(
    ("post_kwargs", "expected"),
    [
        ({"status": 401}, AzureSpeechApiClientAuthenticationError),
        ({"status": 403}, AzureSpeechApiClientAuthenticationError),
        ({"status": 429, "headers": {"Retry-After": "7"}}, AzureSpeechApiClientRateLimitError),
        ({"status": 500, "content": b"boom"}, AzureSpeechApiClientError),
        ({"exc": aiohttp.ClientConnectionError("down")}, AzureSpeechApiClientCommunicationError),
        ({"exc": TimeoutError()}, AzureSpeechApiClientCommunicationError),
    ],
)
async def test_stream_tts_audio_error_before_first_audio(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    mock_voices_list: list[dict],
    caplog: pytest.LogCaptureFixture,
    post_kwargs: dict,
    expected: type[Exception],
) -> None:
    """Errors before the first audio chunk come out of async_stream_tts_audio itself."""
    entity = await _setup_entity(hass, mock_config_entry, aioclient_mock, mock_voices_list)
    aioclient_mock.post(TTS_URL, **post_kwargs)

    with pytest.raises(expected):
        await entity.async_stream_tts_audio(_request("Hello"))

    assert API_KEY not in caplog.text


async def test_stream_tts_audio_empty_response_raises(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    mock_voices_list: list[dict],
) -> None:
    """An empty response is a HomeAssistantError, not a silent stream."""
    entity = await _setup_entity(hass, mock_config_entry, aioclient_mock, mock_voices_list)
    aioclient_mock.post(TTS_URL, content=b"")

    with pytest.raises(HomeAssistantError):
        await entity.async_stream_tts_audio(_request("Hello"))


async def test_stream_tts_audio_consumer_can_stop_early(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    mock_voices_list: list[dict],
) -> None:
    """Closing the stream after the first chunk ends it without error."""
    entity = await _setup_entity(hass, mock_config_entry, aioclient_mock, mock_voices_list)
    aioclient_mock.post(TTS_URL, content=b"some audio")

    response = await entity.async_stream_tts_audio(_request("Hello"))
    first = await anext(response.data_gen)
    await response.data_gen.aclose()

    assert first
    with pytest.raises(StopAsyncIteration):
        await anext(response.data_gen)


async def test_supports_streaming_input(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    mock_voices_list: list[dict],
) -> None:
    """The entity reports that it accepts streaming input."""
    entity = await _setup_entity(hass, mock_config_entry, aioclient_mock, mock_voices_list)

    assert entity.async_supports_streaming_input() is True


async def test_get_tts_audio_unchanged_over_http(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    mock_voices_list: list[dict],
) -> None:
    """The non-streaming route still returns the whole audio in one piece."""
    entity = await _setup_entity(hass, mock_config_entry, aioclient_mock, mock_voices_list)
    aioclient_mock.post(TTS_URL, content=b"whole answer")

    result = await entity.async_get_tts_audio(message="Hello", language="en-US")

    assert result == ("mp3", b"whole answer")
    headers = _tts_calls(aioclient_mock)[0][3]
    assert headers["X-Microsoft-OutputFormat"] == "audio-24khz-48kbitrate-mono-mp3"
