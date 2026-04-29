<div align="center">
  <h1>OpenHospital 🏥</h1>
</div>

<div align="center">
    <a href="https://github.com/ZJU-LLMs/Agent-Kernel/stargazers">
        <img alt="GitHub Stars" src="https://img.shields.io/github/stars/ZJU-LLMs/Agent-Kernel?label=Stars&logo=github&color=brightgreen">
    </a>
    <!-- <a href="https://github.com/ZJU-LLMs/Agent-Kernel/releases">
        <img alt="Version" src="https://img.shields.io/github/v/release/ZJU-LLMs/Agent-Kernel?color=blue&label=Version">
    </a> -->
    <a href="https://arxiv.org/pdf/2603.14771">
        <img alt="Paper" src="https://img.shields.io/badge/Paper-arXiv-b31b1b.svg?logo=arxiv&logoColor=white">
    </a>
    <a href="https://github.com/ZJU-LLMs/Agent-Kernel/pulls">
        <img alt="PRs Welcome" src="https://img.shields.io/badge/PRs-Welcome-8fce00.svg">
    </a>
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

# A Skill Training Ground for the Era of Carbon-Silicon Symbiosis

**OpenHospital** is a dedicated, interactive arena designed for evolving and benchmarking Large Language Model (LLM)-based Collective Intelligence (CI). By embedding physician agents within dynamic environments, it facilitates continuous interaction and professional evolution, overcoming the limitations of static datasets and the "data wall".

## 🎯 Core Advantages

OpenHospital moves beyond static evaluations, offering a comprehensive and interactive sandbox designed to foster and quantify genuine collective intelligence (CI). Its core advantages include:

### 1. Data-in-Agent-Self Paradigm

Diverging from traditional static datasets, OpenHospital requires physician agents to proactively elicit clinical information through continuous, dynamic interactions with autonomous patient agents.

### 2. Authentic Patient Ontology

Patient agents are meticulously modeled to guarantee strict medical correctness while exhibiting highly diverse, lifelike persona traits and behavioral patterns, ensuring highly realistic clinical encounters.

### 3. Dynamic Evolutionary Arena

By simulating complete, non-deterministic medical workflows, the platform serves as a dynamic training ground that continuously catalyzes and assesses the emergence of Collective Intelligence under complex conditions.

### 4. Comprehensive Evaluation Framework

OpenHospital introduces a robust, dual-dimensional metric system that quantitatively benchmarks multi-agent collaboration across both **Medical Capability** (e.g., examination precision, diagnostic accuracy) and **System Efficiency**.

## 🎬 Showcase

This is an interesting introduction to OpenHospital.

<div align="center">
  <a href="https://www.bilibili.com/video/YOUR_VIDEO_ID/" target="_blank">
    <img src="assets/showcase_video_cover.jpg" alt="OpenHospital Showcase" width="700"/>
  </a>
</div>

## 📍 Table of Contents

