import json
import time
import uuid
from urllib.parse import urlparse

import httpx

from .signing import (
    build_canonical_request,
    sha256_body,
    sign_request,
)

from .exceptions import AntivistAPIError, AntivistError
from .models import ConditionalExit


class AntivistClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        api_secret: str,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.api_secret = api_secret
        self.timeout = timeout

        self._http = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json_body: dict | None = None,
    ):
        method = method.upper()

        # Serialize JSON ourselves so that the exact signed bytes
        # are the same bytes sent over HTTP.
        if json_body is None:
            body = b""
        else:
            body = json.dumps(
                json_body,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")

        timestamp = str(int(time.time() * 1000))
        nonce = str(uuid.uuid4())

        # Build the exact raw query string that will be signed and sent.
        request = self._http.build_request(
            method=method,
            url=path,
            params=params,
            content=body,
        )

        parsed_url = urlparse(str(request.url))
        query_string = parsed_url.query

        body_hash = sha256_body(body)

        canonical_request = build_canonical_request(
            method=method,
            path=parsed_url.path,
            query_string=query_string,
            timestamp=timestamp,
            nonce=nonce,
            body_sha256=body_hash,
        )

        signature = sign_request(
            api_secret=self.api_secret,
            canonical_request=canonical_request,
        )

        request.headers.update(
            {
                "X-Antivist-Api-Key": self.api_key,
                "X-Antivist-Timestamp": timestamp,
                "X-Antivist-Nonce": nonce,
                "X-Antivist-Signature": signature,
            }
        )

        if json_body is not None:
            request.headers["Content-Type"] = "application/json"

        response = self._http.send(request)

        if response.is_error:
            try:
                response_body = response.json()
            except ValueError:
                response_body = None

            error_code = None
            error_message = None
            error_details = None

            if isinstance(response_body, dict):
                error = response_body.get("error")

                if isinstance(error, dict):
                    error_code = error.get("code")
                    error_message = error.get("message")
                    error_details = error.get("details")

            raise AntivistAPIError(
                status_code=response.status_code,
                code=error_code,
                message=error_message,
                details=error_details,
                response_body=response_body,
            )

        if not response.content:
            return None

        return response.json()

    def submit_order(
        self,
        *,
        market_id: int,
        side: str,
        price: str,
        quantity: str,
        leverage: str = "1",
        post_only: bool = False,
        reduce_only: bool = False,
        client_order_id: str | None = None,
    ):
        """
        Submit a new limit order to Antivist.
        """
        body = {
            "market_id": market_id,
            "side": side,
            "price": price,
            "quantity": quantity,
            "leverage": leverage,
            "post_only": post_only,
            "reduce_only": reduce_only,
        }

        if client_order_id is not None:
            body["client_order_id"] = client_order_id

        return self._request(
            "POST",
            "/api/match-engine/orders/",
            json_body=body,
        )

    def submit_orders(self, orders: list[dict]):
        """
        Submit multiple orders in a single request.
        """
        return self._request(
            "POST",
            "/api/match-engine/orders/batch-submit/",
            json_body={"orders": orders},
        )

    def get_orders(self):
        """
        Return the authenticated trading account's open orders.
        """
        return self._request(
            "GET",
            "/api/match-engine/orders/",
        )

    def cancel_order(self, order_id: int):
        """
        Cancel an open order owned by the authenticated trading account.
        """
        return self._request(
            "POST",
            f"/api/match-engine/orders/{order_id}/cancel/",
        )

    def cancel_orders(self, order_ids: list[int]):
        """
        Cancel multiple orders in a single request.
        """
        return self._request(
            "POST",
            "/api/match-engine/orders/batch-cancel/",
            json_body={"order_ids": order_ids},
        )

    def cancel_all_orders(self):
        """
        Cancel all open orders owned by the authenticated trading account.
        """
        return self._request(
            "POST",
            "/api/match-engine/orders/cancel-all/",
        )

    def get_positions(self):
        """
        Return positions for the authenticated trading account.
        """
        return self._request(
            "GET",
            "/api/trading-accounts/positions/",
        )

    def get_executions(self):
        """
        Return executions for the authenticated trading account.
        """
        return self._request(
            "GET",
            "/api/trading-accounts/executions/",
        )

    def get_trades(self):
        """
        Return trades for the authenticated trading account.
        """
        return self._request(
            "GET",
            "/api/trading-accounts/trades/",
        )

    def get_order_history(self):
        """
        Return order history for the authenticated trading account.
        """
        return self._request(
            "GET",
            "/api/trading-accounts/order-history/",
        )

    def get_funding_history(self):
        """
        Return funding history for the authenticated trading account.
        """
        return self._request(
            "GET",
            "/api/trading-accounts/funding-history/",
        )

    def get_pnl_history(self):
        """
        Return PnL history for the authenticated trading account.
        """
        return self._request(
            "GET",
            "/api/trading-accounts/pnl-history/",
        )

    def get_portfolio(self):
        """
        Return portfolio metrics for the authenticated trading account.
        """
        return self._request(
            "GET",
            "/api/trading-accounts/portfolio/",
        )

    def get_volume(self):
        """
        Return volume metrics for the authenticated trading account.
        """
        return self._request(
            "GET",
            "/api/trading-accounts/volume/",
        )

    def get_markets(self):
        """
        Return all available Antivist markets.
        """
        return self._request(
            "GET",
            "/api/markets/",
        )

    def get_market(self, slug: str):
        """
        Return metadata for a single Antivist market.
        """
        return self._request(
            "GET",
            f"/api/markets/{slug}/",
        )

    def get_order_book(self, market_id: int):
        """
        Return the current order book for a market.
        """
        return self._request(
            "GET",
            f"/api/match-engine/markets/{market_id}/order-book/",
        )

    def get_market_trades(self, market_id: int):
        """
        Return recent public trades for a market.
        """
        return self._request(
            "GET",
            f"/api/match-engine/markets/{market_id}/trades/",
        )

    def get_risk(self):
        """
        Return authoritative risk state for the authenticated trading account.
        """
        return self._request(
            "GET",
            "/api/trading-accounts/risk/",
        )

    def create_conditional_exits(
        self,
        *,
        parent_order_id: int,
        take_profit: str | None = None,
        stop_loss: str | None = None,
    ) -> list[ConditionalExit]:
        """
        Create one or both server-managed conditional exits for a parent order.
        """
        if take_profit is None and stop_loss is None:
            raise AntivistError(
                "At least one of take_profit or stop_loss must be provided."
            )

        body = {"parent_order_id": parent_order_id}

        if take_profit is not None:
            body["take_profit"] = {"trigger_price": take_profit}

        if stop_loss is not None:
            body["stop_loss"] = {"trigger_price": stop_loss}

        response = self._request(
            "POST",
            "/api/match-engine/conditional-exits/",
            json_body=body,
        )

        return [
            ConditionalExit.from_api(item)
            for item in response["conditional_exits"]
        ]

    def list_conditional_exits(
        self,
        *,
        market_id: int | None = None,
        status: str | None = None,
        parent_order_id: int | None = None,
    ) -> list[ConditionalExit]:
        """
        Return conditional exits, optionally filtered by supported REST params.
        """
        params = {}

        if market_id is not None:
            params["market_id"] = market_id

        if status is not None:
            params["status"] = status

        if parent_order_id is not None:
            params["parent_order_id"] = parent_order_id

        response = self._request(
            "GET",
            "/api/match-engine/conditional-exits/",
            params=params or None,
        )

        return [
            ConditionalExit.from_api(item)
            for item in response["conditional_exits"]
        ]

    def get_conditional_exit(
        self,
        *,
        conditional_exit_id: int,
    ) -> ConditionalExit:
        """
        Return one conditional exit owned by the authenticated account.
        """
        response = self._request(
            "GET",
            f"/api/match-engine/conditional-exits/{conditional_exit_id}/",
        )

        return ConditionalExit.from_api(response["conditional_exit"])

    def cancel_conditional_exit(
        self,
        *,
        conditional_exit_id: int,
    ) -> ConditionalExit:
        """
        Cancel one cancelable conditional exit.
        """
        response = self._request(
            "DELETE",
            f"/api/match-engine/conditional-exits/{conditional_exit_id}/",
        )

        return ConditionalExit.from_api(response["conditional_exit"])
