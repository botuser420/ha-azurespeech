"""Schema definitions for options flow in Azure Speech config flow."""

from typing import Any

import voluptuous as vol

from custom_components.azure_speech.const import (
    CONF_AUDIO_FORMAT,
    CONF_LANGUAGE,
    CONF_PITCH,
    CONF_PROFANITY_MODE,
    CONF_RATE,
    CONF_STYLE,
    CONF_VOICE,
    DEFAULT_AUDIO_FORMAT,
    DEFAULT_LANGUAGE,
    DEFAULT_PITCH,
    DEFAULT_PROFANITY_MODE,
    DEFAULT_RATE,
    DEFAULT_STYLE,
    DEFAULT_VOICE,
)
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
)


def get_options_schema(
    voices_list: list[dict[str, Any]],
    current_options: dict[str, Any],
) -> vol.Schema:
    """Build the options schema with dynamic voices dropdown."""
    voice_options: list[SelectOptionDict] = []
    if voices_list:
        for v in voices_list:
            short_name = v.get("ShortName", "")
            display_name = f"{short_name} ({v.get('Gender', '')}, {v.get('Locale', '')})"
            voice_options.append(SelectOptionDict(value=short_name, label=display_name))

    selected_voice = current_options.get(CONF_VOICE, DEFAULT_VOICE)

    return vol.Schema(
        {
            vol.Optional(
                CONF_VOICE,
                default=selected_voice,
            ): SelectSelector(
                SelectSelectorConfig(
                    options=voice_options or [selected_voice],
                    mode=SelectSelectorMode.DROPDOWN,
                    custom_value=True,
                )
            ),
            vol.Optional(
                CONF_LANGUAGE,
                default=current_options.get(CONF_LANGUAGE, DEFAULT_LANGUAGE),
            ): TextSelector(TextSelectorConfig()),
            vol.Optional(
                CONF_PITCH,
                default=current_options.get(CONF_PITCH, DEFAULT_PITCH),
            ): TextSelector(TextSelectorConfig()),
            vol.Optional(
                CONF_RATE,
                default=current_options.get(CONF_RATE, DEFAULT_RATE),
            ): TextSelector(TextSelectorConfig()),
            vol.Optional(
                CONF_STYLE,
                default=current_options.get(CONF_STYLE, DEFAULT_STYLE),
            ): TextSelector(TextSelectorConfig()),
            vol.Optional(
                CONF_AUDIO_FORMAT,
                default=current_options.get(CONF_AUDIO_FORMAT, DEFAULT_AUDIO_FORMAT),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=["mp3", "wav", "ogg"],
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(
                CONF_PROFANITY_MODE,
                default=current_options.get(CONF_PROFANITY_MODE, DEFAULT_PROFANITY_MODE),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=["masked", "removed", "raw"],
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
        }
    )
