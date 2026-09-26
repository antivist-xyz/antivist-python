import json

import httpx

import pytest

from antivist import AntivistAPIError, AntivistClient


def test_request_sends_signed_json_request():
    captured_request = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_request["method"] = request.method
        captured_request["url"] = str(request.url)
        captured_request["headers"] = dict(request.headers)
        captured_request["body"] = request.content

        return httpx.Response(
            200,
            json={"ok": True},
        )

    transport = httpx.MockTransport(handler)

    client = AntivistClient(
        base_url="https://testnet.antivist.xyz",
        api_key="antv_test",
        api_secret="test-secret",
    )

    # Replace the real HTTP client with a mocked transport.
    client._http.close()
    client._http = httpx.Client(
        base_url=client.base_url,
        timeout=client.timeout,
        transport=transport,
    )

    response = client._request(
        "POST",
        "/api/match-engine/orders/",
        json_body={
            "side": "BUY",
            "market_id": 1,
        },
    )

    assert response == {"ok": True}

    assert captured_request["method"] == "POST"
    assert captured_request["url"] == (
        "https://testnet.antivist.xyz/api/match-engine/orders/"
    )

    assert captured_request["body"] == (
        b'{"market_id":1,"side":"BUY"}'
    )

    headers = captured_request["headers"]

    assert headers["x-antivist-api-key"] == "antv_test"
    assert "x-antivist-timestamp" in headers
    assert "x-antivist-nonce" in headers
    assert "x-antivist-signature" in headers
    assert headers["content-type"] == "application/json"

from urllib.parse import urlparse

import httpx

from antivist import AntivistClient
from antivist.signing import (
    build_canonical_request,
    sha256_body,
    sign_request,
)


def test_request_signature_matches_received_http_request():
    api_secret = "test-secret"

    def handler(request: httpx.Request) -> httpx.Response:
        parsed_url = urlparse(str(request.url))

        timestamp = request.headers["X-Antivist-Timestamp"]
        nonce = request.headers["X-Antivist-Nonce"]
        received_signature = request.headers["X-Antivist-Signature"]

        body_hash = sha256_body(request.content)

        canonical_request = build_canonical_request(
            method=request.method,
            path=parsed_url.path,
            query_string=parsed_url.query,
            timestamp=timestamp,
            nonce=nonce,
            body_sha256=body_hash,
        )

        expected_signature = sign_request(
            api_secret=api_secret,
            canonical_request=canonical_request,
        )

        assert received_signature == expected_signature

        return httpx.Response(
            200,
            json={"ok": True},
        )

    transport = httpx.MockTransport(handler)

    client = AntivistClient(
        base_url="https://testnet.antivist.xyz",
        api_key="antv_test",
        api_secret=api_secret,
    )

    client._http.close()
    client._http = httpx.Client(
        base_url=client.base_url,
        timeout=client.timeout,
        transport=transport,
    )

    response = client._request(
        "POST",
        "/api/match-engine/orders/",
        json_body={
            "market_id": 1,
            "side": "BUY",
            "price": "1000.00",
            "quantity": "1.000",
        },
    )

    assert response == {"ok": True}

def test_submit_order_calls_orders_endpoint():
    captured_request = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_request["method"] = request.method
        captured_request["path"] = request.url.path
        captured_request["body"] = request.content

        return httpx.Response(
            201,
            json={
                "id": 123,
                "status": "ACCEPTED",
            },
        )

    transport = httpx.MockTransport(handler)

    client = AntivistClient(
        base_url="https://testnet.antivist.xyz",
        api_key="antv_test",
        api_secret="test-secret",
    )

    client._http.close()
    client._http = httpx.Client(
        base_url=client.base_url,
        timeout=client.timeout,
        transport=transport,
    )

    response = client.submit_order(
        market_id=1,
        side="BUY",
        price="1000.00",
        quantity="1.000",
        leverage="1",
    )

    assert captured_request["method"] == "POST"
    assert captured_request["path"] == "/api/match-engine/orders/"

    assert json.loads(captured_request["body"]) == {
        "market_id": 1,
        "side": "BUY",
        "price": "1000.00",
        "quantity": "1.000",
        "leverage": "1",
        "post_only": False,
        "reduce_only": False,
    }

    assert response == {
        "id": 123,
        "status": "ACCEPTED",
    }    

