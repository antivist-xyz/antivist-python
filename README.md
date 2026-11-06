# antivist-python

Official synchronous Python SDK for the Antivist Markets REST API.

Antivist is developing perpetual markets for sports exposure. Unlike event-expiring prediction contracts, positions on Antivist are designed to persist across individual sporting events. Trading prices emerge from the interaction of orders in the market; the exchange does not set them using an external probability model.

This SDK provides a thin, authenticated HTTP interface for market data, order entry, account information, and server-managed conditional exits. It does **not** implement a trading strategy, market-making algorithm, or external hedge execution.

**Status:** SDK version `0.1.0`; development and testnet use. The API and SDK may evolve.

## Requirements and installation

- Python **3.11+**
- Access to an Antivist API endpoint and credentials for the operations you intend to perform

Install from the official GitHub repository:

```bash
python3 -m pip install "git+https://github.com/antivist-xyz/antivist-python.git"
```

The package is imported as `antivist`:

```python
from antivist import AntivistClient, AntivistAPIError
```

This README does not assume a PyPI release is available. For reproducible deployments, pin the Git dependency to a reviewed tag or commit rather than tracking the default branch.

## Authentication

Create an Antivist API key and secret through an authorized account. The client signs requests automatically using **HMAC-SHA256**, with a timestamp, unique nonce, and a hash of the exact HTTP request body. You do not need to construct signing headers yourself.

Store credentials outside source control:

```bash
export ANTIVIST_BASE_URL="https://testnet.antivist.xyz"
export ANTIVIST_API_KEY="YOUR_API_KEY"
export ANTIVIST_API_SECRET="YOUR_API_SECRET"
```

All methods in the current SDK go through the signed request client, including market-data requests. The examples below therefore initialize the client with credentials; they do not imply that every underlying market-data endpoint necessarily requires authentication.

## Quick start: inspect a market

This example reads market information and **does not submit orders**.

```python
import os

from antivist import AntivistClient

client = AntivistClient(
    base_url=os.environ["ANTIVIST_BASE_URL"],
    api_key=os.environ["ANTIVIST_API_KEY"],
    api_secret=os.environ["ANTIVIST_API_SECRET"],
)

# List available markets and inspect one team market by slug.
markets = client.get_markets()
market = client.get_market("manchester-city")

print(markets)
print(market)

# Use an actual market ID from the market metadata.
market_id = 4  # Example only: replace with the ID shown in the market metadata.
print(client.get_order_book(market_id))
print(client.get_market_trades(market_id))
print(client.get_market_mark("manchester-city"))
```

Market availability, IDs, slugs and metadata depend on the configured environment. Inspect the API response before making assumptions about individual fields.

## Trading

**Warning:** The following calls can create or cancel orders on the configured exchange. Use a testnet account and verify market rules, account permissions, quantity and price before enabling execution.

### Submit a limit order

```python
import uuid

response = client.submit_order(
    market_id=4,                 # Example only; replace with an actual market ID.
    side="BUY",                 # BUY or SELL
    price="1000.00",           # Decimal values are passed as strings.
    quantity="0.100",
    leverage="1",
    post_only=True,
    reduce_only=False,
    client_order_id=f"example-{uuid.uuid4()}",
)

print(response)
```

The SDK exposes `submit_order` for limit orders. `post_only` and `reduce_only` are request flags passed to the exchange; the server is authoritative on validation, matching, fills and order state. Do not infer acceptance or an open resting order solely from the absence of a Python exception—inspect the returned response.

### Orders and cancellation

```python
# Open orders belonging to the authenticated account.
open_orders = client.get_orders(market_id=4)
print(open_orders)

# Cancel an order using an ID obtained from the API response.
# client.cancel_order(order_id=123)

# Batch requests take lists of SDK-shaped dictionaries or order IDs.
# client.submit_orders([{"market_id": 4, "side": "BUY", "price": "1000.00",
#                        "quantity": "0.100", "leverage": "1",
#                        "post_only": True, "reduce_only": False}])
# client.cancel_orders([123, 124])

# Cancels all open orders owned by the authenticated trading account:
# client.cancel_all_orders()
```

Batch size limits, supported parameters and order status transitions are enforced by the API. For trading automation, use unique `client_order_id` values and reconcile the returned order IDs and states with the exchange.

## Account state and risk

```python
print(client.get_positions())
print(client.get_orders())
print(client.get_executions())
print(client.get_order_history())
print(client.get_trades())
print(client.get_portfolio())
print(client.get_risk())
```

The SDK also exposes `get_funding_history()`, `get_pnl_history()` and `get_volume()`. These methods return API response data; this SDK does not itself calculate margin, P&L, risk limits or a funding model.

## Conditional exits: take profit and stop loss

The server can manage conditional exits tied to an existing parent order. Create a take-profit, stop-loss or both by supplying trigger prices:

