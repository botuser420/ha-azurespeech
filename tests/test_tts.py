"""Tests for Azure Speech TTS platform."""

from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.azure_speech.const import CONF_STYLE, CONF_VOICE
from custom_components.azure_speech.tts import AzureSpeechTTSEntity
from homeassistant.core import HomeAssistant


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


def _sent_ssml(client: AsyncMock) -> str:
    """Return the SSML passed to the mocked Azure client."""
    return client.generate_tts_audio.call_args.kwargs["ssml_content"]


async def _setup(hass: HomeAssistant, entry: MockConfigEntry, client: AsyncMock) -> AzureSpeechTTSEntity:
    """Set up the integration with a mocked client and return a TTS entity."""
    entry.add_to_hass(hass)
    with patch("custom_components.azure_speech.AzureSpeechApiClient", return_value=client):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return AzureSpeechTTSEntity(entry)


async def test_tts_style_defaults_to_none(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api_client: AsyncMock,
) -> None:
    """Without a style option the request has no express-as and the style is advertised."""
    tts_entity = await _setup(hass, mock_config_entry, mock_api_client)
    assert CONF_STYLE in tts_entity.supported_options
    assert tts_entity.default_options[CONF_STYLE] == ""

    await tts_entity.async_get_tts_audio(message="Hello", language="en-US")
    assert "express-as" not in _sent_ssml(mock_api_client)


async def test_tts_style_from_integration_options(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api_client: AsyncMock,
) -> None:
    """The integration's style option reaches the Azure request body."""
    hass.config_entries.async_update_entry(
        mock_config_entry, options={CONF_VOICE: "nl-NL-Grant:MAI-Voice-2.1", CONF_STYLE: "agent"}
    )
    tts_entity = await _setup(hass, mock_config_entry, mock_api_client)
    assert tts_entity.default_options[CONF_STYLE] == "agent"

    await tts_entity.async_get_tts_audio(message="Hallo", language="nl-NL")
    ssml = _sent_ssml(mock_api_client)
    assert '<mstts:express-as style="agent">' in ssml
    assert "nl-NL-Grant:MAI-Voice-2.1" in ssml


async def test_tts_style_call_option_overrides_integration_option(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api_client: AsyncMock,
) -> None:
    """A per-call style wins over the integration option, and an empty one switches it off."""
    hass.config_entries.async_update_entry(mock_config_entry, options={CONF_STYLE: "agent"})
    tts_entity = await _setup(hass, mock_config_entry, mock_api_client)

    await tts_entity.async_get_tts_audio(message="Hi", language="en-US", options={CONF_STYLE: "cheerful"})
    ssml = _sent_ssml(mock_api_client)
    assert 'style="cheerful"' in ssml
    assert "agent" not in ssml

    await tts_entity.async_get_tts_audio(message="Hi", language="en-US", options={CONF_STYLE: ""})
    assert "express-as" not in _sent_ssml(mock_api_client)
