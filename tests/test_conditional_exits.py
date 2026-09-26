import json

import httpx
import pytest

from antivist import (
    AntivistAPIError,
    AntivistClient,
    AntivistError,
    ConditionalExit,
)


def _conditional_exit(**overrides):
    data = {
        "id": 42,
        "market_id": 1,
        "market_name": "JUVE-USDC",
        "parent_order_id": 123,
        "parent_order_request_id": 456,
        "oco_group_id": "oco-1",
        "type": "TAKE_PROFIT",
        "execution_type": "MARKET",
        "side": "SELL",
        "trigger_price": "1100.00",
        "requested_quantity": "1.250",
        "status": "ACTIVE",
        "trigger_order_request_id": None,
        "created_at": "2026-09-26T12:00:00+00:00",
        "activated_at": None,
        "triggered_at": None,
        "executed_at": None,
        "canceled_at": None,
    }
    data.update(overrides)
    return data


def _client(handler):
    client = AntivistClient(
        base_url="https://testnet.antivist.xyz",
        api_key="antv_test",
        api_secret="test-secret",
    )
    client._http.close()
    client._http = httpx.Client(
        base_url=client.base_url,
        timeout=client.timeout,
        transport=httpx.MockTransport(handler),
    )
    return client


def test_create_conditional_exits_with_tp_and_sl_builds_expected_payload():
    # Scenario: both exits are requested in one SDK call.
    # Invariant: only the backend contract shape is serialized.
    # Regression prevented: flattening TP/SL fields or changing endpoint payload.
    def handler(request):
        assert request.method == "POST"
        assert request.url.path == "/api/match-engine/conditional-exits/"
        assert json.loads(request.content) == {
            "parent_order_id": 123,
            "take_profit": {"trigger_price": "1100.00"},
            "stop_loss": {"trigger_price": "950.00"},
        }
        return httpx.Response(
            201,
            json={"ok": True, "conditional_exits": [_conditional_exit()]},
        )

    result = _client(handler).create_conditional_exits(
        parent_order_id=123,
        take_profit="1100.00",
        stop_loss="950.00",
    )

    assert isinstance(result[0], ConditionalExit)


def test_create_conditional_exits_with_only_tp_omits_stop_loss():
    # Scenario: only take profit is requested.
    # Invariant: absent exits are omitted instead of serialized as null.
    # Regression prevented: backend receiving an unintended stop_loss key.
    def handler(request):
        assert json.loads(request.content) == {
            "parent_order_id": 123,
            "take_profit": {"trigger_price": "1100.00"},
        }
        return httpx.Response(
            201,
            json={"ok": True, "conditional_exits": [_conditional_exit()]},
        )

    _client(handler).create_conditional_exits(
        parent_order_id=123,
        take_profit="1100.00",
    )


def test_create_conditional_exits_with_only_sl_omits_take_profit():
    # Scenario: only stop loss is requested.
    # Invariant: absent exits are omitted instead of serialized as null.
    # Regression prevented: backend receiving an unintended take_profit key.
    def handler(request):
        assert json.loads(request.content) == {
            "parent_order_id": 123,
            "stop_loss": {"trigger_price": "950.00"},
        }
        return httpx.Response(
            201,
            json={
                "ok": True,
                "conditional_exits": [
                    _conditional_exit(
                        type="STOP_LOSS",
                        trigger_price="950.00",
                    )
                ],
            },
        )

    _client(handler).create_conditional_exits(
        parent_order_id=123,
        stop_loss="950.00",
    )


def test_create_conditional_exits_requires_tp_or_sl_without_http_request():
    # Scenario: caller supplies neither conditional exit.
    # Invariant: obvious malformed calls fail before transport is touched.
    # Regression prevented: unnecessary signed HTTP requests with empty intent.
    called = False

    def handler(request):
        nonlocal called
        called = True
        return httpx.Response(500)

    client = _client(handler)

    with pytest.raises(AntivistError, match="At least one"):
        client.create_conditional_exits(parent_order_id=123)

    assert called is False


def test_list_conditional_exits_without_filters_has_no_query_string():
    # Scenario: list all conditional exits.
    # Invariant: no synthetic filters are added.
    # Regression prevented: accidental query defaults changing server results.
    def handler(request):
        assert request.method == "GET"
        assert request.url.path == "/api/match-engine/conditional-exits/"
        assert request.url.query == b""
        return httpx.Response(
            200,
            json={"ok": True, "conditional_exits": [_conditional_exit()]},
        )

    assert len(_client(handler).list_conditional_exits()) == 1


