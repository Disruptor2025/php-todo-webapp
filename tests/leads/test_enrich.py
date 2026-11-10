import anthropic
import httpx
import pytest
from pydantic import ValidationError

from leads.enrich import Enricher
from leads.models import Enrichment, Place
from tests.fakes import FakeClaude, good_enrichment

PLACE = Place(id="p1", name="Joe's Plumbing", phone="512-555-0100", rating=4.7, user_rating_count=80,
              opening_hours={"weekdayDescriptions": ["Monday: 8AM-5PM"]}, primary_type="plumber")


def validation_error():
    try:
        Enrichment(summary="x", services=["a"], site_sections=["a", "b", "c"], selling_points=["only one"],
                   tone="friendly")
    except ValidationError as e:
        return e


def test_returns_validated_enrichment():
    claude = FakeClaude(good_enrichment())
    result = Enricher(claude, "claude-opus-5-5").enrich(PLACE, "plumber", "Austin, TX", "none")
    assert result.tone == "family-run" and len(result.selling_points) == 3
    call = claude.calls[0]
    assert call["model"] == "claude-opus-5-5"
    assert call["output_format"] is Enrichment
    assert "Joe's Plumbing" in call["messages"][0]["content"]
    assert call["fallbacks"] == "default"


def test_retries_once_when_invalid_then_succeeds():
    claude = FakeClaude(validation_error(), good_enrichment())
    result = Enricher(claude, "claude-opus-5-5").enrich(PLACE, "plumber", "Austin", "none")
    assert result is not None
    assert len(claude.calls) == 2
    assert "previous answer was invalid" in claude.calls[1]["messages"][0]["content"]


def test_gives_up_after_one_retry():
    claude = FakeClaude(validation_error(), validation_error(), good_enrichment())
    assert Enricher(claude, "claude-opus-5-5").enrich(PLACE, "plumber", "Austin", "none") is None
    assert len(claude.calls) == 2  # never a third (paid) attempt


def test_missing_parsed_output_counts_as_invalid():
    claude = FakeClaude(("max_tokens", None), good_enrichment())
    assert Enricher(claude, "claude-opus-5-5").enrich(PLACE, "plumber", "Austin", "none") is not None


def test_refusal_returns_none_without_retry():
    claude = FakeClaude(("refusal", None))
    assert Enricher(claude, "claude-opus-5-5").enrich(PLACE, "plumber", "Austin", "none") is None
    assert len(claude.calls) == 1


def test_api_error_returns_none():
    err = anthropic.APIConnectionError(request=httpx.Request("POST", "https://api.anthropic.com"))
    claude = FakeClaude(err)
    assert Enricher(claude, "claude-opus-5-5").enrich(PLACE, "plumber", "Austin", "none") is None


def test_no_fallback_param_for_models_without_it():
    claude = FakeClaude(good_enrichment())
    Enricher(claude, "claude-haiku-5-5").enrich(PLACE, "plumber", "Austin", "none")
    assert "fallbacks" not in claude.calls[0]


def test_enrichment_model_rules():
    with pytest.raises(ValidationError):
        good_enrichment(tone="corporate")
    with pytest.raises(ValidationError):
        good_enrichment(selling_points=["a", "b"])
