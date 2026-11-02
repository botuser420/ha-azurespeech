# Azure Speech Custom Integration for Home Assistant

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]
![Project Maintenance][maintenance-shield]

**✨ Azure Speech Integration** for Home Assistant provides full-featured Text-to-Speech (TTS) and Speech-to-Text (STT) capabilities powered by Microsoft Azure Cognitive Speech Services.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/pantherale0/ha-azurespeech?quickstart=1)

---

## ✨ Features

- **Text-to-Speech (TTS)**: High-quality neural voices from Microsoft Azure with SSML payload support; audio is streamed to Home Assistant while Azure is still synthesizing, so playback can start earlier.
- **Speech-to-Text (STT)**: High-accuracy real-time speech recognition for Home Assistant Voice Assistant (Assist).
- **Dynamic Voice Discovery**: Dynamically fetches 500+ Azure neural voices across all regions and languages.
- **UI Configuration & Options Flow**: Easy setup via UI with dropdown selectors for default voice, language, pitch, rate, speaking style (Azure `mstts:express-as`, e.g. `agent` for `nl-NL-Grant:MAI-Voice-2.1`; empty = off), audio formats (`mp3`/`wav`/`ogg`), and profanity filtering.
- **Diagnostic Entities**: Monitor API connection status and cached voice counts.
- **Custom Service Action**: `azure_speech.refresh_voices` service action to update cached voices on demand.
- **Pure Async Architecture**: Built with lightweight `aiohttp` (no native C binary dependencies, fully non-blocking on HA event loop).

---

## 🚀 Supported Platforms

| Platform | Description                                                    |
| -------- | -------------------------------------------------------------- |
| `tts`    | Azure Speech Text-to-Speech entity (`tts.azure_speech_tts`)    |
| `stt`    | Azure Speech Speech-to-Text entity (`stt.azure_speech_stt`)    |
| `sensor` | API Connection Status & Cached Voices Count diagnostic sensors |

---

## 🚀 Quick Start

### Installation via HACS

1. Ensure [HACS](https://hacs.xyz/) is installed in your Home Assistant instance.
2. Open HACS -> Integrations -> Custom Repositories.
3. Add repository URL: `https://github.com/pantherale0/ha-azurespeech` with category `Integration`.
4. Click **Install**.
5. Restart Home Assistant.

### Configuration

1. Go to **Settings -> Devices & Services -> Add Integration**.
2. Search for **Azure Speech**.
3. Enter your Azure Speech **API Key** and **Region** (e.g., `eastus`, `westeurope`).
4. Click **Submit**.

---

## 📊 Diagnostics & Services

- **Diagnostic Sensors**: `sensor.azure_speech_<region>_api_connection_status` and `sensor.azure_speech_<region>_cached_voices_count`.
- **Service Action**: `azure_speech.refresh_voices` - Call from automations or Developer Tools -> Services to reload Azure voice lists.

---

## 👥 Credits & Maintenance

Made with ❤️ by [@pantherale0][user_profile].

[commits-shield]: https://img.shields.io/github/commit-activity/y/pantherale0/ha-azurespeech.svg?style=for-the-badge
[commits]: https://github.com/pantherale0/ha-azurespeech/commits/main
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[hacs]: https://github.com/hacs/integration
[license-shield]: https://img.shields.io/github/license/pantherale0/ha-azurespeech.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40pantherale0-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/pantherale0/ha-azurespeech.svg?style=for-the-badge
[releases]: https://github.com/pantherale0/ha-azurespeech/releases
[user_profile]: https://github.com/pantherale0