def test_request_raises_antivist_api_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            401,
            json={
                "error": {
                    "code": "AUTHENTICATION_FAILED",
                    "message": "Authentication failed.",
                }
            },
        )

    transport = httpx.MockTransport(handler)

    client = AntivistClient(
        base_url="https://testnet.antivist.xyz",
        api_key="antv_test",
        api_secret="wrong-secret",
    )

    client._http.close()
    client._http = httpx.Client(
        base_url=client.base_url,
        timeout=client.timeout,
        transport=transport,
    )

    with pytest.raises(AntivistAPIError) as exc_info:
        client.submit_order(
            market_id=1,
            side="BUY",
            price="1000.00",
            quantity="1.000",
        )

    error = exc_info.value

    assert error.status_code == 401
    assert error.code == "AUTHENTICATION_FAILED"
    assert error.message == "Authentication failed."
    assert error.response_body == {
        "error": {
            "code": "AUTHENTICATION_FAILED",
            "message": "Authentication failed.",
        }
    }

def test_get_orders_calls_orders_endpoint():
    captured_request = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_request["method"] = request.method
        captured_request["path"] = request.url.path
        captured_request["body"] = request.content

        return httpx.Response(
            200,
            json={
                "ok": True,
                "orders": [
                    {
                        "order_id": 38,
                        "market_id": 4,
                        "side": "BUY",
                        "price": "1000.00",
                        "quantity": "1.000",
                        "status": "OPEN",
                    }
                ],
            },
        )

    transport = httpx.MockTransport(handler)

    client = AntivistClient(
        base_url="https://testnet.antivist.xyz",
        api_key="antv_test",
        api_secret="test-secret",
    )

    client._http.close()
    client._http = httpx.Client(
        base_url=client.base_url,
        timeout=client.timeout,
        transport=transport,
    )

    response = client.get_orders()

    assert captured_request["method"] == "GET"
    assert captured_request["path"] == "/api/match-engine/orders/"
    assert captured_request["body"] == b""

    assert response["ok"] is True
    assert len(response["orders"]) == 1
    assert response["orders"][0]["order_id"] == 38


def test_cancel_order_calls_cancel_endpoint():
    captured_request = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_request["method"] = request.method
        captured_request["path"] = request.url.path
        captured_request["body"] = request.content

        return httpx.Response(
            200,
            json={
                "ok": True,
                "order": {
                    "order_id": 38,
                    "status": "CANCELED",
                },
            },
        )

    transport = httpx.MockTransport(handler)

    client = AntivistClient(
        base_url="https://testnet.antivist.xyz",
        api_key="antv_test",
        api_secret="test-secret",
    )

    client._http.close()
    client._http = httpx.Client(
        base_url=client.base_url,
        timeout=client.timeout,
        transport=transport,
    )

    response = client.cancel_order(38)

    assert captured_request["method"] == "POST"
    assert captured_request["path"] == "/api/match-engine/orders/38/cancel/"
    assert captured_request["body"] == b""

    assert response == {
        "ok": True,
        "order": {
            "order_id": 38,
            "status": "CANCELED",
        },
    }        

def test_cancel_all_orders_calls_cancel_all_endpoint():
    captured_request = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_request["method"] = request.method
        captured_request["path"] = request.url.path
        captured_request["body"] = request.content

        return httpx.Response(
            200,
            json={
                "ok": True,
                "canceled_order_ids": [38, 39],
            },
        )

    transport = httpx.MockTransport(handler)

    client = AntivistClient(
        base_url="https://testnet.antivist.xyz",
        api_key="antv_test",
        api_secret="test-secret",
    )

    client._http.close()
    client._http = httpx.Client(
        base_url=client.base_url,
        timeout=client.timeout,
        transport=transport,
    )

    response = client.cancel_all_orders()

    assert captured_request["method"] == "POST"
    assert captured_request["path"] == "/api/match-engine/orders/cancel-all/"
    assert captured_request["body"] == b""

    assert response == {
        "ok": True,
        "canceled_order_ids": [38, 39],
    }    

