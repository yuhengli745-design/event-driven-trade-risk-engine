# Event-Driven Trade Lifecycle and Risk Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and publish a tested Python engine that implements the approved order, execution, price, risk, P&L, idempotency, logging, and replay behavior.

**Architecture:** A framework-free `TradingEngine` owns in-memory aggregate state and dispatches immutable domain events. Small modules define events, state models, risk checks, JSON Lines persistence, and structured logging; replay reuses the same application path with persistence disabled.

**Tech Stack:** Python 3.11+, standard library, pytest, ruff, GitHub Actions

**Spec:** `docs/superpowers/specs/2026-11-09-trade-risk-engine-design.md`

## Global Constraints

- Use `Decimal` for all quantities, prices, notionals, and P&L values.
- Runtime dependencies remain standard-library only.
- Events are immutable dataclasses with event IDs and UTC timestamps.
- Persisted events use versioned deterministic JSON Lines records.
- All examples are synthetic and the README describes the project as a simulation.

## Review Focus

- Non-positive order quantity or price must be rejected without creating a tradable order.
- Execution quantity or price must be positive and overfills must leave all state unchanged.
- Duplicate event/order IDs must not create ambiguous state.
- Position reversal must realize only the closed portion and correctly reset average cost.
- Unknown, malformed, or partially truncated event-store records must identify the failing line.

---

### Task 1: Package foundation and domain events

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `src/trade_engine/__init__.py`, `src/trade_engine/events.py`
- Test: `tests/test_events.py`

**Interfaces:**
- Produces immutable `OrderSubmitted`, `OrderCancelled`, `ExecutionReceived`, and `PriceUpdated` dataclasses plus `Side` and `OrderStatus` enums.

- [ ] Write tests for required identifiers, positive quantities/prices, UTC-aware timestamps, and immutability.
- [ ] Run `python -m pytest tests/test_events.py -v` and verify the missing package/API causes failure.
- [ ] Implement the event dataclasses and validation using `Decimal`.
- [ ] Run the focused test and full `python -m pytest` suite.
- [ ] Commit with `feat: add domain events`.

### Task 2: Orders, positions, and P&L

**Files:**
- Create: `src/trade_engine/models.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Consumes `Side` and `OrderStatus`.
- Produces `Order.apply_execution(quantity, price)`, `Position.apply_execution(signed_quantity, price)`, `Position.mark(price)`, and deterministic snapshot dictionaries.

- [ ] Write tests for partial/full fills, overfills, long and short weighted average cost, reductions, and crossing through zero.
- [ ] Run the focused test and confirm expected failures.
- [ ] Implement minimal order and position state behavior.
- [ ] Run focused and full test suites.
- [ ] Commit with `feat: add order and position accounting`.

### Task 3: Pre-trade risk controls

**Files:**
- Create: `src/trade_engine/risk.py`
- Test: `tests/test_risk.py`

**Interfaces:**
- Produces `RiskLimits(max_abs_position, max_abs_notional)`, `RiskManager`, and a validation result containing approval and reason.

- [ ] Write tests for exact-boundary approval, position breach, notional breach, sell-side projection, active-order reservations, cancellation release, and symbol-specific/default limits.
- [ ] Run focused tests and confirm failures.
- [ ] Implement projected-position and projected-notional checks.
- [ ] Run focused and full suites.
- [ ] Commit with `feat: add pre-trade risk limits`.

### Task 4: Event-driven engine and idempotency

**Files:**
- Create: `src/trade_engine/engine.py`
- Test: `tests/test_engine.py`

**Interfaces:**
- Consumes domain events, models, and `RiskManager`.
- Produces `TradingEngine.process(event, persist=True) -> ProcessingResult` and `TradingEngine.snapshot() -> dict`.

- [ ] Write tests for submission, rejection, cancellation, invalid transitions, missing orders, duplicate order IDs, duplicate execution IDs with matching/different payloads, and transactional overfill rejection.
- [ ] Run focused tests and confirm failures.
- [ ] Implement dispatch, lifecycle validation, atomic state changes, and execution-ID deduplication.
- [ ] Run focused and full suites.
- [ ] Commit with `feat: implement event-driven trading engine`.

### Task 5: JSON Lines persistence and deterministic replay

**Files:**
- Create: `src/trade_engine/event_store.py`
- Modify: `src/trade_engine/engine.py`
- Test: `tests/test_event_store.py`, `tests/test_replay_integration.py`

**Interfaces:**
- Produces `JsonLinesEventStore.append(event)`, `JsonLinesEventStore.read_all()`, event encode/decode helpers, and `TradingEngine.replay(store)`.

- [ ] Write tests for Decimal/timestamp round trips, accepted/rejected/ignored append order, unknown schema/event types, malformed/truncated lines, append-failure atomicity, and exact snapshot equality after replay.
- [ ] Run focused tests and confirm failures.
- [ ] Implement deterministic codec, append-only audit storage, candidate-state commit after append, line-numbered errors, and replay without double persistence.
- [ ] Run focused and full suites.
- [ ] Commit with `feat: add deterministic event replay`.

### Task 6: Structured logging and end-to-end scenario

**Files:**
- Create: `src/trade_engine/logging.py`, `examples/run_demo.py`
- Modify: `src/trade_engine/engine.py`
- Test: `tests/test_logging.py`, `tests/test_workflow_integration.py`

**Interfaces:**
- Produces `JsonFormatter`, `configure_json_logger()`, and a runnable synthetic workflow.

- [ ] Write tests for accepted, rejected, and ignored JSON log records and the complete workflow state.
- [ ] Run focused tests and confirm failures.
- [ ] Add logger integration and the demo scenario.
- [ ] Run the demo, focused tests, and full suite.
- [ ] Commit with `feat: add structured logs and demo workflow`.

### Task 7: Public documentation and CI

**Files:**
- Create: `README.md`, `LICENSE`, `.github/workflows/ci.yml`
- Modify: `pyproject.toml`

**Interfaces:**
- Produces reproducible setup, demo, test, architecture, design-choice, limitation, and interview-explanation documentation.

- [ ] Write README commands and confirm each works in a clean local install.
- [ ] Add MIT license, package metadata, pytest/ruff configuration, and Python 3.11/3.12 CI.
- [ ] Run `python -m pytest`, `python -m ruff check .`, package build/install checks, and the demo.
- [ ] Compare implementation against every acceptance criterion in the design.
- [ ] Commit with `docs: add project guide and CI`.

### Task 8: GitHub publication

**Files:** No source changes expected.

**Interfaces:**
- Produces public GitHub repository `event-driven-trade-risk-engine` with the verified default branch pushed.

- [ ] Confirm no secrets or private data are tracked and inspect the complete diff/history.
- [ ] Create the public GitHub repository and configure `origin`.
- [ ] Push the default branch and verify repository visibility and file presence through GitHub.
- [ ] Report the repository URL and exact local verification evidence.
