"""
Mimo audio/video generation client.
"""

from __future__ import annotations

import base64
import os
from typing import Any, Optional

import httpx


class MimoMediaClient:
    """Call Xiaomi Mimo endpoints for audio/video generation."""

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        audio_endpoint: Optional[str] = None,
        video_endpoint: Optional[str] = None,
        timeout: float = 60.0,
    ):
        self.base_url = (base_url or os.getenv("MIMO_BASE_URL", "").strip() or "https://api.xiaomimimo.com/v1").rstrip("/")
        self.api_key = (api_key or os.getenv("MIMO_API_KEY", "").strip())
        self.audio_endpoint = (audio_endpoint or os.getenv("MIMO_AUDIO_ENDPOINT", "").strip() or "/audio/speech")
        self.video_endpoint = (video_endpoint or os.getenv("MIMO_VIDEO_ENDPOINT", "").strip())
        self.audio_model = os.getenv("MIMO_AUDIO_MODEL", "").strip()
        self.video_model = os.getenv("MIMO_VIDEO_MODEL", "").strip()
        self.timeout = timeout

    def describe(self) -> dict[str, Any]:
        return {
            "provider": "mimo",
            "base_url": self.base_url,
            "audio_endpoint": self.audio_endpoint,
            "video_endpoint": self.video_endpoint,
            "audio_model": self.audio_model,
            "video_model": self.video_model,
            "audio_configured": bool(self.api_key and self.audio_endpoint),
            "video_configured": bool(self.api_key and self.video_endpoint),
        }

    def synthesize_audio(
        self,
        *,
        text: str,
        voice: str = "default",
        response_format: str = "mp3",
        speed: float = 1.0,
        model: str = "",
    ) -> dict[str, Any]:
        if not self.api_key:
            return {"status": "not_configured", "error": "MIMO_API_KEY 未配置"}
        if not self.audio_endpoint:
            return {"status": "not_configured", "error": "MIMO_AUDIO_ENDPOINT 未配置"}

        payload = {
            "model": model or self.audio_model or "mimo-v2-pro",
            "input": text,
            "voice": voice,
            "response_format": response_format,
            "speed": speed,
        }
        response = self._request_binary("POST", self.audio_endpoint, json=payload)
        return {
            "status": "ok",
            "content_type": response.get("content_type", ""),
            "audio": response.get("bytes"),
            "payload": payload,
        }

    def generate_video(
        self,
        *,
        prompt: str,
        model: str = "",
        size: str = "1280x720",
        duration: int = 6,
        fps: int = 24,
        seed: Optional[int] = None,
    ) -> dict[str, Any]:
        if not self.api_key:
            return {"status": "not_configured", "error": "MIMO_API_KEY 未配置"}
        if not self.video_endpoint:
            return {"status": "not_configured", "error": "MIMO_VIDEO_ENDPOINT 未配置"}

        payload: dict[str, Any] = {
            "model": model or self.video_model or "mimo-video",
            "prompt": prompt,
            "size": size,
            "duration": duration,
            "fps": fps,
        }
        if seed is not None:
            payload["seed"] = seed

        response = self._request_json("POST", self.video_endpoint, json=payload)
        return {
            "status": "ok",
            "payload": payload,
            "response": response,
        }

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _request_json(self, method: str, path: str, *, json: dict[str, Any]) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.request(
                method,
                f"{self.base_url}{path}",
                json=json,
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    def _request_binary(self, method: str, path: str, *, json: dict[str, Any]) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.request(
                method,
                f"{self.base_url}{path}",
                json=json,
                headers=self._headers(),
            )
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            if "application/json" in content_type:
                data = resp.json()
                audio_b64 = data.get("audio") or data.get("b64_audio") or data.get("data")
                if isinstance(audio_b64, dict):
                    audio_b64 = audio_b64.get("b64") or audio_b64.get("b64_json")
                if isinstance(audio_b64, list):
                    audio_b64 = audio_b64[0].get("b64") if audio_b64 else None
                if not audio_b64:
                    raise RuntimeError("未在 JSON 响应中找到音频内容")
                return {"bytes": base64.b64decode(audio_b64), "content_type": "audio/mpeg"}
            return {"bytes": resp.content, "content_type": content_type or "audio/mpeg"}
