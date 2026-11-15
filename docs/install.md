# Install

## CLI

Only [`uv`](https://docs.astral.sh/uv/) is required. It fetches Python 3.12 if the machine lacks it.

```bash
uv tool install agent-arb
agent-arb init
```

`init` writes `~/.config/agent-arb/config.toml` and checks that the model endpoint answers. The default endpoint is Ollama at `http://localhost:11434/v1` with `llama3.2:3b`. Larger models review better; set `[model].name` to any model your endpoint serves. Any OpenAI-compatible server works: vLLM, LM Studio, llama.cpp server.

Upgrade with `uv tool upgrade agent-arb`.

### Air-gapped

Copy the wheel from a GitHub release and the model file, then:

```bash
uv tool install ./agent_arb-<version>-py3-none-any.whl
```

## Skill

```bash
npx skills add pckeyan/agent-arb@agent-arb -g
```

Or copy `skills/agent-arb/` into `~/.claude/skills/` for Claude Code, `~/.codex/skills/` for Codex, or a project's `.claude/skills/`. The folder needs a Python 3 interpreter on the path for its three scripts and nothing else. It does not need the CLI.

Compiled company packs for the skill are JSON files. Compile and approve with the CLI, then convert:

```bash
agent-arb rules compile standards.pdf --out acme.yaml
agent-arb rules approve acme.yaml --reviewer "your name"
python -c "import yaml,json,sys; json.dump(yaml.safe_load(open('acme.yaml')), open('acme.json','w'), indent=1)"
```

Point the skill at the folder holding `acme.json` when it asks for company packs.
