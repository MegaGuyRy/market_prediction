# News-First RAG + XGBoost + Multi-Agent Trading System  
(PostgreSQL · pgvector · Alpaca · Ollama · Docker)

---

## Overview

This repository implements a **fully automated, institutional-style trading system** built around a clear separation of responsibilities:

- **News & events decide where to look**
- **Machine learning decides what the signal is**
- **LLM agents critique and stress-test decisions**
- **Deterministic rules enforce capital and risk discipline**
- **Execution and monitoring are fully auditable**

The system is **news-first**, **ML-driven**, and **rule-controlled**, designed to scale from a local machine to a home server with minimal changes.

> **Design philosophy**  
> News routes attention.  
> ML proposes trades.  
> Agents challenge assumptions.  
> Rules enforce discipline.  
> Execution follows audited decisions.

---

## Key Design Decisions (Locked)

- **Trading cadence:** Daily  
- **Full decision runs:** Twice per trading day  
  - Morning (open-ish)
  - Afternoon (pre-close)
- **Intraday behavior:**  
  - No LLM agents  
  - Deterministic safety only (stops, drawdown, gap/volatility rules)
- **Universe:** Blue-chip equities (liquid large caps)
- **Automation:** Fully automated (no human-in-the-loop)
- **Deployment:** Docker + Docker Compose

---

## High-Level System Flow (News-First)

```mermaid
flowchart TB

subgraph A["News & Market Awareness"]
  A1["News Sources<br/>(RSS, SEC, Press Releases)"]
  A2["Ingest & Normalize"]
  A3["RAG Index<br/>(pgvector embeddings)"]
  A4["News / Event Scanner"]
end

subgraph B["Candidate Selection Policy"]
  B1["News-Driven Candidates"]
  B2["Market-Driven Candidates<br/>(gaps, volume, volatility)"]
  B3["Portfolio-Driven Candidates<br/>(open positions)"]
  B4["Baseline Universe Coverage"]
  B5["Final Candidate List"]
end

subgraph C["Market Data & Features"]
  C1["Market Data Pull (OHLCV)"]
  C2["Feature Engineering"]
  C3["Feature Store (Postgres)"]
end

subgraph D["ML Signal Engine"]
  D1["XGBoost Model"]
  D2["Signal Output<br/>(BUY / SELL / HOLD,<br/>confidence, edge)"]
end

subgraph E["Multi-Agent Critique (Local LLMs)"]
  E1["Market Analyst"]
  E2["Bull"]
  E3["Bear"]
  E4["Risk Manager"]
  E5["Committee"]
end

subgraph F["Portfolio & Execution"]
  F1["Risk Controller<br/>(hard rules)"]
  F2["Execution Engine<br/>(Alpaca)"]
end

subgraph G["Monitoring & Audit"]
  G1["Logs & Decisions"]
  G2["Trades & PnL"]
end

subgraph H["Intraday Safety<br/>(No Agents)"]
  H1["Stop-Losses"]
  H2["Drawdown Limits"]
  H3["Gap / Volatility Guards"]
end

A1 --> A2 --> A3 --> A4 --> B1
B1 --> B5
B2 --> B5
B3 --> B5
B4 --> B5

B5 --> C1 --> C2 --> C3
C3 --> D1 --> D2

D2 --> E1
D2 --> E2
D2 --> E3
D2 --> E4

E1 --> E5
E2 --> E5
E3 --> E5
E4 --> E5

E5 --> F1 --> F2 --> G1 --> G2

F2 -. monitored by .-> H1
F2 -. monitored by .-> H2
F2 -. monitored by .-> H3
```
---
#### Tech Stack
Core
* Python – orchestration, features, ML, policy, execution

* PostgreSQL – system of record

* pgvector – vector search for news RAG

* XGBoost – primary ML signal engine

* Alpaca API – paper / live execution

Local AI

* Ollama – local LLM runtime

* News & sentiment summarization

* Analyst / Bull / Bear / Risk / Committee agents

Deployment

* Docker + Docker Compose

* reproducible runs

* easy migration to a home server

* clean separation of services

---
#### Dockerized Runtime Architecture

* postgres
  * OHLCV bars
  * features
  * news + embeddings (pgvector)
  * signals, agent reports, decisions, trades

* ollama
  * local LLMs for agents & sentiment

* app
  * Python trading orchestrator

* scheduler (optional)
  * triggers twice-daily runs

---
#### Candidate Selection Policy (Summary)

A ticker is analyzed if any of the following apply:
1. News-Driven
   * earnings, guidance, legal/regulatory, M&A, analyst actions
   * high novelty or sentiment magnitude

2. Market-Driven
    * large gaps
    * abnormal volume or volatility
    * breakouts / breakdowns

3. Portfolio-Driven (mandatory)
    * all open positions
    * positions near stops or exits

4. Baseline Coverage
    * rotating subset of blue-chip stocks to avoid blind spots
    * Candidate selection decides what gets analyzed, not what gets traded.

---
#### ML Signal Engine (LSTM or XGBoost)
* Evaluates candidate tickers only
* Outputs:
  * BUY / SELL / HOLD
  * confidence / expected return
  * edge score
* ML is the only component allowed to propose new trades
---
#### Multi-Agent Critique (Local LLMs)
Agents do not generate trades.
They:
* critique ML proposals
* evaluate news evidence
* identify risk and blind spots
Agents:
* Market Analyst (regime / anomaly)
* Bull (best-case thesis)
* Bear (counter-thesis)
* Risk Manager (event & exposure risk)
* Committee (final proposal)
Agents may reduce or veto trades — never increase exposure.
---
Portfolio & Risk Controller (Hard Rules)
Final authority (pure code):
* risk-per-trade sizing
* max position size per stock
* max portfolio exposure
* drawdown-based de-risking
* optional volatility targeting
LLMs cannot override this layer.
---
Position Lifecycle
Scheduled (Twice Daily)
* enter new positions
* reduce / exit existing positions
* update stops and targets
Intraday (Always On, No Agents)
* stop-loss execution
* drawdown enforcement

gap / volatility emergency rules
