"""Offline Bedrock contracts using injected clients; no credentials or network."""

from types import SimpleNamespace

from botocore.exceptions import ClientError

from ethiocontexteval.bedrock_client import BedrockClient
from ethiocontexteval.providers.bedrock_provider import BedrockProvider
from ethiocontexteval.quotas import inspect_quotas


def test_exact_discovery_and_provider_contract():
    control = SimpleNamespace(
        list_foundation_models=lambda **_: {"modelSummaries": [{"modelId": "model:1"}]}
    )
    client = BedrockClient(runtime_client=object(), control_client=control)
    provider = BedrockProvider(client=client)
    assert provider.is_model_available("model:1")
    assert not provider.is_model_available("model")
    assert not provider.is_model_available("model:2")


def test_converse_normalization_and_error():
    calls = []

    def converse(**kwargs):
        calls.append(kwargs)
        return {
            "output": {"message": {"content": [{"text": "hello"}]}},
            "usage": {"inputTokens": 2, "outputTokens": 3},
            "stopReason": "end_turn",
        }

    client = BedrockClient(
        runtime_client=SimpleNamespace(converse=converse), control_client=object(), max_retries=0
    )
    result = BedrockProvider(client=client).generate("model:1", "prompt", max_tokens=10)
    assert result.response == "hello"
    assert result.total_tokens == 5
    assert calls[0]["inferenceConfig"]["maxTokens"] == 10

    def fail(**kwargs):
        raise ClientError(
            {"Error": {"Code": "ThrottlingException", "Message": "Too many tokens per day"}},
            "Converse",
        )

    client._runtime = SimpleNamespace(converse=fail)
    result = client.converse(model_id="model:1", prompt="hello")
    assert result.status == "error"
    assert "Too many tokens per day" in result.error
    assert "quota" in result.error


def test_quota_pagination_is_advisory():
    paginator = SimpleNamespace(
        paginate=lambda **_: [
            {"Quotas": [{"QuotaName": "Qwen requests per minute", "Value": 0}]},
            {"Quotas": [{"QuotaName": "Other", "Value": 5}]},
        ]
    )
    report = inspect_quotas(SimpleNamespace(get_paginator=lambda _: paginator), "qwen")
    assert len(report["quotas"]) == 1
    assert report["zero_quota_warning"]
