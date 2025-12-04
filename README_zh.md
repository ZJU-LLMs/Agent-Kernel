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
    <a href="https://github.com/ZJU-LLMs/Agent-Kernel/releases">
        <img alt="Version" src="https://img.shields.io/badge/Version-1.0.0-blue">
    </a>
    <!-- Project Resources -->
    <a href="https://www.agent-kernel.tech/">
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
  <i>感谢您的支持！为 Agent-Kernel 点亮一颗 🌟 Star，帮助我们不断成长和完善！</i>
</div>

---

# 探索群体智能的无限可能

**Agent-Kernel** 是一款用户友好的多智能体系统开发框架，深度赋能**大规模**社会模拟，**为探索大规模群体智能提供无限可能**。

## ✨ 亮点

Agent-Kernel 支持：

- **运行时动态增减大模型智能体**；

- **智能体数量无限扩展**；

- **模拟过程中实时干预**；

- **智能体行为和大模型输出的验证与审查**；

- **跨模拟场景代码复用**。

## 🎬 应用展示

Agent-Kernel 已成功应用于多个复杂的社会模拟场景：

### 1. 25 号宇宙

模拟著名的“25 号宇宙”社会学实验，以探索人口密度、社会结构与行为异常之间的关系。

<div align="center">
  <img src="assets/rat.jpg" alt="25号宇宙实验" width="700"/>
</div>

### 2. 浙江大学校园生活

构建高保真度的校园环境模拟，用于研究行人流动动态、资源分配和社会互动模式。

<div align="center">
 <img src="assets/zju.png" alt="浙大校园模拟" width="700"/>
</div>

## 📍 目录

- [✨ 亮点](#-亮点)
- [🎬 应用展示](#-应用展示)
  - [25 号宇宙](#1-25-号宇宙)
  - [浙江大学校园生活](#2-浙江大学校园生活)
- [🎯 核心优势：为何选择 Agent-Kernel？](#-核心优势为何选择-agent-kernel)
  - [适应性](#1-适应性)
  - [可配置性](#2-可配置性)
  - [可靠性](#3-可靠性)
  - [可复用性](#4-可复用性)
- [🏛️ 架构与设计](#️-架构与设计)
  - [框架总览](#1-框架总览)
  - [软件设计](#2-软件设计)
- [🚀 快速入门](#-快速入门)
  - [环境要求](#1-环境要求)
  - [安装](#2-安装)
  - [（可选）启动 Society-Panel](#3-可选启动-society-panel)
- [📂 项目结构](#-项目结构)
- [🎓 引用](#-引用)
- [🤝 贡献者](#-贡献者)
- [📜 许可证](#-许可证)

## 🎯 核心优势：为何选择 Agent-Kernel？

Agent-Kernel 为社会模拟研究提供了四大核心优势，使其在多智能体系统领域脱颖而出：

### 1. 适应性

Agent-Kernel 支持在运行时增减智能体、改变环境和修改行为。这意味着我们能够模拟社会中的人口流动、环境变迁和行为模式的持续演进，从而捕捉真实社会中不断变化的动态过程。

### 2. 可配置性

Agent-Kernel 赋予了研究者强大的实时干预能力 。通过内置的控制器模块，您可以在仿真运行时直接调整实验参数或触发突发事件，从而高效地验证各类复杂的社会学假设 。

### 3. 可靠性

Agent-Kernel 引入了严格的系统级校验机制，我们对智能体的每次行为都进行了验证，确保符合物理与社会规则，从而保障了模拟结果的科学有效性。

### 4. 可复用性

Agent-Kernel 采用了标准化的插件化设计，功能模块被封装为可互换的插件单元，支持跨场景的无缝复用 ，极大地加速了研究迭代的效率 。

## 🏛️ 架构与设计

### 1. 框架总览

Agent-Kernel 框架采用模块化微内核架构，包含一个由 **Agent**、**Environment**、**Action**、**Controller** 和 **System** 模块组成的核心系统以及多个插件。其中核心系统负责注册插件、行为审查、异步通信以及其他关键职责，而插件则提供社会模拟所需的具体功能，如下图所示：

<p align="center">

<img src="assets/framework.png" alt="Agent-Kernel 框架" width="700"/>

</p>

### 2. 软件设计

为了实现 Agent-Kernel 框架的核心设计目标，我们采用了一系列精巧的软件设计策略，如下图所示：

<p align="center">

<img src="assets/softwaredesign.png" alt="Agent-Kernel 软件设计" width="700"/>

</p>

## 🚀 快速入门

### 1. 环境要求

- `Python ≥ 3.11`

### 2. 安装

您可以根据需求选择**单机版**或**分布式版**。

#### Agent-Kernel 单机版

```bash
pip install agentkernel-standalone
```

#### Agent-Kernel 分布式版本

```bash
pip install agentkernel-distributed
```

> 分布式包依赖于 **Ray**，会自动进行安装。

#### 可选附加功能

两个包都支持可选的附加功能：

- `[web]` → `aiohttp`, `fastapi`, `uvicorn`
- `[storages]` → `asyncpg`, `pymilvus`, `redis`
- `[all]` → 同时包含 `web` 和 `storages`

```bash
# 安装示例
pip install agentkernel-standalone[all]
pip install agentkernel-distributed[web,storages]
```

### 3. （可选）启动 Society-Panel

Society-Panel 是一个基于网页的控制面板，可以帮助您可视化地配置、部署和监控模拟。

1.  **启动面板：**
    使用项目提供的启动脚本来启动整个应用（后端 + 前端界面）。**这些脚本会自动检查并安装所有必需的依赖，您无需手动配置环境。**

    - **在 Linux/macOS 上：**

      ```bash
      # 授予执行权限（仅首次需要）
      chmod +x scripts/start_society_panel.sh
      ./scripts/start_society_panel.sh
      ```

    - **在 Windows 上：**
      ```bash
      scripts\start_society_panel.bat
      ```

2.  **访问界面：**
    当脚本确认服务已成功运行后，打开您的浏览器并访问：
    **`http://localhost:5174`**

通过该面板，您可以上传自定义代码包、通过图形化界面编辑配置文件，并控制模拟的生命周期。要关闭面板及所有相关服务，只需在运行脚本的终端窗口中按下 `Ctrl+C` 即可。

## 📂 项目结构

```
MAS/
├── packages/
│   ├── agentkernel-distributed/   # 分布式版本 (自动安装 Ray)
│   └── agentkernel-standalone/    # 本地单机版本
│
├── examples/
│   ├── distributed_test/          # 分布式版本 (Ray) 示例
│   └── standalone_test/           # 本地单机版本示例
│
├── society-panel/
│   ├── backend/                   # FastAPI 后端服务
│   └── frontend/                  # Vue 3 + Vite 前端
│
└── README.md
```

## 🎓 引用

如果您在研究中使用了 Agent-Kernel，请考虑引用我们的论文：

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

## 🤝 贡献者

感谢所有为 Agent-Kernel 做出贡献的开发者们：

<a href="https://github.com/ZJU-LLMs/Agent-Kernel/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=ZJU-LLMs/Agent-Kernel&v=1" />
</a>

_我们同样欢迎您通过提交 Pull Requests 成为贡献者中的一员！_

## 📜 许可证

本项目采用 Apache 2.0 许可证。
