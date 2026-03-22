# Setup Guide

This guide mirrors your phase spec and adds the machine-specific findings from this host.

## Phase 0: System preparation

Install Homebrew if needed:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

Install core dependencies:

```bash
brew install git node python@3.11
```

Verify:

```bash
node -v
python3 --version
git --version
```

Install Xcode command line tools:

```bash
xcode-select --install
```

Host reality on this machine:

- `node` is already installed as `v25.8.1`
- `python3` is already installed as `3.14.3`
- `openclaw` is already installed
- `ollama` client is already installed

The Python code in this repo targets Python 3.11+ and works on 3.14 as well.

## Phase 1: Ollama

Install and start Ollama if needed:

```bash
brew install ollama
brew services start ollama
ollama pull llama3:8b-instruct
ollama run llama3:8b-instruct
```

Test prompt:

```text
Explain what a JSON schema is in one paragraph.
```

If you want your repo scripts to target the same model id as the initial spec, set:

```bash
export AGENT_MODEL="llama3:8b-instruct"
```

## Phase 2: OpenClaw

Install if needed:

```bash
npm install -g openclaw@latest
openclaw onboard --install-daemon
openclaw status
```

On this machine, `openclaw status` already reports a running local gateway and an `ollama` provider configured in `~/.openclaw/openclaw.json`.

## Phase 3: OpenClaw + Ollama

The current host config shape uses `~/.openclaw/openclaw.json`, not `~/.openclaw/config.json`. A matching example file is included at [`config/openclaw.local.example.json`](/Users/chappie/Projects/Agent.Chappie/config/openclaw.local.example.json).

To apply it safely, merge only the relevant fields into `~/.openclaw/openclaw.json`:

- `models.providers.ollama.baseUrl`
- `models.providers.ollama.models`
- `agents.defaults.model.primary`
- `agents.defaults.models`

Recommended host validation:

```bash
openclaw status
openclaw run "Summarise the benefits of structured outputs."
```

## Phase 7: External model storage

For a 256GB internal SSD, move Ollama models to external storage:

```bash
export OLLAMA_MODELS=/Volumes/ExternalSSD/ollama
echo 'export OLLAMA_MODELS=/Volumes/ExternalSSD/ollama' >> ~/.zshrc
```

Clean unused models:

```bash
ollama rm <model>
```

## Security constraints

- keep OpenClaw bound to loopback only
- do not install public skills unless you explicitly trust them
- do not expose Ollama or OpenClaw ports externally
