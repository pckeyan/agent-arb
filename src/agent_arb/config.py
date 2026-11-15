"""User configuration: where the model is and the defaults for a review."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("AGENT_ARB_CONFIG_DIR", Path.home() / ".config" / "agent-arb"))
CONFIG_PATH = CONFIG_DIR / "config.toml"

DEFAULT_TOML = """# Agent ARB configuration
[model]
# Any OpenAI-compatible endpoint. Ollama is the default.
base_url = "http://localhost:11434/v1"
name = "llama3.2:3b"
api_key = ""
timeout_seconds = 180

[review]
# Service tier when the document does not state one: 1 is most critical.
default_tier = 2
# Ask the author to justify each decision before showing findings.
challenge_mode = false
"""


@dataclass
class ModelConfig:
    base_url: str = "http://localhost:11434/v1"
    name: str = "llama3.2:3b"
    api_key: str = ""
    timeout_seconds: float = 180


@dataclass
class ReviewConfig:
    default_tier: int = 2
    challenge_mode: bool = False


@dataclass
class Config:
    model: ModelConfig = field(default_factory=ModelConfig)
    review: ReviewConfig = field(default_factory=ReviewConfig)


def load_config(path: Path = CONFIG_PATH) -> Config:
    if not path.exists():
        return Config()
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    m = data.get("model", {})
    r = data.get("review", {})
    return Config(
        model=ModelConfig(
            base_url=m.get("base_url", ModelConfig.base_url),
            name=m.get("name", ModelConfig.name),
            api_key=m.get("api_key", ""),
            timeout_seconds=float(m.get("timeout_seconds", 180)),
        ),
        review=ReviewConfig(
            default_tier=int(r.get("default_tier", 2)),
            challenge_mode=bool(r.get("challenge_mode", False)),
        ),
    )


def write_default_config(path: Path = CONFIG_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(DEFAULT_TOML, encoding="utf-8")
    return path
