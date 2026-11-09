# Event-Driven Trade Lifecycle and Risk Engine Design

## Intent

Build a public, interview-ready Python project that demonstrates the claims in Lee's CV with runnable code, deterministic behavior, clear documentation, and meaningful automated tests.

## Goals

- Process order, fill, and market-price events through one event-driven engine.
- Maintain order lifecycle, position, average cost, realized P&L, and unrealized P&L state.
- Reject invalid lifecycle transitions and orders that breach configured position or notional limits.
- Treat duplicate execution IDs idempotently.
- Persist events as JSON Lines and reproduce identical state by replaying them in order.
- Emit structured JSON logs containing event and outcome context.
- Include unit tests, end-to-end integration tests, failure scenarios, a demonstration script, architecture documentation, and CI.
- Remain small enough for the owner to understand and explain in an interview.

## Non-goals

- Connecting to a broker, exchange, or live market-data provider.
- Authentication, a web UI, a database, or a distributed message broker.
- Portfolio optimization, order matching, latency simulation, commissions, or corporate actions.
- Supporting derivatives, multiple currencies, or cash accounting.

## Anti-goals

- Hiding trading logic behind a framework.
- Using binary floating-point values for quantity, money, price, or P&L.
- Claiming production readiness or live-trading capability.
- Adding features that cannot be demonstrated and tested clearly.

## Constraints

- Python 3.11 or newer.
- Use `Decimal` for quantity and monetary calculations.
- Runtime code uses the Python standard library; development dependencies are `pytest` and `ruff`.
- Events are immutable dataclasses with explicit event IDs and UTC timestamps.
- Persisted event records are versioned JSON objects serialized in deterministic field order.
- Public repository name: `event-driven-trade-risk-engine`.
- All example identifiers, prices, and executions are synthetic.

## Approaches considered

1. **Core Python engine (selected).** A framework-free package focused on state transitions, risk rules, replay, and tests. It maps directly to the CV description and is practical to explain.
2. **Core engine plus REST API.** Easier to demonstrate through HTTP, but adds transport code that does not improve the trading-domain evidence.
3. **Mini trading platform.** A database, queue, and web interface would look broader but would obscure the core logic and materially increase unfinished-work risk.

## Architecture

`TradingEngine` is the single event dispatcher and aggregate owner. It receives `OrderSubmitted`, `OrderCancelled`, `ExecutionReceived`, and `PriceUpdated` events. Domain models and small services hold order state, positions, P&L calculations, lifecycle rules, and risk limits.

For live processing, the engine validates and applies an event to a candidate copy of state, appends the input event to a JSON Lines audit store, then commits the candidate state. If append fails, live state remains unchanged. Replay reads the same records and applies them through the same domain behavior without writing them again. Rejected and duplicate events are retained in the audit stream so replay reproduces outcomes and state exactly.

## Domain behavior

### Orders

- A submitted order has a unique order ID, symbol, side, positive quantity, and positive limit price.
- Initial status is `NEW`; accumulated filled quantity is zero.
- An order can move from `NEW` or `PARTIALLY_FILLED` to `CANCELLED`.
- Executions move the order to `PARTIALLY_FILLED` or `FILLED`.
- A cancelled, rejected, or filled order cannot receive a new execution.
- An execution cannot make cumulative filled quantity exceed ordered quantity.
- Reusing an existing order ID is rejected.

### Risk

- Pre-trade checks apply to order submission using the projected position after all existing active orders and the new order fill. Existing remaining buy quantity is positive and existing remaining sell quantity is negative.
- `max_abs_position` limits the absolute projected net quantity per symbol.
- `max_abs_notional` limits `abs(projected position * order limit price)` per symbol.
- Limits are configurable per symbol, with a required default limit.
- Risk rejection creates a rejected order record with a human-readable reason. The rejected submission remains in the audit event stream but never becomes a tradable active order.

### Positions and P&L

- Buy quantities are positive and sell quantities are negative.
- Average cost uses the weighted-average method while increasing a position in the same direction.
- Reducing a position realizes P&L against average cost.
- Crossing through zero realizes P&L on the closed portion and sets average cost to the execution price for the newly opened remainder.
- Unrealized P&L uses the latest known market price; it is zero until a market price exists.
- Total P&L equals realized plus unrealized P&L.

### Idempotency

- Every execution has a globally unique `execution_id`.
- A repeated execution ID is ignored before any state change, even if its repeated payload differs.
- Ignored duplicates are represented in the processing result and structured log.

### Persistence and replay

- Every validly decoded business event, including events with rejected or ignored outcomes, is appended to a JSON Lines audit file before candidate state is committed.
- Each line contains schema version, event type, event ID, occurred-at timestamp, and event payload.
- Replay preserves file order and uses the normal validation/application path with persistence disabled.
- Replaying the same complete log into a fresh engine yields an identical serializable state snapshot.
- A malformed or unknown event record raises an explicit serialization error with the line number.
- An append failure raises an event-store error and leaves engine state unchanged.

### Structured logging

- A JSON log record is emitted for every processed, rejected, or ignored event.
- Fields include event type, event ID, processing status, and relevant order, execution, or symbol identifiers.
- Rejection and ignore records include a reason.

## Project structure

- `src/trade_engine/events.py`: event dataclasses and enums.
- `src/trade_engine/models.py`: orders, positions, and serializable snapshots.
- `src/trade_engine/risk.py`: risk configuration and projected-limit validation.
- `src/trade_engine/engine.py`: dispatch, lifecycle validation, state changes, and processing results.
- `src/trade_engine/event_store.py`: JSON Lines codec, append, and replay loading.
- `src/trade_engine/logging.py`: JSON logging formatter and logger factory.
- `examples/run_demo.py`: synthetic end-to-end scenario.
- `tests/`: focused unit tests plus replay and workflow integration tests.
- `README.md`: explanation, setup, architecture, examples, and limitations.

## Acceptance criteria

- A demo scenario submits orders, records partial and full fills, changes prices, rejects a risk breach, ignores a duplicate execution, and prints final state.
- Unit tests cover lifecycle transitions, both risk limits, open-order risk reservation, duplicate executions, long and short P&L, position crossing, malformed events, and append failure atomicity.
- Integration tests prove complete workflow behavior and exact state equality after replay.
- `pytest` and `ruff check .` complete successfully on Python 3.11+.
- GitHub Actions runs both checks on pushes and pull requests.
- The repository contains no secrets, private datasets, or claims of live-trading readiness.

## Builder decisions

- Exact internal helper names and exception hierarchy.
- Formatting of console demo output.
- Test fixture organization.
- README visual style, provided all acceptance criteria are documented.
