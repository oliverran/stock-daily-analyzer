"""Offline tests: no real model, quote provider, email or trades."""
import json
from unittest.mock import Mock

import pytest

import llm
from reporting import generate_report


@pytest.fixture
def contexts(monkeypatch):
    pool = [{"ticker": "000001.SZ", "name": "Demo A", "rsi": 30},
            {"ticker": "000002.SZ", "name": "Demo B", "rsi": 40}]
    monkeypatch.setattr(llm, "llm_enabled", lambda: True)
    monkeypatch.setattr(llm, "_gather_stock_context", lambda stock: stock)
    monkeypatch.setattr(llm.requests, "post", Mock(side_effect=AssertionError("network forbidden")))
    return pool


@pytest.mark.parametrize("value", [
    ["bad"], "bad", True, 1, None, {}, [],
    {"ticker": "OUTSIDE", "name": "fake", "reason": "test"},
    {"ticker": "000001.SZ", "name": "A", "reason": []},
    {"ticker": "000001.SZ", "name": "A", "reason": " "},
    {"ticker": ["000001.SZ"], "name": "A", "reason": "test"},
    {"ticker": "000001.SZ", "name": "A", "reason": "x" * 2001},
])
def test_invalid_pick_falls_back_with_label(monkeypatch, contexts, value):
    monkeypatch.setattr(llm, "_call_ark", lambda prompt: value)
    result = llm.select_top_picks({"超卖反弹": contexts})
    assert result["超卖反弹"]["ticker"] == "000001.SZ"
    assert "校验未通过" in result["超卖反弹"]["reason"]
    report = generate_report(None, [], {}, result)
    assert "待研究标的" in report
    assert "最值得买" not in report


def test_valid_pick_uses_canonical_name_and_discards_extra_fields(monkeypatch, contexts):
    monkeypatch.setattr(llm, "_call_ark", lambda prompt: {
        "ticker": "000002.SZ", "name": "invented", "reason": " test ", "other": "ignored"})
    result = llm.select_top_picks({"test": contexts})
    assert result == {"test": {"ticker": "000002.SZ", "name": "Demo B", "reason": "test"}}


def test_membership_is_category_specific(monkeypatch, contexts):
    monkeypatch.setattr(llm, "_call_ark", lambda prompt: {
        "ticker": "000002.SZ", "name": "Demo B", "reason": "test"})
    result = llm.select_top_picks({"A": contexts[:1], "B": contexts[1:], "empty": []})
    assert result["A"]["ticker"] == "000001.SZ"
    assert "规则回退" in result["A"]["reason"]
    assert result["B"]["reason"] == "test"
    assert "empty" not in result


def test_disabled_llm_does_not_gather(monkeypatch):
    monkeypatch.setattr(llm, "llm_enabled", lambda: False)
    gather = Mock(side_effect=AssertionError("no gathering"))
    monkeypatch.setattr(llm, "_gather_stock_context", gather)
    assert llm.select_top_picks({"test": [{}]}) == {}


@pytest.mark.parametrize("value", [[], ["bad"], "bad", True, 1, None, {"reason": "ok"}])
def test_call_ark_only_returns_objects(monkeypatch, value):
    monkeypatch.setenv("ARK_API_KEY", "test-key")
    monkeypatch.setenv("ARK_MODEL_ID", "test-model")
    response = Mock()
    response.json.return_value = {"choices": [{"message": {"content": json.dumps(value)}}]}
    monkeypatch.setattr(llm.requests, "post", Mock(return_value=response))
    assert llm._call_ark("test") == (value if isinstance(value, dict) else None)


@pytest.mark.parametrize("value", [1, ["bad"], {"summary": []}, {"summary": " "}])
def test_bad_attribution_and_news_shapes_are_safe(monkeypatch, value):
    monkeypatch.setattr(llm, "_call_ark", lambda prompt: value)
    assert llm._summarize_attribution_with_llm("demo", "price moved", ["headline"]) == "无法生成归因总结。"
    assert llm._filter_news_with_llm("demo", ["headline"]) == ["headline"]


def test_missing_evidence_and_unverified_summary_label(monkeypatch):
    call = Mock(return_value={"summary": "无法确认"})
    monkeypatch.setattr(llm, "_call_ark", call)
    assert "证据不足" in llm._summarize_attribution_with_llm("demo", "price moved", [])
    call.assert_not_called()
    assert "非已证实归因" in llm._summarize_attribution_with_llm("demo", "price moved", ["headline"])
    assert "不得补造" in call.call_args.args[0]


def test_report_omits_non_dict_selection():
    assert "已省略" in generate_report(None, [], {}, {"test": ["bad"]})
