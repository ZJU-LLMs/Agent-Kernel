<div align="center">
 <img
  src="assets/agentkernel_logo.png"
  alt="Agent-Kernel Logo"
  width="400"
 />
</div>

<div align="center">
    <!-- Core Metrics -->
    <a href="https://github.com/ZJU-LLMs/Agent-Kernel/stargazers">
        <img alt="GitHub Stars" src="https://img.shields.io/github/stars/ZJU-LLMs/Agent-Kernel?style=social">
    </a>
    <a href="https://github.com/ZJU-LLMs/Agent-Kernel/releases">
        <img alt="Version" src="https://img.shields.io/badge/Version-1.0-blue">
    </a>
    <!-- Project Resources -->
    <a href="[YOUR_HOMEPAGE_URL]">
        <img alt="Homepage" src="https://img.shields.io/badge/Homepage-Website-1f4b99?logo=home&logoColor=white">
    </a>
    <a href="[YOUR_PAPER_URL]">
        <img alt="Paper" src="https://img.shields.io/badge/Paper-arXiv-b31b1b.svg?logo=arxiv&logoColor=white">
    </a>
    <!-- Community -->
    <a href="[YOUR_SOCIETYHUB_URL]">
        <img alt="SocietyHub" src="https://img.shields.io/badge/SocietyHub-Community-2ea44f?logo=discourse&logoColor=white">
    </a>
    <!-- <a href="[YOUR_DISCORD_INVITE_LINK]">
        <img alt="Join us on Discord" src="https://img.shields.io/badge/Discord-Join-5865F2?logo=discord&logoColor=white">
    </a> -->
    <!-- Contribution -->
    <a href="https://github.com/ZJU-LLMs/Agent-Kernel/pulls">
        <img alt="PRs Welcome" src="https://img.shields.io/badge/PRs-Welcome-8fce00.svg">
    </a>
    <!-- License -->
    <a href="https://github.com/ZJU-LLMs/Agent-Kernel/blob/main/LICENSE">
        <img alt="License" src="https://img.shields.io/badge/License-Apache_2.0-orange.svg">
    </a>
</div>

<br>

<div align="center">

[English](README.md) •
[简体中文](README_zh.md)

</div>

<div align="center">
  <i>We appreciate your support! Help us grow and improve by giving Agent-Kernel a 🌟 star on GitHub!</i>
</div>

---

# Agent-Kernel

**Agent-Kernel** is a Multi-Agent System (MAS) framework featuring a novel society-centric modular microkernel architecture, designed to support agent-based social simulation in both distributed and standalone environments.

## 📍 Table of Contents

