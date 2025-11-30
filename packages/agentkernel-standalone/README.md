<p align="center">
  <img
    src="../../assets/agentkernel_logo.png"
    width="400"
  />
</p>

# Agent-Kernel Standalone

**Agent-Kernel Standalone** is a lightweight, self-contained Multi-Agent System (MAS) framework for local environments. It provides the same modular microkernel architecture as the distributed version but runs entirely on a single machine — no Ray or external services required.

---

## 🚀 QuickStart

### 1. Requirements

- `Python ≥ 3.11`
- `uv`

Install `uv`:

```bash
# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# or via pip
pip install uv
```

### 2. Clone and setup environment

```bash
git clone https://github.com/ZJU-LLMs/Agent-Kernel.git
cd Agent-Kernel
uv venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1
```

### 3. Install Agent-Kernel Standalone

- `web` → `aiohttp`, `fastapi`, `uvicorn`
- `storages` → `asyncpg`, `pymilvus`, `redis`
- `all` → includes both `web` and `storages`

> You can add extras with `.[web]`, `.[storages]`, or `.[all]` after the package path.

```bash
cd packages/agentkernel-standalone
# base install
uv pip install -e .

# with optional features:
# uv pip install -e ".[web]"
# uv pip install -e ".[storages]"
# uv pip install -e ".[all]"
```

### 4. Run example simulation

```bash
uv run python -m examples.standalone_test.run_simulation
```
