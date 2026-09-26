from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConditionalExit:
    """
    Public SDK representation of a server-managed conditional exit.

    Decimal-like API values remain strings so the SDK never converts
    monetary values through binary floating point.
    """

    id: int
    market_id: int
    market_name: str
    parent_order_id: int
    parent_order_request_id: int | None
    oco_group_id: str | None
    type: str
    execution_type: str
    side: str
    trigger_price: str
    requested_quantity: str | None
    status: str
    trigger_order_request_id: int | None
    created_at: str
    activated_at: str | None
    triggered_at: str | None
    executed_at: str | None
    canceled_at: str | None

    @classmethod
    def from_api(cls, data: dict) -> "ConditionalExit":
        """
        Build a ConditionalExit from one object returned by the REST API.
        """
        return cls(
            id=data["id"],
            market_id=data["market_id"],
            market_name=data["market_name"],
            parent_order_id=data["parent_order_id"],
            parent_order_request_id=data.get("parent_order_request_id"),
            oco_group_id=data.get("oco_group_id"),
            type=data["type"],
            execution_type=data["execution_type"],
            side=data["side"],
            trigger_price=data["trigger_price"],
            requested_quantity=data.get("requested_quantity"),
            status=data["status"],
            trigger_order_request_id=data.get("trigger_order_request_id"),
            created_at=data["created_at"],
            activated_at=data.get("activated_at"),
            triggered_at=data.get("triggered_at"),
            executed_at=data.get("executed_at"),
            canceled_at=data.get("canceled_at"),
        )