```python
exits = client.create_conditional_exits(
    parent_order_id=123,  # Replace with an actual parent order ID.
    take_profit="1100.00",
    stop_loss="950.00",
)

for exit_order in exits:
    print(exit_order.id, exit_order.type, exit_order.status)
```

The return value is a `list[ConditionalExit]`, not an order-submission response dictionary.

```python
active = client.list_conditional_exits(status="ACTIVE")

if active:
    selected = client.get_conditional_exit(
        conditional_exit_id=active[0].id,
    )
    print(selected.trigger_price, selected.requested_quantity)

    # Only cancel if you intend to remove this protection:
    # canceled = client.cancel_conditional_exit(
    #     conditional_exit_id=selected.id,
    # )
```

Conditional-exit trigger evaluation is **server-side**, based on Mark Price. Triggered exits use reduce-only MARKET execution. When both take profit and stop loss are configured, the backend manages their OCO relationship. Effective exit size depends on parent fills and the currently reducible position, rather than being guaranteed by a client-side quantity. The `requested_quantity` field is not a guarantee of full execution.

`ConditionalExit` is a frozen dataclass with fields including `id`, `market_id`, `parent_order_id`, `type`, `side`, `trigger_price`, `requested_quantity`, `status`, `oco_group_id` and lifecycle timestamps. Price and quantity values remain strings to avoid binary floating-point conversion inside the SDK.

## Error handling

```python
import httpx
from antivist import AntivistAPIError, AntivistError

try:
    result = client.get_positions()
    print(result)
except AntivistAPIError as exc:
    # Non-successful HTTP response from Antivist.
    print("HTTP status:", exc.status_code)
    print("Error code:", exc.code)
    print("Message:", exc.message)
    print("Details:", exc.details)
except AntivistError as exc:
    # SDK-level validation, e.g. a conditional exit with no TP or SL.
    print("SDK error:", exc)
except httpx.HTTPError as exc:
    # Transport, timeout, connection or protocol failures.
    print("Network error:", exc)
```

The client does not implement automatic order retries. A network timeout after order submission may leave the execution result unknown: query exchange state before deciding whether to resubmit. Use `client_order_id` to help reconcile intent with exchange records.

## Client API reference

Methods below are defined on `AntivistClient`. Unless specified, methods return decoded JSON responses from the API. Exact response shapes are controlled by the server.

| Method | Purpose |
| --- | --- |
| `get_markets()` | List markets |
| `get_market(slug)` | Read one market's metadata |
| `get_market_mark(slug)` | Read persisted mark-price metadata |
| `get_order_book(market_id)` | Read a market order book |
| `get_market_trades(market_id)` | Read recent market trades |
| `submit_order(*, market_id, side, price, quantity, leverage="1", post_only=False, reduce_only=False, client_order_id=None)` | Submit a limit order |
| `submit_orders(orders)` | Batch-submit orders |
| `get_orders(market_id=None)` | Get authenticated account's open orders |
| `cancel_order(order_id)` | Cancel one owned order |
| `cancel_orders(order_ids)` | Batch-cancel orders |
| `cancel_all_orders()` | Cancel all owned open orders |
| `get_positions()` | Account positions |
| `get_executions()` | Account executions |
| `get_trades()` | Account trades |
| `get_order_history()` | Historical orders |
| `get_funding_history()` | Funding history |
| `get_pnl_history()` | P&L history |
| `get_portfolio()` | Portfolio metrics |
| `get_volume()` | Volume metrics |
| `get_risk()` | Authoritative account risk state |
| `create_conditional_exits(*, parent_order_id, take_profit=None, stop_loss=None)` | Create TP/SL resources; returns `list[ConditionalExit]` |
| `list_conditional_exits(*, market_id=None, status=None, parent_order_id=None)` | List conditional exits; returns `list[ConditionalExit]` |
| `get_conditional_exit(*, conditional_exit_id)` | Read one exit; returns `ConditionalExit` |
| `cancel_conditional_exit(*, conditional_exit_id)` | Cancel an exit; returns `ConditionalExit` |

The SDK is currently **synchronous**. It does not include native WebSocket subscriptions, an async client, market-making strategies, external-venue execution or automated hedging.

## Development

```bash
git clone https://github.com/antivist-xyz/antivist-python.git
cd antivist-python
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest -q
```

Tests use mocked HTTP transports for request serialization and signing behavior; they do not by themselves prove production exchange availability or successful live order execution.

## Related project

[Albridge](https://github.com/antivist-xyz/albridge) is a cross-venue liquidity-translation prototype built using the Antivist SDK. Its public demo can calculate theoretical quotes from external prediction-market data without submitting orders to Antivist.

## Disclaimer

This SDK provides access to trading APIs, not financial advice or a guarantee of execution, liquidity or profitability. Trading perpetual markets involves financial risk. Review API permissions, market rules and risk controls before deploying automated systems or using real capital.