@pytest.mark.parametrize(
    ("kwargs", "expected_query"),
    [
        ({"market_id": 1}, "market_id=1"),
        ({"status": "ACTIVE"}, "status=ACTIVE"),
        ({"parent_order_id": 123}, "parent_order_id=123"),
    ],
)
def test_list_conditional_exits_maps_supported_filters(kwargs, expected_query):
    # Scenario: each documented backend filter is used independently.
    # Invariant: SDK query parameter names match the REST contract exactly.
    # Regression prevented: renamed, dropped, or invented filter parameters.
    def handler(request):
        assert request.url.query.decode() == expected_query
        return httpx.Response(
            200,
            json={"ok": True, "conditional_exits": []},
        )

    assert _client(handler).list_conditional_exits(**kwargs) == []


def test_get_conditional_exit_uses_detail_path():
    # Scenario: fetch one conditional exit.
    # Invariant: the resource id is placed in the canonical REST detail path.
    # Regression prevented: calling list endpoint or malformed detail URLs.
    def handler(request):
        assert request.method == "GET"
        assert request.url.path == "/api/match-engine/conditional-exits/42/"
        return httpx.Response(
            200,
            json={"ok": True, "conditional_exit": _conditional_exit()},
        )

    assert _client(handler).get_conditional_exit(
        conditional_exit_id=42
    ).id == 42


def test_cancel_conditional_exit_uses_delete():
    # Scenario: cancel an existing conditional exit.
    # Invariant: cancellation uses DELETE on the detail resource.
    # Regression prevented: reusing the POST order-cancel convention.
    def handler(request):
        assert request.method == "DELETE"
        assert request.url.path == "/api/match-engine/conditional-exits/42/"
        return httpx.Response(
            200,
            json={
                "ok": True,
                "conditional_exit": _conditional_exit(status="CANCELED"),
            },
        )

    assert _client(handler).cancel_conditional_exit(
        conditional_exit_id=42
    ).status == "CANCELED"


def test_conditional_exit_requests_reuse_existing_signed_request_layer():
    # Scenario: conditional-exit request goes through the normal client transport.
    # Invariant: existing HMAC headers are present without endpoint-specific auth.
    # Regression prevented: a second unsigned or manually signed HTTP path.
    def handler(request):
        assert request.headers["X-Antivist-Api-Key"] == "antv_test"
        assert request.headers["X-Antivist-Timestamp"]
        assert request.headers["X-Antivist-Nonce"]
        assert request.headers["X-Antivist-Signature"]
        return httpx.Response(
            200,
            json={"ok": True, "conditional_exits": []},
        )

    _client(handler).list_conditional_exits()


def test_conditional_exit_api_error_uses_existing_exception_and_details():
    # Scenario: backend rejects a conditional exit request.
    # Invariant: status, code, message and details survive SDK error conversion.
    # Regression prevented: conditional-exit-specific exception fragmentation.
    def handler(request):
        return httpx.Response(
            400,
            json={
                "error": {
                    "code": "INVALID_TRIGGER_PRICE",
                    "message": "Invalid trigger price.",
                    "details": {"trigger_price": "950.00"},
                }
            },
        )

    with pytest.raises(AntivistAPIError) as exc_info:
        _client(handler).create_conditional_exits(
            parent_order_id=123,
            stop_loss="950.00",
        )

    error = exc_info.value
    assert error.status_code == 400
    assert error.code == "INVALID_TRIGGER_PRICE"
    assert error.message == "Invalid trigger price."
    assert error.details == {"trigger_price": "950.00"}


def test_conditional_exit_decimal_values_remain_strings():
    # Scenario: API returns decimal-formatted trigger and quantity values.
    # Invariant: SDK never converts financial decimals through float.
    # Regression prevented: binary floating-point precision loss.
    model = ConditionalExit.from_api(_conditional_exit())

    assert model.trigger_price == "1100.00"
    assert isinstance(model.trigger_price, str)
    assert model.requested_quantity == "1.250"
    assert isinstance(model.requested_quantity, str)


def test_conditional_exit_parses_null_trigger_order_request_id():
    # Scenario: an exit has not created its trigger order yet.
    # Invariant: nullable foreign ids remain None.
    # Regression prevented: int coercion or KeyError before trigger.
    model = ConditionalExit.from_api(
        _conditional_exit(trigger_order_request_id=None)
    )

    assert model.trigger_order_request_id is None


def test_conditional_exit_parses_nullable_timestamps():
    # Scenario: an ACTIVE exit has not reached later lifecycle timestamps.
    # Invariant: nullable lifecycle timestamps remain None.
    # Regression prevented: parsing assumptions tied to EXECUTED state.
    model = ConditionalExit.from_api(
        _conditional_exit(
            activated_at=None,
            triggered_at=None,
            executed_at=None,
            canceled_at=None,
        )
    )

    assert model.activated_at is None
    assert model.triggered_at is None
    assert model.executed_at is None
    assert model.canceled_at is None