def test_get_positions_calls_positions_endpoint():
    captured_request = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_request["method"] = request.method
        captured_request["path"] = request.url.path
        captured_request["body"] = request.content

        return httpx.Response(
            200,
            json={
                "ok": True,
                "positions": [
                    {
                        "market_id": 4,
                        "market_name": "JUVE-USDC",
                        "quantity": "1.000",
                        "entry_price": "1000.00",
                    }
                ],
            },
        )

    transport = httpx.MockTransport(handler)

    client = AntivistClient(
        base_url="https://testnet.antivist.xyz",
        api_key="antv_test",
        api_secret="test-secret",
    )

    client._http.close()
    client._http = httpx.Client(
        base_url=client.base_url,
        timeout=client.timeout,
        transport=transport,
    )

    response = client.get_positions()

    assert captured_request["method"] == "GET"
    assert captured_request["path"] == "/api/trading-accounts/positions/"
    assert captured_request["body"] == b""

    assert response["ok"] is True
    assert len(response["positions"]) == 1    

def test_get_executions_calls_executions_endpoint():
    captured_request = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_request["method"] = request.method
        captured_request["path"] = request.url.path
        captured_request["body"] = request.content

        return httpx.Response(
            200,
            json={
                "ok": True,
                "executions": [
                    {
                        "execution_id": 12,
                        "market_id": 4,
                        "price": "1000.00",
                        "quantity": "1.000",
                    }
                ],
            },
        )

    transport = httpx.MockTransport(handler)

    client = AntivistClient(
        base_url="https://testnet.antivist.xyz",
        api_key="antv_test",
        api_secret="test-secret",
    )

    client._http.close()
    client._http = httpx.Client(
        base_url=client.base_url,
        timeout=client.timeout,
        transport=transport,
    )

    response = client.get_executions()

    assert captured_request["method"] == "GET"
    assert captured_request["path"] == "/api/trading-accounts/executions/"
    assert captured_request["body"] == b""

    assert response["ok"] is True
    assert len(response["executions"]) == 1    

def test_get_trades_calls_trades_endpoint():
    captured_request = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_request["method"] = request.method
        captured_request["path"] = request.url.path
        captured_request["body"] = request.content

        return httpx.Response(
            200,
            json={
                "ok": True,
                "trades": [
                    {
                        "trade_id": 21,
                        "market_id": 4,
                        "price": "1000.00",
                        "quantity": "1.000",
                    }
                ],
            },
        )

    transport = httpx.MockTransport(handler)

    client = AntivistClient(
        base_url="https://testnet.antivist.xyz",
        api_key="antv_test",
        api_secret="test-secret",
    )

    client._http.close()
    client._http = httpx.Client(
        base_url=client.base_url,
        timeout=client.timeout,
        transport=transport,
    )

    response = client.get_trades()

    assert captured_request["method"] == "GET"
    assert captured_request["path"] == "/api/trading-accounts/trades/"
    assert captured_request["body"] == b""

    assert response["ok"] is True
    assert len(response["trades"]) == 1

def test_get_trades_calls_trades_endpoint():
    captured_request = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_request["method"] = request.method
        captured_request["path"] = request.url.path
        captured_request["body"] = request.content

        return httpx.Response(
            200,
            json={
                "ok": True,
                "trades": [
                    {
                        "trade_id": 21,
                        "market_id": 4,
                        "price": "1000.00",
                        "quantity": "1.000",
                    }
                ],
            },
        )

    transport = httpx.MockTransport(handler)

    client = AntivistClient(
        base_url="https://testnet.antivist.xyz",
        api_key="antv_test",
        api_secret="test-secret",
    )

    client._http.close()
    client._http = httpx.Client(
        base_url=client.base_url,
        timeout=client.timeout,
        transport=transport,
    )

    response = client.get_trades()

    assert captured_request["method"] == "GET"
    assert captured_request["path"] == "/api/trading-accounts/trades/"
    assert captured_request["body"] == b""

    assert response["ok"] is True
    assert len(response["trades"]) == 1

