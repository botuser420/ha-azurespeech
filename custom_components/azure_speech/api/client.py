"""Azure Speech API client implementation using aiohttp."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any, Final

import aiohttp

from .exceptions import (
    AzureSpeechApiClientAuthenticationError,
    AzureSpeechApiClientCommunicationError,
    AzureSpeechApiClientError,
    AzureSpeechApiClientRateLimitError,
)

TIMEOUT: Final = 15


class AzureSpeechApiClient:
    """API client for communicating with Azure Speech REST APIs."""

    def __init__(
        self,
        api_key: str,
        region: str,
        session: aiohttp.ClientSession,
        endpoint: str | None = None,
    ) -> None:
        """Initialize the Azure Speech API client.

        :param api_key: Azure Cognitive Services API Key.
        :param region: Azure Region (e.g. eastus, westeurope).
        :param session: aiohttp ClientSession provided by Home Assistant.
        :param endpoint: Optional custom endpoint base URL.
        """
        self._api_key = api_key
        self._region = region
        self._session = session
        self._endpoint = endpoint.rstrip("/") if endpoint else None

    @property
    def tts_base_url(self) -> str:
        """Get the base URL for Azure TTS services."""
        if self._endpoint:
            return self._endpoint
        return f"https://{self._region}.tts.speech.microsoft.com"

    @property
    def stt_base_url(self) -> str:
        """Get the base URL for Azure STT services."""
        if self._endpoint:
            return self._endpoint
        return f"https://{self._region}.stt.speech.microsoft.com"

    def _headers(self, extra_headers: dict[str, str] | None = None) -> dict[str, str]:
        """Generate base headers for API requests."""
        headers = {
            "Ocp-Apim-Subscription-Key": self._api_key,
            "User-Agent": "HomeAssistant-AzureSpeechIntegration/0.1.0",
        }
        if extra_headers:
            headers.update(extra_headers)
        return headers

    async def _handle_response_errors(self, response: aiohttp.ClientResponse) -> None:
        """Handle HTTP error status codes and raise integration exceptions."""
        if response.status in (401, 403):
            raise AzureSpeechApiClientAuthenticationError(
                f"Authentication failed (HTTP {response.status}): Invalid API key or region."
            )
        if response.status == 429:
            retry_after_hdr = response.headers.get("Retry-After")
            retry_after = int(retry_after_hdr) if retry_after_hdr and retry_after_hdr.isdigit() else 60
            raise AzureSpeechApiClientRateLimitError(retry_after=retry_after)
        if response.status >= 400:
            text = await response.text()
            raise AzureSpeechApiClientError(f"Azure Speech API error (HTTP {response.status}): {text}")

    async def get_voices(self) -> list[dict[str, Any]]:
        """Fetch the list of available neural voices for the configured region."""
        url = f"{self.tts_base_url}/cognitiveservices/voices/list"
        try:
            async with asyncio.timeout(TIMEOUT):
                response = await self._session.get(url, headers=self._headers())
                await self._handle_response_errors(response)
                voices: list[dict[str, Any]] = await response.json()
                return voices
        except TimeoutError as err:
            raise AzureSpeechApiClientCommunicationError(
                "Timeout while fetching voices list from Azure Speech API"
            ) from err
        except aiohttp.ClientError as err:
            raise AzureSpeechApiClientCommunicationError(f"Connection error fetching voices: {err}") from err

    async def generate_tts_audio(
        self,
        ssml_content: str,
        output_format: str = "audio-24khz-48kbitrate-mono-mp3",
    ) -> bytes:
        """Request TTS synthesis audio bytes from Azure Speech REST API.

        :param ssml_content: SSML XML payload string.
        :param output_format: X-Microsoft-OutputFormat header value.
        :return: Raw binary audio bytes (MP3, WAV, OPUS).
        """
        url = f"{self.tts_base_url}/cognitiveservices/v1"
        headers = self._headers(
            {
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": output_format,
            }
        )
        try:
            async with asyncio.timeout(TIMEOUT):
                response = await self._session.post(
                    url,
                    headers=headers,
                    data=ssml_content.encode("utf-8"),
                )
                await self._handle_response_errors(response)
                return await response.read()
        except TimeoutError as err:
            raise AzureSpeechApiClientCommunicationError("Timeout generating TTS audio from Azure Speech API") from err
        except aiohttp.ClientError as err:
            raise AzureSpeechApiClientCommunicationError(f"Connection error generating TTS audio: {err}") from err

    async def stream_tts_audio(
        self,
        ssml_content: str,
        output_format: str = "audio-24khz-48kbitrate-mono-mp3",
    ) -> AsyncIterator[bytes]:
        """Stream TTS synthesis audio from Azure Speech REST API as it arrives.

        Same endpoint, headers and SSML as `generate_tts_audio`, but the audio
        chunks are yielded in order while the response body is still being
        received. The connection is closed when the stream ends or the consumer
        stops iterating. Timeouts apply to connecting and to each read, not to
        the whole stream.

        :param ssml_content: SSML XML payload string.
        :param output_format: X-Microsoft-OutputFormat header value.
        :return: Async iterator of raw audio byte chunks (MP3, WAV, OPUS).
        """
        url = f"{self.tts_base_url}/cognitiveservices/v1"
        headers = self._headers(
            {
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": output_format,
            }
        )
        timeout = aiohttp.ClientTimeout(total=None, connect=TIMEOUT, sock_read=TIMEOUT)
        response: aiohttp.ClientResponse | None = None
        try:
            response = await self._session.post(
                url,
                headers=headers,
                data=ssml_content.encode("utf-8"),
                timeout=timeout,
            )
            await self._handle_response_errors(response)
            async for chunk in response.content.iter_any():
                if chunk:
                    yield chunk
        except TimeoutError as err:
            raise AzureSpeechApiClientCommunicationError("Timeout streaming TTS audio from Azure Speech API") from err
        except aiohttp.ClientError as err:
            raise AzureSpeechApiClientCommunicationError(f"Connection error streaming TTS audio: {err}") from err
        finally:
            if response is not None:
                response.close()

    async def transcribe_stt_audio(
        self,
        wav_audio_bytes: bytes,
        language: str = "en-US",
        profanity_mode: str = "masked",
    ) -> dict[str, Any]:
        """Transcribe short WAV audio stream to text via Azure STT REST API.

        :param wav_audio_bytes: Binary WAV PCM 16kHz audio stream.
        :param language: Language BCP-47 locale tag (e.g. en-US).
        :param profanity_mode: Profanity filter setting (masked, removed, raw).
        :return: Dict containing RecognitionStatus and DisplayText.
        """
        url = (
            f"{self.stt_base_url}/speech/recognition/conversation/cognitiveservices/v1"
            f"?language={language}&profanity={profanity_mode}"
        )
        headers = self._headers(
            {
                "Content-Type": "audio/wav; codecs=audio/pcm; samplerate=16000",
                "Accept": "application/json",
            }
        )
        try:
            async with asyncio.timeout(TIMEOUT):
                response = await self._session.post(
                    url,
                    headers=headers,
                    data=wav_audio_bytes,
                )
                await self._handle_response_errors(response)
                result: dict[str, Any] = await response.json()
                return result
        except TimeoutError as err:
            raise AzureSpeechApiClientCommunicationError("Timeout transcribing audio with Azure STT API") from err
        except aiohttp.ClientError as err:
            raise AzureSpeechApiClientCommunicationError(f"Connection error transcribing STT audio: {err}") from err
