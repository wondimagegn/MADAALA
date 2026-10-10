"""Local Ollama HTTP API provider (default http://localhost:11434)."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Any

from ethiocontexteval.providers.base import (
    GenerationResult,
    ModelInfo,
    ModelProvider,
    ProviderError,
)


class OllamaProvider(ModelProvider):
    """
    Talks to a local Ollama daemon only.

    Does not pull/download models automatically.
    Does not expose or bind remote interfaces.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        *,
        timeout_seconds: float = 120.0,
        open_url: Any | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        # injectable for tests
        self._open = open_url or urllib.request.urlopen

    def provider_name(self) -> str:
        return "ollama"

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        url = f"{self.base_url}{path}"
        data = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with self._open(req, timeout=self.timeout_seconds) as resp:
                body = resp.read().decode("utf-8")
                if not body.strip():
                    return {}
                return json.loads(body)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace") if exc.fp else str(exc)
            raise ProviderError(f"Ollama HTTP {exc.code} at {path}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise ProviderError(
                f"Cannot reach Ollama at {self.base_url}: {exc.reason}. "
                "Is Ollama installed and running locally?"
            ) from exc
        except TimeoutError as exc:
            raise ProviderError(f"Ollama request timed out at {path}") from exc

    def health_check(self) -> dict[str, Any]:
        try:
            # /api/tags is the standard lightweight local probe
            payload = self._request("GET", "/api/tags")
            models = []
            if isinstance(payload, dict):
                models = payload.get("models") or []
            return {
                "ok": True,
                "message": f"Ollama reachable at {self.base_url}",
                "provider": "ollama",
                "base_url": self.base_url,
                "installed_model_count": len(models) if isinstance(models, list) else 0,
            }
        except ProviderError as exc:
            return {
                "ok": False,
                "message": str(exc),
                "provider": "ollama",
                "base_url": self.base_url,
            }

    def list_models(self) -> list[ModelInfo]:
        payload = self._request("GET", "/api/tags")
        if not isinstance(payload, dict):
            return []
        out: list[ModelInfo] = []
        for item in payload.get("models") or []:
            if not isinstance(item, dict):
                continue
            mid = str(item.get("name") or item.get("model") or "").strip()
            if not mid:
                continue
            out.append(
                ModelInfo(
                    model_id=mid,
                    name=mid,
                    provider="ollama",
                    metadata={
                        k: item.get(k)
                        for k in ("size", "digest", "modified_at", "details")
                        if k in item
                    },
                )
            )
        return out

    def ensure_model_available(self, model_id: str) -> None:
        models = self.list_models()
        ids = {m.model_id for m in models}
        if model_id in ids:
            return
        # Ollama often lists "name:tag"; allow matching bare name if unique tag not required
        bare = model_id.split(":")[0]
        matches = [i for i in ids if i == model_id or i.startswith(bare + ":") or i == bare]
        if matches:
            return
        sample = ", ".join(sorted(ids)[:12]) if ids else "(none installed)"
        raise ProviderError(
            f"Ollama model '{model_id}' is not installed locally. "
            f"Install it manually with: ollama pull {model_id} "
            f"(this project will not auto-download). Installed: {sample}"
        )

    def generate(
        self,
        model_id: str,
        prompt: str,
        *,
        temperature: float = 0.0,
        max_tokens: int = 500,
        seed: int | None = 0,
        **kwargs: Any,
    ) -> GenerationResult:
        ts = datetime.now(UTC).isoformat()
        options: dict[str, Any] = {
            "temperature": float(temperature),
            "num_predict": int(max_tokens),
        }
        if seed is not None:
            options["seed"] = int(seed)
        # allow caller overrides without inventing tokens
        extra_opts = kwargs.get("options")
        if isinstance(extra_opts, dict):
            options.update(extra_opts)

        body = {
            "model": model_id,
            "prompt": prompt,
            "stream": False,
            "options": options,
        }
        started = time.perf_counter()
        try:
            raw = self._request("POST", "/api/generate", body)
            latency = time.perf_counter() - started
            if not isinstance(raw, dict):
                return GenerationResult(
                    provider="ollama",
                    model_id=model_id,
                    response=None,
                    latency_seconds=round(latency, 4),
                    timestamp=ts,
                    status="error",
                    error="Unexpected Ollama response type",
                    provider_metadata={},
                )
            text = raw.get("response")
            # Ollama may return eval counts — only record if present
            prompt_eval = raw.get("prompt_eval_count")
            eval_count = raw.get("eval_count")
            in_tok = int(prompt_eval) if prompt_eval is not None else None
            out_tok = int(eval_count) if eval_count is not None else None
            total = None
            if in_tok is not None and out_tok is not None:
                total = in_tok + out_tok
            done_reason = raw.get("done_reason")
            meta = {
                k: raw.get(k)
                for k in (
                    "created_at",
                    "done",
                    "total_duration",
                    "load_duration",
                    "prompt_eval_duration",
                    "eval_duration",
                    "context",
                )
                if k in raw and k != "context"
            }
            # drop huge context arrays from stored metadata
            return GenerationResult(
                provider="ollama",
                model_id=str(raw.get("model") or model_id),
                response=str(text) if text is not None else None,
                latency_seconds=round(latency, 4),
                input_tokens=in_tok,
                output_tokens=out_tok,
                total_tokens=total,
                finish_reason=str(done_reason) if done_reason is not None else (
                    "stop" if raw.get("done") else None
                ),
                timestamp=ts,
                status="ok" if text is not None else "error",
                error=None if text is not None else "Empty response from Ollama",
                provider_metadata=meta,
            )
        except ProviderError as exc:
            latency = time.perf_counter() - started
            return GenerationResult(
                provider="ollama",
                model_id=model_id,
                response=None,
                latency_seconds=round(latency, 4),
                timestamp=ts,
                status="error",
                error=str(exc),
                provider_metadata={"base_url": self.base_url},
            )
