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
  <i>感谢您的支持！为 Agent-Kernel 点亮一颗 🌟 Star，帮助我们不断成长和完善！</i>
</div>

---

# Agent-Kernel

**Agent-Kernel** 是一个多智能体系统 (Multi-Agent System, MAS) 框架，其开创了一种以社会为中心的模块化微内核架构，旨在为分布式和单机环境下的社会模拟提供支持。

## 📍 目录

- [✨ 核心优势：为何选择 Agent-Kernel？](#-核心优势为何选择-agent-kernel)
  - [适应性](#-适应性)
  - [可配置性](#-可配置性)
  - [可靠性](#-可靠性)
  - [可复用性](#-可复用性)
- [🎬 应用展示](#-应用展示)
  - [25 号宇宙](#-25-号宇宙)
  - [浙江大学校园生活](#-浙江大学校园生活)
- [🏛️ 架构与设计](#️-架构与设计)
  - [框架总览](#-框架总览)
  - [软件设计](#-软件设计)
- [🚀 快速入门](#️-快速入门)
  - [1. 环境要求](#1-环境要求)
  - [2. 克隆并设置环境](#2-克隆并设置环境)
  - [3. 选择要安装的包](#3-选择要安装的包)
- [📂 项目结构](#-项目结构)
- [🎓 引用](#-引用)
- [🤝 贡献者](#-贡献者)
- [📜 许可证](#-许可证)

## ✨ 核心优势：为何选择 Agent-Kernel？

Agent-Kernel 为社会模拟研究提供了四大核心优势，使其在多智能体系统领域脱颖而出：

### • 适应性

Agent-Kernel 支持在运行时增减智能体、改变环境和修改行为。这意味着我们能够模拟社会中的人口流动、环境变迁和行为模式的持续演进，从而捕捉真实社会中不断变化的动态过程。

### • 可配置性

Agent-Kernel 赋予了研究者强大的实时干预能力 。通过内置的控制器模块，您可以在仿真运行时直接调整实验参数或触发突发事件，从而高效地验证各类复杂的社会学假设 。

### • 可靠性

Agent-Kernel 引入了严格的系统级校验机制，我们对智能体的每次行为都进行了验证，确保符合物理与社会规则，从而保障了模拟结果的科学有效性。

### • 可复用性

Agent-Kernel 采用了标准化的插件化设计，功能模块被封装为可互换的插件单元，支持跨场景的无缝复用 ，极大地加速了研究迭代的效率 。

## 🎬 应用展示

Agent-Kernel 已成功应用于多个复杂的社会模拟场景：

### • 25 号宇宙

模拟著名的“25 号宇宙”社会学实验，以探索人口密度、社会结构与行为异常之间的关系。

<div align="center">
  <img src="assets/rat.jpg" alt="25号宇宙实验" width="700"/>
</div>

### • 浙江大学校园生活

构建高保真度的校园环境模拟，用于研究行人流动动态、资源分配和社会互动模式。

<div align="center">
 <img src="assets/zju.png" alt="浙大校园模拟" width="700"/>
</div>

## 🏛️ 架构与设计

### • 框架总览

Agent-Kernel 框架采用模块化微内核架构，包含一个由 **Agent**、**Environment**、**Action**、**Controller** 和 **System** 模块组成的核心系统以及多个插件。其中核心系统负责注册插件和异步通信，而插件则提供社会模拟所需的专业功能，如下图所示：

<p align="center">

<img src="assets/framework.png" alt="Agent-Kernel 框架" width="700"/>

</p>

### • 软件设计

为了实现 Agent-Kernel 框架的核心设计目标，我们采用了一系列精巧的软件设计策略，如下图所示：

<p align="center">

<img src="assets/softwaredesign.png" alt="Agent-Kernel 软件设计" width="700"/>

</p>

## 🚀 快速入门

### 1. 环境要求

- `Python ≥ 3.11`
- `uv`

安装 `uv`:

```bash
# Linux/macOS 用户
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell) 用户
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 或通过 pip 安装
pip install uv
```

### 2. 克隆并设置环境

```bash
git clone https://github.com/ZJU-LLMs/Agent-Kernel.git
cd Agent-Kernel
uv venv
# Linux/macOS 用户
source .venv/bin/activate
# Windows PowerShell 用户
# .venv\Scripts\Activate.ps1
```

### 3. 选择要安装的包

您可以选择使用分布式包或单机包。

两者都支持可选的附加功能：

- `web` → `aiohttp`, `fastapi`, `uvicorn`
- `storages` → `asyncpg`, `pymilvus`, `redis`
- `all` → 同时包含 `web` 和 `storages`

> 您可以在包路径后添加 `.[web]`、`.[storages]` 或 `.[all]` 来安装附加功能。

#### Agent-Kernel 分布式版本

```bash
cd packages/agentkernel-distributed
# 基础安装
uv pip install -e .

# 安装可选功能:
# uv pip install -e ".[web]"
# uv pip install -e ".[storages]"
# uv pip install -e ".[all]"
```

- 分布式包依赖于 **Ray**，会自动进行安装。
- 在本地使用时，**无需手动启动 Ray 集群**。

运行分布式示例：

```bash
uv run python -m examples.distributed_test.run_simulation
```

#### Agent-Kernel 单机版

```bash
cd packages/agentkernel-standalone
# 基础安装
uv pip install -e .

# 安装可选功能:
# uv pip install -e ".[web]"
# uv pip install -e ".[storages]"
# uv pip install -e ".[all]"
```

运行单机版示例：

```bash
uv run python -m examples.standalone_test.run_simulation
```

## 📂 项目结构

```
MAS/
├── packages/
│   ├── agentkernel-distributed/   # 分布式版本 (自动安装 ray)
│   └── agentkernel-standalone/    # 本地单机版本
│
├── examples/
│   ├── distributed_test/
│   └── standalone_test/
│
└── README.md
```

## 🎓 引用

如果您在研究中使用了 Agent-Kernel，请考虑引用我们的论文：

```
@article{agentkernel2025,
  title={Agent-Kernel: A MicroKernel Multi-Agents System Framework for Adaptive Social Simulation based on LLMs},
  author={Author, Lead and Author, Co and Author, Co},
  journal={Journal of Simulation},
  year={2025},
  publisher={Publisher}
}
```

## 🤝 贡献者

感谢所有为 Agent-Kernel 做出贡献的开发者们：

<a href="https://github.com/ZJU-LLMs/Agent-Kernel/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=ZJU-LLMs/Agent-Kernel" />
</a>

_我们同样欢迎您通过提交 Pull Requests 成为贡献者中的一员！_

## 📜 许可证

本项目采用 Apache 2.0 许可证。
