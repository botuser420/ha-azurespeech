"""Tests for Azure Speech config flow and options flow."""

from unittest.mock import patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.azure_speech.api import (
    AzureSpeechApiClientAuthenticationError,
    AzureSpeechApiClientCommunicationError,
)
from custom_components.azure_speech.const import CONF_API_KEY, CONF_AUDIO_FORMAT, CONF_REGION, CONF_VOICE, DOMAIN
from homeassistant import config_entries
from homeassistant.core import HomeAssistant


async def test_user_flow_success(hass: HomeAssistant) -> None:
    """Test successful user step setup."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] == "form"
    assert result["step_id"] == "user"

    with patch(
        "custom_components.azure_speech.config_flow_handler.config_flow.validate_auth_input",
        return_value={"title": "Azure Speech (eastus)", "voice_count": "2"},
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_API_KEY: "valid_secret_key",
                CONF_REGION: "eastus",
            },
        )
        assert result2["type"] == "create_entry"
        assert result2["title"] == "Azure Speech (eastus)"
        assert result2["data"][CONF_API_KEY] == "valid_secret_key"
        assert result2["data"][CONF_REGION] == "eastus"


async def test_user_flow_invalid_auth(hass: HomeAssistant) -> None:
    """Test user step with invalid API key credentials."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

    with patch(
        "custom_components.azure_speech.config_flow_handler.config_flow.validate_auth_input",
        side_effect=AzureSpeechApiClientAuthenticationError("Invalid Key"),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_API_KEY: "bad_key",
                CONF_REGION: "eastus",
            },
        )
        assert result2["type"] == "form"
        assert result2["errors"] == {"base": "invalid_auth"}


async def test_user_flow_cannot_connect(hass: HomeAssistant) -> None:
    """Test user step with network connection timeout."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

    with patch(
        "custom_components.azure_speech.config_flow_handler.config_flow.validate_auth_input",
        side_effect=AzureSpeechApiClientCommunicationError("Timeout"),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_API_KEY: "key",
                CONF_REGION: "eastus",
            },
        )
        assert result2["type"] == "form"
        assert result2["errors"] == {"base": "cannot_connect"}


async def test_reauth_flow_success(hass: HomeAssistant, mock_config_entry: MockConfigEntry) -> None:
    """Test re-authentication flow."""
    mock_config_entry.add_to_hass(hass)

    result = await mock_config_entry.start_reauth_flow(hass)
    assert result["type"] == "form"
    assert result["step_id"] == "reauth_confirm"

    with patch(
        "custom_components.azure_speech.config_flow_handler.config_flow.validate_auth_input",
        return_value={"title": "Azure Speech (eastus)", "voice_count": "2"},
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_API_KEY: "new_valid_key",
                CONF_REGION: "eastus",
            },
        )
        assert result2["type"] == "abort"
        assert result2["reason"] == "reauth_successful"
        assert mock_config_entry.data[CONF_API_KEY] == "new_valid_key"


async def test_options_flow(hass: HomeAssistant, mock_config_entry: MockConfigEntry) -> None:
    """Test options flow configuration."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] == "form"
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_VOICE: "en-US-AvaMultilingualNeural",
            CONF_AUDIO_FORMAT: "mp3",
        },
    )
    assert result2["type"] == "create_entry"
    assert mock_config_entry.options[CONF_VOICE] == "en-US-AvaMultilingualNeural"
    assert mock_config_entry.options[CONF_AUDIO_FORMAT] == "mp3"


async def test_options_flow_style(hass: HomeAssistant, mock_config_entry: MockConfigEntry) -> None:
    """The speaking style can be set in the options flow."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_VOICE: "nl-NL-Grant:MAI-Voice-2.1", "style": "agent"},
    )
    assert result2["type"] == "create_entry"
    assert mock_config_entry.options["style"] == "agent"
