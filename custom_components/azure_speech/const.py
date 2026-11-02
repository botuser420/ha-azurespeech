"""Constants for azure_speech."""

from logging import Logger, getLogger
from typing import Final

from homeassistant.const import Platform

LOGGER: Logger = getLogger(__package__)

# Integration metadata
DOMAIN: Final = "azure_speech"
ATTRIBUTION: Final = "Data provided by Microsoft Azure Speech Services"

# Configuration options
CONF_API_KEY: Final = "api_key"
CONF_REGION: Final = "region"
CONF_ENDPOINT: Final = "endpoint"
CONF_VOICE: Final = "voice"
CONF_LANGUAGE: Final = "language"
CONF_PITCH: Final = "pitch"
CONF_RATE: Final = "rate"
CONF_STYLE: Final = "style"
CONF_AUDIO_FORMAT: Final = "audio_format"
CONF_PROFANITY_MODE: Final = "profanity_mode"

# Default configuration values
DEFAULT_REGION: Final = "eastus"
DEFAULT_LANGUAGE: Final = "en-US"
DEFAULT_VOICE: Final = "en-US-AvaMultilingualNeural"
DEFAULT_PITCH: Final = "default"
DEFAULT_RATE: Final = "default"
DEFAULT_STYLE: Final = ""  # empty = no mstts:express-as wrapper
DEFAULT_AUDIO_FORMAT: Final = "mp3"
DEFAULT_PROFANITY_MODE: Final = "masked"

# Common Azure Speech regions
AZURE_REGIONS: Final[list[str]] = [
    "eastus",
    "eastus2",
    "westus",
    "westus2",
    "westus3",
    "centralus",
    "northcentralus",
    "southcentralus",
    "westeurope",
    "northeurope",
    "uksouth",
    "ukwest",
    "francecentral",
    "germanywestcentral",
    "eastasia",
    "southeastasia",
    "japaneast",
    "japanwest",
    "australiaeast",
    "centralindia",
    "brazilsouth",
    "canadacentral",
    "koreacentral",
]

# Audio Output Format mappings for Azure TTS REST API
AZURE_OUTPUT_FORMATS: Final[dict[str, str]] = {
    "mp3": "audio-24khz-48kbitrate-mono-mp3",
    "wav": "riff-24khz-16bit-mono-pcm",
    "ogg": "webm-24khz-16bit-24kbps-mono-opus",
}

# Platforms supported
PLATFORMS: Final[list[Platform]] = [
    Platform.TTS,
    Platform.STT,
    Platform.SENSOR,
]
