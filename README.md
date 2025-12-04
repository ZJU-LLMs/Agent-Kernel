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
        <img alt="GitHub Stars" src="https://img.shields.io/github/stars/ZJU-LLMs/Agent-Kernel?label=Stars&logo=github&color=brightgreen">
    </a>
    <!-- <a href="https://github.com/ZJU-LLMs/Agent-Kernel/stargazers">
        <img alt="GitHub Stars" src="https://img.shields.io/github/stars/ZJU-LLMs/Agent-Kernel?style=social">
    </a> -->
    <!-- <a href="https://github.com/ZJU-LLMs/Agent-Kernel/releases">
        <img alt="Version" src="https://img.shields.io/github/v/release/ZJU-LLMs/Agent-Kernel?color=blue&label=Version">
    </a> -->
    <a href="https://github.com/ZJU-LLMs/Agent-Kernel/releases">
        <img alt="Version" src="https://img.shields.io/badge/Version-1.0.0-blue">
    </a>
    <!-- Project Resources -->
    <a href="https://www.agent-kernel.tech">
        <img alt="Homepage" src="https://img.shields.io/badge/Homepage-Website-1f4b99?logo=home&logoColor=white">
    </a>
    <a href="https://arxiv.org/abs/2512.01610">
        <img alt="Paper" src="https://img.shields.io/badge/Paper-arXiv-b31b1b.svg?logo=arxiv&logoColor=white">
    </a>
    <!-- Community -->
    <a href="https://www.agent-kernel.tech/societyhub">
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

# Explore the Scaling Law of Collective Intelligence

**Agent-Kernel** is a user-friendly multi-agent system development framework, which is designed to powerfully enable **large-scale** social simulation. This offers the opportunity to **Explore the Scaling Law of Collective Intelligence**.

## ✨ Highlights

Agent-Kernel supports:

- **dynamic addition and removal of LLMs-based agents at runtime**;

- **unlimited scalability of agents**;

- **real-time intervention during the simulation process**;

- **trustworthy verification of agent behaviors and large model outputs**;

- **code reuse across different simulation scenarios**.

## 🎬 Showcase

Agent-Kernel has been successfully applied to several complex social simulation scenarios:

### 1. Universe 25 Experiment

Simulating the famous "Universe 25" sociological experiment to explore the relationships between population density, social structure, and behavioral anomalies.

<div align="center">
  <img src="assets/rat.jpg" alt="Universe 25 Experiment" width="700"/>
</div>

### 2. ZJU Campus Life

Constructing a high-fidelity simulation of the campus environment to study pedestrian flow dynamics, resource allocation, and social interaction patterns.

<div align="center">
 <img src="assets/zju.png" alt="ZJU Campus Life" width="700"/>
</div>

## 📍 Table of Contents

