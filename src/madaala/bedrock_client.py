"""Amazon Bedrock client for MADAALA (credentials via boto3 chain only)."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

# Errors that are often transient
_RETRYABLE_CODES = {
    "ThrottlingException",
    "TooManyRequestsException",
    "ServiceUnavailableException",
    "ModelTimeoutException",
    "InternalServerException",
    "RequestTimeout",
}


@dataclass
class GenerationResult:
    """Structured result from a single Converse call."""

    response_text: str | None
    latency_seconds: float
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    timestamp: str
    model_id: str
    raw_stop_reason: str | None
    error: str | None
    status: str  # ok | error

    def usage_dict(self) -> dict[str, Any]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "latency_seconds": self.latency_seconds,
            "timestamp": self.timestamp,
            "stop_reason": self.raw_stop_reason,
            "error": self.error,
            "status": self.status,
        }


class BedrockClient:
    """
    Thin wrapper around Bedrock Runtime Converse API.

    Authentication uses the default boto3 credential provider chain.
    Never pass long-lived keys through this class constructor.
    """

    def __init__(
        self,
        region_name: str = "us-east-1",
        *,
        profile_name: str | None = None,
        max_retries: int = 4,
        base_backoff_seconds: float = 1.0,
        max_backoff_seconds: float = 20.0,
        runtime_client: Any | None = None,
        control_client: Any | None = None,
    ) -> None:
        self.region_name = region_name
        self.profile_name = profile_name
        self.max_retries = max_retries
        self.base_backoff_seconds = base_backoff_seconds
        self.max_backoff_seconds = max_backoff_seconds
        if runtime_client is not None:
            self._runtime = runtime_client
        else:
            session = boto3.Session(profile_name=profile_name, region_name=region_name)
            self._runtime = session.client("bedrock-runtime")
        if control_client is not None:
            self._control = control_client
        else:
            session = boto3.Session(profile_name=profile_name, region_name=region_name)
            self._control = session.client("bedrock")

    def list_foundation_models(self, *, by_provider: str | None = None) -> list[dict[str, Any]]:
        """List foundation models via Bedrock control-plane API."""
        kwargs: dict[str, Any] = {}
        if by_provider:
            kwargs["byProvider"] = by_provider
        try:
            response = self._control.list_foundation_models(**kwargs)
        except ClientError as exc:
            raise RuntimeError(
                f"Unable to list Bedrock foundation models in {self.region_name}: {exc}"
            ) from exc
        models = []
        for summary in response.get("modelSummaries", []):
            input_mods = summary.get("inputModalities") or []
            output_mods = summary.get("outputModalities") or []
            models.append(
                {
                    "provider": summary.get("providerName"),
                    "model_name": summary.get("modelName"),
                    "model_id": summary.get("modelId"),
                    "model_arn": summary.get("modelArn"),
                    "input_modalities": list(input_mods),
                    "output_modalities": list(output_mods),
                    "response_streaming": summary.get("responseStreamingSupported"),
                    "customizations": summary.get("customizationsSupported"),
                    "inference_types": summary.get("inferenceTypesSupported"),
                    "lifecycle": summary.get("modelLifecycle", {}).get("status")
                    if isinstance(summary.get("modelLifecycle"), dict)
                    else summary.get("modelLifecycle"),
                }
            )
        return models

    def is_model_available(self, model_id: str) -> bool:
        """Return True if model_id appears in list_foundation_models (exact ID)."""
        try:
            models = self.list_foundation_models()
        except RuntimeError:
            return False
        ids = {m["model_id"] for m in models if m.get("model_id")}
        if model_id in ids:
            return True
        return False

    def ensure_model_available(self, model_id: str) -> None:
        if not self.is_model_available(model_id):
            raise RuntimeError(
                f"Model '{model_id}' was not discovered in {self.region_name}. Check the exact ID/region or use --skip-model-check for an independently verified inference profile. Discovery does not establish runtime capacity."
            )

    def converse(
        self,
        *,
        model_id: str,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.0,
        system: str | None = None,
    ) -> GenerationResult:
        """
        Call Bedrock Runtime Converse with bounded exponential backoff.

        Does not retry indefinitely. Non-retryable errors fail immediately.
        """
        messages = [{"role": "user", "content": [{"text": prompt}]}]
        inference = {
            "maxTokens": int(max_tokens),
            "temperature": float(temperature),
        }
        kwargs: dict[str, Any] = {
            "modelId": model_id,
            "messages": messages,
            "inferenceConfig": inference,
        }
        if system:
            kwargs["system"] = [{"text": system}]

        attempt = 0
        last_error: str | None = None
        while attempt <= self.max_retries:
            attempt += 1
            started = time.perf_counter()
            ts = datetime.now(UTC).isoformat()
            try:
                response = self._runtime.converse(**kwargs)
                latency = time.perf_counter() - started
                text = _extract_text(response)
                usage = response.get("usage") or {}
                in_tok = usage.get("inputTokens")
                out_tok = usage.get("outputTokens")
                total = usage.get("totalTokens")
                if total is None and in_tok is not None and out_tok is not None:
                    total = int(in_tok) + int(out_tok)
                return GenerationResult(
                    response_text=text,
                    latency_seconds=round(latency, 4),
                    input_tokens=int(in_tok) if in_tok is not None else None,
                    output_tokens=int(out_tok) if out_tok is not None else None,
                    total_tokens=int(total) if total is not None else None,
                    timestamp=ts,
                    model_id=model_id,
                    raw_stop_reason=response.get("stopReason"),
                    error=None,
                    status="ok",
                )
            except ClientError as exc:
                latency = time.perf_counter() - started
                code = exc.response.get("Error", {}).get("Code", "ClientError")
                last_error = format_aws_error(exc)
                if code in _RETRYABLE_CODES and attempt <= self.max_retries:
                    _sleep_backoff(
                        attempt,
                        self.base_backoff_seconds,
                        self.max_backoff_seconds,
                    )
                    continue
                return GenerationResult(
                    response_text=None,
                    latency_seconds=round(latency, 4),
                    input_tokens=None,
                    output_tokens=None,
                    total_tokens=None,
                    timestamp=ts,
                    model_id=model_id,
                    raw_stop_reason=None,
                    error=last_error,
                    status="error",
                )
            except (BotoCoreError, Exception) as exc:  # noqa: BLE001 â€” surface as result
                latency = time.perf_counter() - started
                last_error = format_aws_error(exc)
                if attempt <= self.max_retries and _is_retryable_message(last_error):
                    _sleep_backoff(
                        attempt,
                        self.base_backoff_seconds,
                        self.max_backoff_seconds,
                    )
                    continue
                return GenerationResult(
                    response_text=None,
                    latency_seconds=round(latency, 4),
                    input_tokens=None,
                    output_tokens=None,
                    total_tokens=None,
                    timestamp=ts,
                    model_id=model_id,
                    raw_stop_reason=None,
                    error=last_error,
                    status="error",
                )

        return GenerationResult(
            response_text=None,
            latency_seconds=0.0,
            input_tokens=None,
            output_tokens=None,
            total_tokens=None,
            timestamp=datetime.now(UTC).isoformat(),
            model_id=model_id,
            raw_stop_reason=None,
            error=last_error or "unknown error after retries",
            status="error",
        )


def _extract_text(response: dict[str, Any]) -> str:
    output = response.get("output") or {}
    message = output.get("message") or {}
    parts = message.get("content") or []
    texts: list[str] = []
    for part in parts:
        if isinstance(part, dict) and "text" in part:
            texts.append(str(part["text"]))
    return "\n".join(texts).strip()


def _sleep_backoff(attempt: int, base: float, cap: float) -> None:
    # attempt is 1-based after failure
    delay = min(cap, base * (2 ** (attempt - 1)))
    delay = delay * (0.5 + random.random())  # jitter
    time.sleep(delay)


def _is_retryable_message(message: str) -> bool:
    lowered = message.lower()
    return any(
        token in lowered
        for token in ("throttl", "timeout", "temporarily", "unavailable", "too many")
    )


def format_aws_error(exc: Exception) -> str:
    code = type(exc).__name__
    message = str(exc)
    if isinstance(exc, ClientError):
        code = exc.response.get("Error", {}).get("Code", code)
        message = exc.response.get("Error", {}).get("Message", message)
    explanations = {
        "NoCredentialsError": "AWS credentials were not found.",
        "AccessDeniedException": "AWS credentials are valid but Bedrock access was denied.",
        "ResourceNotFoundException": "The selected model/profile is not available.",
        "ThrottlingException": "Check account/model runtime quota (RPM/TPM and daily tokens) in the selected region.",
    }
    return f"{code}: {message} {explanations.get(code, '')}".strip()
