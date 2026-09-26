import os
import uuid
from antivist import AntivistAPIError, AntivistClient


client = AntivistClient(
    base_url=os.environ["ANTIVIST_BASE_URL"],
    api_key=os.environ["ANTIVIST_API_KEY"],
    api_secret=os.environ["ANTIVIST_API_SECRET"],
)

try:
    order = client.submit_order(
        market_id=4,
        side="BUY",
        price="1000.00",
        quantity="1.000",
        leverage= "1",
        client_order_id=f"albridge-test-{uuid.uuid4()}",
    )

    created_order = client.submit_order(
        market_id=4,
        side="BUY",
        price="1000.00",
        quantity="1.000",
        leverage="1",
        client_order_id=f"albridge-test-{uuid.uuid4()}",
    )

    order_id = created_order["order"]["order_id"]

    print("ORDER SUBMITTED")
    print(order)

    print()
    print("OPEN ORDERS")
    print(client.get_orders())

    print()
    print("CANCEL ORDER")
    print(client.cancel_order(order_id))

    print()
    print("OPEN ORDERS AFTER CANCEL")
    print(client.get_orders())

    print()
    print("OPEN ORDERS BEFORE CANCEL ALL")
    print(client.get_orders())

    print()
    print("CANCEL ALL")
    print(client.cancel_all_orders())

    print()
    print("OPEN ORDERS AFTER CANCEL ALL")
    print(client.get_orders())

    print()
    print("POSITIONS")
    print(client.get_positions())

    print()
    print("EXECUTIONS")
    print(client.get_executions())

    print()
    print("TRADES")
    print(client.get_trades())

    print()
    print("ORDER HISTORY")
    print(client.get_order_history())

    print()
    print("FUNDING HISTORY")
    print(client.get_funding_history())

    print()
    print("PNL HISTORY")
    print(client.get_pnl_history())

    print()
    print("PORTFOLIO")
    print(client.get_portfolio())

    print()
    print("VOLUME")
    print(client.get_volume())

    print()
    print("MARKETS")
    print(client.get_markets())

    print()
    print("JUVENTUS")
    print(client.get_market("juventus"))

    print()
    print("ORDER BOOK")
    print(client.get_order_book(4))

    print()
    print("MARKET TRADES")
    print(client.get_market_trades(4))

except AntivistAPIError as exc:
    print("API ERROR")
    print("status_code:", exc.status_code)
    print("code:", exc.code)
    print("message:", exc.message)
    print("body:", exc.response_body) 