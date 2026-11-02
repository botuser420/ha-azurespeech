"""Tests for the SSML builder."""

from xml.etree import ElementTree as ET

from custom_components.azure_speech.entity_utils import generate_ssml

MSTTS_NS = "https://www.w3.org/2001/mstts"


def test_ssml_without_style_has_no_express_as() -> None:
    """No style (None, empty or blank) keeps the SSML unchanged."""
    baseline = generate_ssml("Hello", "en-US-AvaMultilingualNeural")
    assert "express-as" not in baseline
    assert "https://www.w3.org/2001/mstts" not in baseline
    assert generate_ssml("Hello", "en-US-AvaMultilingualNeural", style=None) == baseline
    assert generate_ssml("Hello", "en-US-AvaMultilingualNeural", style="") == baseline
    assert generate_ssml("Hello", "en-US-AvaMultilingualNeural", style="   ") == baseline


def test_ssml_with_style_wraps_text_in_express_as() -> None:
    """A style wraps the text in mstts:express-as and declares the namespace."""
    ssml = generate_ssml("Hallo", "nl-NL-Grant:MAI-Voice-2.1", language="nl-NL", style="agent")
    assert f"xmlns:mstts='{MSTTS_NS}'" in ssml
    root = ET.fromstring(ssml)  # noqa: S314
    voice = root.find("{http://www.w3.org/2001/10/synthesis}voice")
    assert voice is not None
    assert voice.get("name") == "nl-NL-Grant:MAI-Voice-2.1"
    express = voice.find(f"{{{MSTTS_NS}}}express-as")
    assert express is not None
    assert express.get("style") == "agent"
    prosody = express.find("{http://www.w3.org/2001/10/synthesis}prosody")
    assert prosody is not None
    assert (prosody.text or "").strip() == "Hallo"


def test_ssml_style_attribute_is_escaped() -> None:
    """Quotes and markup in the style cannot break out of the attribute."""
    ssml = generate_ssml("Hi", "v", style="a\"b'<&>")
    root = ET.fromstring(ssml)  # noqa: S314
    express = root.find(f".//{{{MSTTS_NS}}}express-as")
    assert express is not None
    assert express.get("style") == "a\"b'<&>"


def test_ssml_style_ignored_for_raw_ssml() -> None:
    """A complete <speak> document passes through untouched."""
    raw = "<speak version='1.0'>x</speak>"
    assert generate_ssml(raw, "v", style="agent") == raw