def test_get_order_history_calls_order_history_endpoint():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/api/trading-accounts/order-history/"

        return httpx.Response(
            200,
            json={
                "ok": True,
                "orders": [],
            },
        )

    transport = httpx.MockTransport(handler)

    client = AntivistClient(
        base_url="https://testnet.antivist.xyz",
        api_key="antv_test",
        api_secret="test-secret",
    )

    client._http.close()
    client._http = httpx.Client(
        base_url=client.base_url,
        timeout=client.timeout,
        transport=transport,
    )

    response = client.get_order_history()

    assert response == {
        "ok": True,
        "orders": [],
    }


def test_get_funding_history_calls_funding_history_endpoint():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/api/trading-accounts/funding-history/"

        return httpx.Response(
            200,
            json={
                "ok": True,
                "funding_history": [],
            },
        )

    transport = httpx.MockTransport(handler)

    client = AntivistClient(
        base_url="https://testnet.antivist.xyz",
        api_key="antv_test",
        api_secret="test-secret",
    )

    client._http.close()
    client._http = httpx.Client(
        base_url=client.base_url,
        timeout=client.timeout,
        transport=transport,
    )

    response = client.get_funding_history()

    assert response == {
        "ok": True,
        "funding_history": [],
    }


def test_get_pnl_history_calls_pnl_history_endpoint():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/api/trading-accounts/pnl-history/"

        return httpx.Response(
            200,
            json={
                "ok": True,
                "pnl_history": [],
            },
        )

    transport = httpx.MockTransport(handler)

    client = AntivistClient(
        base_url="https://testnet.antivist.xyz",
        api_key="antv_test",
        api_secret="test-secret",
    )

    client._http.close()
    client._http = httpx.Client(
        base_url=client.base_url,
        timeout=client.timeout,
        transport=transport,
    )

    response = client.get_pnl_history()

    assert response == {
        "ok": True,
        "pnl_history": [],
    }


def test_get_portfolio_calls_portfolio_endpoint():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/api/trading-accounts/portfolio/"

        return httpx.Response(
            200,
            json={
                "ok": True,
                "portfolio": {},
            },
        )

    transport = httpx.MockTransport(handler)

    client = AntivistClient(
        base_url="https://testnet.antivist.xyz",
        api_key="antv_test",
        api_secret="test-secret",
    )

    client._http.close()
    client._http = httpx.Client(
        base_url=client.base_url,
        timeout=client.timeout,
        transport=transport,
    )

    response = client.get_portfolio()

    assert response == {
        "ok": True,
        "portfolio": {},
    }


def test_get_volume_calls_volume_endpoint():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/api/trading-accounts/volume/"

        return httpx.Response(
            200,
            json={
                "ok": True,
                "volume": {},
            },
        )

    transport = httpx.MockTransport(handler)

    client = AntivistClient(
        base_url="https://testnet.antivist.xyz",
        api_key="antv_test",
        api_secret="test-secret",
    )

    client._http.close()
    client._http = httpx.Client(
        base_url=client.base_url,
        timeout=client.timeout,
        transport=transport,
    )

    response = client.get_volume()

    assert response == {
        "ok": True,
        "volume": {},
    }

def test_get_markets_calls_markets_endpoint():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/api/markets/"

        return httpx.Response(
            200,
            json={
                "ok": True,
                "markets": [],
            },
        )

    transport = httpx.MockTransport(handler)

    client = AntivistClient(
        base_url="https://testnet.antivist.xyz",
        api_key="antv_test",
        api_secret="test-secret",
    )

    client._http.close()
    client._http = httpx.Client(
        base_url=client.base_url,
        timeout=client.timeout,
        transport=transport,
    )

    response = client.get_markets()

    assert response == {
        "ok": True,
        "markets": [],
    }


