"""SSML builder utility for Azure Speech TTS."""

from xml.sax import saxutils


def generate_ssml(
    text: str,
    voice: str,
    language: str = "en-US",
    pitch: str = "default",
    rate: str = "default",
    *,
    style: str | None = None,
) -> str:
    """Generate valid SSML XML payload for Azure Speech TTS REST API.

    :param text: Text string or raw SSML to speak.
    :param voice: Voice short name (e.g. en-US-AvaMultilingualNeural).
    :param language: Language BCP-47 tag (e.g. en-US).
    :param pitch: Pitch string (e.g. default, +10%, -10%).
    :param rate: Rate string (e.g. default, 1.1, 0.9).
    :param style: Optional speaking style (mstts:express-as), e.g. agent. Empty or None adds no wrapper.
    :return: Formatted SSML XML string.
    """
    stripped = text.strip()
    if stripped.startswith("<speak") and stripped.endswith("</speak>"):
        return stripped

    escaped_text = saxutils.escape(text)
    style = (style or "").strip()

    if not style:
        return (
            "<speak version='1.0' "
            f"xml:lang='{language}' "
            "xmlns='http://www.w3.org/2001/10/synthesis' "
            "xmlns:mstts='http://www.w3.org/2001/mstts'>\n"
            f"  <voice name='{voice}'>\n"
            f"    <prosody rate='{rate}' pitch='{pitch}'>\n"
            f"      {escaped_text}\n"
            "    </prosody>\n"
            "  </voice>\n"
            "</speak>"
        )

    escaped_style = saxutils.quoteattr(style)
    return (
        "<speak version='1.0' "
        f"xml:lang='{language}' "
        "xmlns='http://www.w3.org/2001/10/synthesis' "
        "xmlns:mstts='https://www.w3.org/2001/mstts'>\n"
        f"  <voice name='{voice}'>\n"
        f"    <mstts:express-as style={escaped_style}>\n"
        f"      <prosody rate='{rate}' pitch='{pitch}'>\n"
        f"        {escaped_text}\n"
        "      </prosody>\n"
        "    </mstts:express-as>\n"
        "  </voice>\n"
        "</speak>"
    )
