# antivist-python

Official synchronous Python SDK for the Antivist Markets Public REST API.

## Conditional exits (TP/SL)

Conditional exits are created against an existing parent order:

```python
tp_sl = client.create_conditional_exits(
    parent_order_id=order.id,
    take_profit="1100.00",
    stop_loss="950.00",
)
```

List active conditional exits:

```python
active_exits = client.list_conditional_exits(
    status="ACTIVE",
)
```

Cancel one conditional exit:

```python
client.cancel_conditional_exit(
    conditional_exit_id=tp_sl[0].id,
)
```

The SDK only submits and reads conditional-exit resources. Trigger evaluation is
performed server-side using Mark Price. Triggered exits are reduce-only MARKET
orders, OCO behavior is handled by the backend, and the effective exit quantity
is determined server-side from the parent order's filled quantity and the
currently reducible position.

`requested_quantity` describes the quantity requested by the server-managed
exit lifecycle; it does not guarantee that the full quantity will ultimately be
executed.