def test_get_market_calls_market_detail_endpoint():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/api/markets/juventus/"

        return httpx.Response(
            200,
            json={
                "ok": True,
                "market": {
                    "market_id": 4,
                    "market_name": "JUVE-USDC",
                },
            },
        )

    transport = httpx.MockTransport(handler)

    client = AntivistClient(
        base_url="https://testnet.antivist.xyz",
        api_key="antv_test",
        api_secret="test-secret",
    )

    client._http.close()
    client._http = httpx.Client(
        base_url=client.base_url,
        timeout=client.timeout,
        transport=transport,
    )

    response = client.get_market("juventus")

    assert response["ok"] is True


def test_get_order_book_calls_order_book_endpoint():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/api/match-engine/markets/4/order-book/"

        return httpx.Response(
            200,
            json={
                "ok": True,
                "bids": [],
                "asks": [],
            },
        )

    transport = httpx.MockTransport(handler)

    client = AntivistClient(
        base_url="https://testnet.antivist.xyz",
        api_key="antv_test",
        api_secret="test-secret",
    )

    client._http.close()
    client._http = httpx.Client(
        base_url=client.base_url,
        timeout=client.timeout,
        transport=transport,
    )

    response = client.get_order_book(4)

    assert response["ok"] is True


def test_get_market_trades_calls_public_trades_endpoint():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/api/match-engine/markets/4/trades/"

        return httpx.Response(
            200,
            json={
                "ok": True,
                "trades": [],
            },
        )

    transport = httpx.MockTransport(handler)

    client = AntivistClient(
        base_url="https://testnet.antivist.xyz",
        api_key="antv_test",
        api_secret="test-secret",
    )

    client._http.close()
    client._http = httpx.Client(
        base_url=client.base_url,
        timeout=client.timeout,
        transport=transport,
    )

    response = client.get_market_trades(4)

    assert response["ok"] is True

def test_get_risk_calls_risk_endpoint():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/api/trading-accounts/risk/"

        return httpx.Response(
            200,
            json={
                "ok": True,
                "collateral_balance": "100000.00000000",
                "reserved_order_margin": "1.00245000",
                "position_margin": "250.00000000",
                "available_to_trade": "99748.99755000",
            },
        )

    transport = httpx.MockTransport(handler)

    client = AntivistClient(
        base_url="https://testnet.antivist.xyz",
        api_key="antv_test",
        api_secret="test-secret",
    )

    client._http.close()
    client._http = httpx.Client(
        base_url=client.base_url,
        timeout=client.timeout,
        transport=transport,
    )

    response = client.get_risk()

    assert response == {
        "ok": True,
        "collateral_balance": "100000.00000000",
        "reserved_order_margin": "1.00245000",
        "position_margin": "250.00000000",
        "available_to_trade": "99748.99755000",
    }                

def test_get_market_preserves_polymarket_oracle_sources():
    expected_oracle_sources = {
        "polymarket": {
            "last_synced_at": "2026-09-08T10:00:00+00:00",
            "markets": [
                {
                    "id": "pm-market-123",
                    "condition_id": "condition-abc",
                    "slug": "juventus-chelsea",
                    "outcomes": [
                        {
                            "name": "Chelsea FC",
                            "token_id": "token-chelsea",
                        },
                        {
                            "name": "Draw",
                            "token_id": "token-draw",
                        },
                        {
                            "name": "Juventus Turin",
                            "token_id": "token-juventus",
                        },
                    ],
                },
            ],
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/api/markets/juventus/"

        return httpx.Response(
            200,
            json={
                "id": 4,
                "market_name": "JUVE-USDC",
                "oracle_sources": expected_oracle_sources,
            },
        )

    transport = httpx.MockTransport(handler)

    client = AntivistClient(
        base_url="https://testnet.antivist.xyz",
        api_key="antv_test",
        api_secret="test-secret",
    )

    client._http.close()
    client._http = httpx.Client(
        base_url=client.base_url,
        timeout=client.timeout,
        transport=transport,
    )

    response = client.get_market("juventus")

    assert response["oracle_sources"] == expected_oracle_sources
    assert (
        response["oracle_sources"]["polymarket"]["markets"][0]
        ["outcomes"][2]["token_id"]
        == "token-juventus"
    )        