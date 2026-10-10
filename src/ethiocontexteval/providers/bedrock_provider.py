"""Optional Amazon Bedrock provider (funded / cloud study path)."""

from __future__ import annotations

from typing import Any

from ethiocontexteval.providers.base import (
    GenerationResult,
    ModelInfo,
    ModelProvider,
    ProviderError,
)


class BedrockProvider(ModelProvider):
    """
    Optional AWS Bedrock backend.

    Requires optional dependency group: pip install -e ".[aws]"
    Credentials via standard boto3 chain only — never hard-coded.

    Planned for the funded study when AWS research infrastructure is available.
    The preliminary local pilot does not require this provider.
    """

    def __init__(
        self,
        region_name: str = "us-east-1",
        *,
        client: Any | None = None,
        **kwargs: Any,
    ) -> None:
        self.region_name = region_name
        self._client = client
        self._client_kwargs = kwargs

    def provider_name(self) -> str:
        return "bedrock"

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from ethiocontexteval.bedrock_client import BedrockClient
        except ImportError as exc:  # pragma: no cover
            raise ProviderError(
                "Bedrock support requires optional AWS deps. "
                'Install with: pip install -e ".[aws]"'
            ) from exc
        try:
            import boto3  # noqa: F401
        except ImportError as exc:
            raise ProviderError(
                "boto3 is not installed. Install optional AWS extras: "
                'pip install -e ".[aws]"'
            ) from exc
        self._client = BedrockClient(region_name=self.region_name, **self._client_kwargs)
        return self._client

    def health_check(self) -> dict[str, Any]:
        try:
            client = self._get_client()
            models = client.list_foundation_models()
            return {
                "ok": True,
                "message": f"Bedrock reachable in {self.region_name}",
                "provider": "bedrock",
                "region": self.region_name,
                "foundation_model_count": len(models),
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "message": str(exc),
                "provider": "bedrock",
                "region": self.region_name,
            }

    def list_models(self) -> list[ModelInfo]:
        client = self._get_client()
        raw = client.list_foundation_models()
        out: list[ModelInfo] = []
        for item in raw:
            mid = item.get("model_id")
            if not mid:
                continue
            out.append(
                ModelInfo(
                    model_id=str(mid),
                    name=item.get("model_name"),
                    provider=str(item.get("provider") or "bedrock"),
                    metadata={
                        k: item.get(k)
                        for k in (
                            "input_modalities",
                            "output_modalities",
                            "inference_types",
                            "lifecycle",
                            "model_arn",
                        )
                        if k in item
                    },
                )
            )
        return out

    def ensure_model_available(self, model_id: str) -> None:
        client = self._get_client()
        try:
            client.ensure_model_available(model_id)
        except RuntimeError as exc:
            raise ProviderError(str(exc)) from exc

    def generate(
        self,
        model_id: str,
        prompt: str,
        *,
        temperature: float = 0.0,
        max_tokens: int = 500,
        **kwargs: Any,
    ) -> GenerationResult:
        client = self._get_client()
        system = kwargs.get("system")
        result = client.converse(
            model_id=model_id,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
        )
        return GenerationResult(
            provider="bedrock",
            model_id=result.model_id,
            response=result.response_text,
            latency_seconds=result.latency_seconds,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            total_tokens=result.total_tokens,
            finish_reason=result.raw_stop_reason,
            timestamp=result.timestamp,
            status=result.status,
            error=result.error,
            provider_metadata={"region": self.region_name},
        )
