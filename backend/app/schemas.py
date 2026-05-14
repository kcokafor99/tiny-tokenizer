from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.config import get_settings


class TokenizeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(..., min_length=0)
    tokenizer: str = Field(..., min_length=1, max_length=64)

    @field_validator("text")
    @classmethod
    def _length_check(cls, v: str) -> str:
        cap = get_settings().max_prompt_chars
        if len(v) > cap:
            raise ValueError(f"text exceeds maximum of {cap} characters")
        return v

    @field_validator("tokenizer")
    @classmethod
    def _slug(cls, v: str) -> str:
        if not v.replace("-", "").replace("_", "").replace(".", "").isalnum():
            raise ValueError("tokenizer slug must be alphanumeric (with -, _, .)")
        return v


class TokenInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    bytes_hex: str = Field(..., description="Hex-encoded raw token bytes")
    display: str = Field(..., description="UTF-8 decoded if valid, else hex fallback")
    valid_utf8: bool


class TokenizeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tokenizer: str
    token_count: int
    tokens: list[TokenInfo]
    duration_ms: float


class HealthResponse(BaseModel):
    status: str
    version: str