- [✨ Core Advantages: Why Choose Agent-Kernel?](#-core-advantages-why-choose-agent-kernel)
  - [Adaptability](#-adaptability)
  - [Configurability](#-configurability)
  - [Reliability](#-reliability)
  - [Reusability](#-reusability)
- [🎬 Showcase](#-showcase)
  - [Universe 25 Experiment](#-universe-25-experiment)
  - [ZJU Campus Life](#-zju-campus-life)
- [🏛️ Architecture and Design](#-architecture-and-design)
  - [Framework Overview](#-framework-overview)
  - [Software Design](#-software-design)
- [🚀 QuickStart](#️-quickstart)
  - [1. Requirements](#1-requirements)
  - [2. Clone and setup environment](#2-clone-and-setup-environment)
  - [3. Choose a package to install](#3-choose-a-package-to-install)
- [📂 Project Structure](#-project-structure)
- [🎓 Citation](#-citation)
- [🤝 Contributors](#-contributors)
- [📜 License](#-license)

## ✨ Core Advantages: Why Choose Agent-Kernel?

Agent-Kernel offers four core advantages for social simulation, making it stand out in the study of multi-agent systems:

### • Adaptability

Agent-Kernel supports adding/removing agents, changing environments, and modifying behaviors at runtime. This enables simulations to naturally reflect population flow, environmental shifts, and evolving behavioral patterns.

### • Configurability

With the Controller module, Agent-Kernel allows real-time adjustments to parameters or events during simulation. This makes it easy to test and validate complex sociological hypotheses.

### • Reliability

Agent-Kernel employs a strict system-level verification mechanism, validating every agent action. This ensures that simulation behaviors follow physical and social rules, maintaining scientific rigor.

### • Reusability

Agent-Kernel uses a standardized, plugin-based modular design. Codes can be reused across scenarios, significantly accelerating research iteration.

## 🎬 Showcase

Agent-Kernel has been successfully applied to several complex social simulation scenarios:

### • Universe 25 Experiment

Simulating the famous "Universe 25" sociological experiment to explore the relationships between population density, social structure, and behavioral anomalies.

<div align="center">
  <img src="assets/rat.jpg" alt="Universe 25 Experiment" width="700"/>
</div>

### • ZJU Campus Life

Constructing a high-fidelity simulation of the campus environment to study pedestrian flow dynamics, resource allocation, and social interaction patterns.

<div align="center">
 <img src="assets/zju.png" alt="ZJU Campus Life" width="700"/>
</div>

## 🏛️Architecture and Design

### • Framework Overview

The Agent-Kernel framework adopts a modular microkernel architecture, with a core system—composed of the **Agent**, **Environment**, **Action**, **Controller**, and **System** modules—and multiple plugins. The core manages plugin registration and asynchronous communication, while plugins provide the specialized functions for social simulation, as shown in the diagram below:

<p align="center">

<img src="assets/framework.png" alt="Agent-Kernel Framework" width="700"/>

</p>

### • Software Design

To realize the core design goals of the Agent-Kernel framework, we made a series of deliberate software design decisions, as illustrated in the diagram below:

<p align="center">

<img src="assets/softwaredesign.png" alt="Agent-Kernel Software Design" width="700"/>

</p>

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

### 3. Choose a package to install

You can work with either distributed or standalone package.

Both support optional extras:

- `web` → `aiohttp`, `fastapi`, `uvicorn`
- `storages` → `asyncpg`, `pymilvus`, `redis`
- `all` → includes both `web` and `storages`

> You can add extras with `.[web]`, `.[storages]`, or `.[all]` after the package path.

#### Agent-Kernel Distributed

```bash
cd packages/agentkernel-distributed
# base install
uv pip install -e .

# with optional features:
# uv pip install -e ".[web]"
# uv pip install -e ".[storages]"
# uv pip install -e ".[all]"
```

- The distributed package depends on **ray** and will install it automatically.
- **No manual Ray cluster startup is required** for local usage.

Run the distributed example:

```bash
uv run python -m examples.distributed_test.run_simulation
```

#### Agent-Kernel Standalone

```bash
cd packages/agentkernel-standalone
# base install
uv pip install -e .

# with optional features:
# uv pip install -e ".[web]"
# uv pip install -e ".[storages]"
# uv pip install -e ".[all]"
```

Run the standalone example:

```bash
uv run python -m examples.standalone_test.run_simulation
```

## 📂 Project Structure

```
MAS/
├── packages/
│   ├── agentkernel-distributed/   # Distributed version (installs ray automatically)
│   └── agentkernel-standalone/    # Local single-machine version
│
├── examples/
│   ├── distributed_test/
│   └── standalone_test/
│
└── README.md
```

## 🎓 Citation

If you use Agent-Kernel in your research, please consider citing our paper:

```
@article{agentkernel2025,
  title={Agent-Kernel: A MicroKernel Multi-Agents System Framework for Adaptive Social Simulation based on LLMs},
  author={Author, Lead and Author, Co and Author, Co},
  journal={Journal of Simulation},
  year={2025},
  publisher={Publisher}
}
```

## 🤝 Contributors

Thanks to all the developers who have contributed to Agent-Kernel:

<a href="https://github.com/ZJU-LLMs/Agent-Kernel/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=ZJU-LLMs/Agent-Kernel" />
</a>

_We also welcome you to become one of our contributors via Pull Requests!_

## 📜 License

This project is licensed under the Apache 2.0.
