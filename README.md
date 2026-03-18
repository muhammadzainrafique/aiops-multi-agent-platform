# AIOps Multi-Agent Platform

> AI-Powered DevOps platform for autonomous IT operations.
> Intelligent agents monitor, detect, and resolve issues inside a Kubernetes cluster.

## How It Works
```
Prometheus Alert
      │
      ▼
┌─────────────┐    Redis Queue    ┌─────────────┐    Redis Queue    ┌─────────────┐
│  Supervisor │ ────────────────► │  Evaluator  │ ────────────────► │  Resolver   │
│   Agent     │                   │   Agent     │                   │   Agent     │
│             │                   │  (Groq LLM) │                   │  (K8s fix)  │
└─────────────┘                   └─────────────┘                   └─────────────┘
```

| Agent | Responsibility |
|---|---|
| **Supervisor** | Receives Prometheus AlertManager webhooks, collects pod logs, creates Incident objects, pushes to queue |
| **Evaluator** | Consumes incidents, calls Groq LLM to diagnose issues, generates human-readable recommendations |
| **Resolver** | Consumes enriched incidents, executes automated fixes (restart pod, scale deployment), updates status |

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| Containerisation | Docker |
| Orchestration | Kubernetes (Minikube for dev) |
| Monitoring | Prometheus + Grafana |
| Message Queue | Redis |
| AI Backend | Groq API (Llama 3) |
| Dev Environment | WSL2 / Ubuntu |

## Quick Start
```bash
# 1. Clone
git clone https://github.com/muhammadzainrafique/aiops-multi-agent-platform.git
cd aiops-multi-agent-platform

# 2. Configure environment
cp .env.example .env
# Edit .env and add your GROQ_API_KEY

# 3. Start all services
cd infra/docker
docker compose up --build
```

## Project Structure
```
agents/
  supervisor/     # Webhook listener + alert dispatcher
  evaluator/      # LLM-powered log analyser
  resolver/       # Kubernetes remediation executor
shared/
  models/         # Incident data model
  utils/          # Redis client, K8s client, logger
infra/
  docker/         # Docker Compose
  kubernetes/     # K8s manifests (agents, monitoring, storage)
monitoring/
  prometheus/     # Scrape config
  grafana/        # Dashboard JSON
scripts/          # Setup, teardown, failure simulation
docs/             # Architecture diagrams
```

## Team

- Muhammad Zain — FA22-CSE-024
- Hamza Maqsood — FA22-CSE-080
- Muhammad Farooq — FA22-CSE-090

**Supervisor:** Engr. Waqas Riaz, MUST — Feb 2026