- [🎯 Core Advantages](#-core-advantages)
- [🎬 Showcase](#-showcase)
- [🏛️ Benchmarking Framework](#️-benchmarking-framework)
- [🚀 Quick Start](#-quick-start)
- [📂 Project Structure](#-project-structure)
- [🎓 Citation](#-citation)
- [🤝 Contributors](#-contributors)

## 🏛️ Benchmarking Framework

OpenHospital provides a multi-dimensional evaluation comprising both clinical validity and systemic efficiency:

- **Medical Capability**:
  - **Examination Precision**: Assesses the relevance and necessity of ordered tests, penalizing redundant tests.
  - **Diagnostic Accuracy**: Measures the correctness of the final consensus diagnosis.
  - **Treatment Plan Alignment**: Evaluates therapeutic quality against gold-standard guidelines across safety, effectiveness, and personalization.
- **System Efficiency**:
  - Evaluates the computational cost of system execution using Total Input Tokens.

## 🚀 Quick Start

This baseline is built on top of the Agent-Kernel framework. The steps below show the fastest way to configure the required services, start the hospital baseline, and make sure the evaluation-critical events are recorded correctly.

### 1. Prerequisites

- `Python >= 3.9`
- `Node.js >= 18` for the baseline frontend
- `Redis` for KV state and graph state
- `Milvus` for vector retrieval
- One chat model API and one embedding API

### 2. Install the project

```bash
git clone https://github.com/ZJU-LLMs/Agent-Kernel.git
cd Agent-Kernel

pip install -e "packages/agentkernel-distributed[all]"

cd demo/OpenHospital/baseline/frontend
npm install
cd ../../..
```

### 3. Configure databases

Edit `baseline/configs/db_config.yaml` and make sure these services are reachable:

- `default_redis`: Redis KV state, default `localhost:6379`, db `0`
- `default_graph`: Redis graph-related state, default `localhost:6379`, db `1`
- `MedicalVectorAdapter` / `ReflectionVectorAdapter` / `ExaminationsVectorAdapter` / `PatientVectorAdapter`: Milvus, default `http://localhost:19530`

If you want to use the built-in `recorder` to persist trajectories in PostgreSQL, also edit `baseline/configs/system_config.yaml`:

- `recorder.enable_db: true` enables database persistence
- Set `dbname`, `user`, `password`, `host`, and `port` for your PostgreSQL instance
- This is optional, but useful when you want trajectory data stored in PG instead of relying only on exported JSON and log files

### 4. Configure model APIs

Edit `baseline/configs/models_config.yaml`:

- Set `api_key` and `base_url` for `chat`, `patient`, and `evaluation`
- Set the embedding model endpoint for `embedding`
- The default template uses an OpenAI-compatible API format

### 5. Prepare baseline data

Copy your benchmark data into `baseline/data/` using these filenames:

```text
baseline/data/
├── ground_truth/ground_truth.json
├── patients/profiles.jsonl
└── examinations/examination_data.json
```

The baseline already includes doctor profiles and relation data. Replace the files above if you want to run your own dataset.

### 6. Start required services

Before running the simulation, make sure Redis, Milvus, and your model APIs are already running.

If you enabled the recorder database, make sure PostgreSQL is also running before startup.

### 7. Run the baseline

For the fastest local path, use the integrated startup script:

```bash
cd baseline
./startup/startup.sh
```

Then open:

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`

### Startup scripts

- `baseline/startup/startup.sh`: full local workflow. Cleans old state in fresh mode, starts the frontend dev server, then runs the simulation and API server together.
- `baseline/startup/startup.sh resume`: resumes a previous simulation run without clearing Redis and logs.
- `baseline/startup/startup_backend.sh`: runs the simulation only, without frontend or API server. Useful for generating logs first.
- `baseline/startup/startup_backend.sh resume`: resumes a simulation-only run from checkpoint.
- `baseline/startup/startup_frontend.sh`: replays an existing log directory in offline mode, starts frontend + backend for visualization, and does not require Redis.
- `baseline/startup/startup_batch_train_eval.sh`: runs the long-run batch train/eval pipeline based on prepared split data.

### ✨ Events required for evaluation

To support benchmark evaluation, the simulation should record at least these events:

- `SCHEDULE_EXAMINATION`: used to evaluate examination rationality
- `PRESCRIBE_TREATMENT`: used to evaluate diagnosis accuracy and treatment quality
- `LLM_INFERENCE`: used to count prompt tokens

These events are evaluation-critical. If they are missing or malformed, the benchmark metrics cannot be computed correctly.

If you also want complete patient trajectory replay and frontend visualization, keep recording these interaction events as well:

- `PATIENT_REGISTER`
- `PATIENT_MOVE`
- `DO_EXAMINATION`
- `RECEIVE_TREATMENT`
- `SEND_MESSAGE`
- `IDLE`

See `baseline/docs/evaluation_events.md` for the detailed evaluation event schema.

## 📂 Project Structure

```text
OpenHospital/
├── assets/                              # Images and static assets used by the demo
├── baseline/                            # Main hospital baseline simulation
│   ├── backend/                         # FastAPI backend and replay APIs
│   ├── configs/                         # Simulation, model, DB, and system configs
│   ├── data/                            # Baseline runtime data
│   │   ├── catalogs/                    # Medical catalogs and normal examination references
│   │   ├── doctors/                     # Doctor profiles
│   │   ├── examinations/                # Examination data
│   │   ├── ground_truth/                # Ground-truth labels
│   │   ├── patients/                    # Patient profiles
│   │   └── relation/                    # Hospital relation graph data
│   ├── frontend/                        # Vue/Vite frontend
│   ├── plugins/                         # Agent, action, and environment plugins
│   ├── scripts/                         # Data prep and training/evaluation helpers
│   ├── startup/                         # Startup scripts
│   └── run_simulation.py                # Baseline simulation runner
├── data/                                # Public benchmark catalogs, normal examination references, and sample patient data
├── README.md
└── README_zh.md
```

## 🎓 Citation

If you use OpenHospital in your research, please consider citing our paper:

```bibtex
@misc{liu2026openhospitalthinginitselfarenaevolving,
      title={OpenHospital: A Thing-in-itself Arena for Evolving and Benchmarking LLM-based Collective Intelligence}, 
      author={Peigen Liu and Rui Ding and Yuren Mao and Ziyan Jiang and Yuxiang Ye and Yunjun Gao and Ying Zhang and Renjie Sun and Longbin Lai and Zhengping Qian},
      year={2026},
      eprint={2603.14771},
      archivePrefix={arXiv},
      primaryClass={cs.AI},
      url={https://arxiv.org/abs/2603.14771}, 
}
```

## 🤝 Contributors

<a href="https://github.com/ZJU-LLMs/Agent-Kernel/graphs/contributors">
<img src="https://contrib.rocks/image?repo=ZJU-LLMs/Agent-Kernel&v=1" width=400 />
</a>

*We welcome contributions via Pull Requests!*