- [✨ Highlights](#-highlights)
- [🎬 Showcase](#-showcase)
  - [Universe 25 Experiment](#1-universe-25-experiment)
  - [ZJU Campus Life](#2-zju-campus-life)
- [🎯 Core Advantages: Why Choose Agent-Kernel?](#-core-advantages-why-choose-agent-kernel)
  - [Adaptability](#1-adaptability)
  - [Configurability](#2-configurability)
  - [Reliability](#3-reliability)
  - [Reusability](#4-reusability)
- [🏛️ Architecture and Design](#️-architecture-and-design)
  - [Framework Overview](#1-framework-overview)
  - [Software Design](#2-software-design)
- [🚀 Quick Start](#-quick-start)
  - [Requirements](#1-requirements)
  - [Installation](#2-installation)
  - [(Optional) Start Society-Panel](#3-optional-start-society-panel)
- [📂 Project Structure](#-project-structure)
- [🎓 Citation](#-citation)
- [🤝 Contributors](#-contributors)
- [📜 License](#-license)

## 🎯 Core Advantages: Why Choose Agent-Kernel?

Agent-Kernel offers four core advantages for social simulation, making it stand out in the study of multi-agent systems:

### 1. Adaptability

Agent-Kernel supports adding/removing agents, changing environments, and modifying behaviors at runtime. This enables simulations to naturally reflect population flow, environmental shifts, and evolving behavioral patterns.

### 2. Configurability

With the Controller module, Agent-Kernel allows real-time adjustments to parameters or events during simulation. This makes it easy to test and validate complex sociological hypotheses.

### 3. Reliability

Agent-Kernel employs a strict system-level verification mechanism, validating every agent action. This ensures that simulation behaviors follow physical and social rules, maintaining scientific rigor.

### 4. Reusability

Agent-Kernel uses a standardized, plugin-based modular design. Codes can be reused across scenarios, significantly accelerating research iteration.

## 🏛️ Architecture and Design

### 1. Framework Overview

The Agent-Kernel framework adopts a modular microkernel architecture, with a core system—composed of the **Agent**, **Environment**, **Action**, **Controller**, and **System** modules—and multiple plugins. The core manages plugin registration, behavior verification, asynchronous communication, and other core responsibilities, while plugins provide the specialized functions for social simulation, as shown in the diagram below:

<p align="center">

<img src="assets/framework.png" alt="Agent-Kernel Framework" width="700"/>

</p>

### 2. Software Design

To realize the core design goals of the Agent-Kernel framework, we made a series of deliberate software design decisions, as illustrated in the diagram below:

<p align="center">

<img src="assets/softwaredesign.png" alt="Agent-Kernel Software Design" width="700"/>

</p>

## 🚀 Quick Start

### 1. Requirements

- `Python ≥ 3.11`

### 2. Installation

You can choose either **standalone** or **distributed** package based on your needs.

#### Agent-Kernel Standalone

```bash
pip install agentkernel-standalone
```

#### Agent-Kernel Distributed

```bash
pip install agentkernel-distributed
```

> The distributed package depends on **Ray** and will install it automatically.

#### Optional Extras

Both packages support optional extras:

- `[web]` → `aiohttp`, `fastapi`, `uvicorn`
- `[storages]` → `asyncpg`, `pymilvus`, `redis`
- `[all]` → includes both `web` and `storages`

```bash
# Example with extras
pip install agentkernel-standalone[all]
pip install agentkernel-distributed[web,storages]
```

### 3. (Optional) Start Society-Panel

Society-Panel is a web-based control panel to help you configure, deploy, and monitor your simulations visually.

1.  **Launch the panel:**
    Use the provided startup scripts to launch the entire application stack (backend + UI). **These scripts will automatically check for and install all required dependencies, so no manual environment setup is needed.**

    - **On Linux/macOS:**

      ```bash
      # Grant execution permission (first time only)
      chmod +x scripts/start_society_panel.sh
      ./scripts/start_society_panel.sh
      ```

    - **On Windows:**
      ```bash
      scripts\start_society_panel.bat
      ```

2.  **Access the UI:**
    Once the script confirms that the services are running, open your browser and navigate to:
    **`http://localhost:5174`**

From the panel, you can upload custom code packages, edit configuration files through a graphical interface, and control the simulation lifecycle. To shut down the panel and all related services, simply press `Ctrl+C` in the terminal where you ran the script.

## 📂 Project Structure

```
MAS/
├── packages/
│   ├── agentkernel-distributed/   # Distributed version (installs Ray automatically)
│   └── agentkernel-standalone/    # Local single-machine version
│
├── examples/
│   ├── distributed_test/          # Example for the distributed version (Ray)
│   └── standalone_test/           # Example for the local standalone version
│
├── society-panel/
│   ├── backend/                   # FastAPI backend service
│   └── frontend/                  # Vue 3 + Vite frontend
│
└── README.md
```

## 🎓 Citation

If you use Agent-Kernel in your research, please consider citing our paper:

```
@misc{mao2025agentkernelmicrokernelmultiagentframework,
      title={Agent-Kernel: A MicroKernel Multi-Agent System Framework for Adaptive Social Simulation Powered by LLMs},
      author={Yuren Mao and Peigen Liu and Xinjian Wang and Rui Ding and Jing Miao and Hui Zou and Mingjie Qi and Wanxiang Luo and Longbin Lai and Kai Wang and Zhengping Qian and Peilun Yang and Yunjun Gao and Ying Zhang},
      year={2025},
      eprint={2512.01610},
      archivePrefix={arXiv},
      primaryClass={cs.MA},
      url={https://arxiv.org/abs/2512.01610},
}
```

## 🤝 Contributors

Thanks to all the developers who have contributed to Agent-Kernel:

<a href="https://github.com/ZJU-LLMs/Agent-Kernel/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=ZJU-LLMs/Agent-Kernel&v=1" />
</a>

_We also welcome you to become one of our contributors via Pull Requests!_

## 📜 License

This project is licensed under the Apache 2.0.
