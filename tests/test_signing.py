import hashlib
import hmac

from antivist.signing import (
    build_canonical_request,
    sha256_body,
    sign_request,
)


def test_sha256_body():
    body = b'{"market_id":1,"side":"BUY"}'

    expected = hashlib.sha256(body).hexdigest()

    assert sha256_body(body) == expected


def test_build_canonical_request():
    body = b'{"market_id":1,"side":"BUY"}'
    body_sha256 = hashlib.sha256(body).hexdigest()

    canonical_request = build_canonical_request(
        method="post",
        path="/api/match-engine/orders/",
        query_string="",
        timestamp="1787150000000",
        nonce="550e8400-e29b-41d4-a716-446655440000",
        body_sha256=body_sha256,
    )

    expected = "\n".join(
        [
            "POST",
            "/api/match-engine/orders/",
            "",
            "1787150000000",
            "550e8400-e29b-41d4-a716-446655440000",
            body_sha256,
        ]
    )

    assert canonical_request == expected


def test_sign_request():
    api_secret = "test-secret"

    canonical_request = "\n".join(
        [
            "POST",
            "/api/match-engine/orders/",
            "",
            "1787150000000",
            "550e8400-e29b-41d4-a716-446655440000",
            "abc123",
        ]
    )

    expected = hmac.new(
        api_secret.encode("utf-8"),
        canonical_request.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    assert sign_request(api_secret, canonical_request) == expected


def test_signing_matches_antivist_protocol_test_vector():
    api_secret = "test-secret"
    body = b'{"market_id":1,"side":"BUY"}'

    body_sha256 = sha256_body(body)

    assert (
        body_sha256
        == "1083fdc285bdc191b41eab6e6396adcf32f86bcf7cbd56ea66926a38e69f1d52"
    )

    canonical_request = build_canonical_request(
        method="POST",
        path="/api/match-engine/orders/",
        query_string="",
        timestamp="1787150000000",
        nonce="550e8400-e29b-41d4-a716-446655440000",
        body_sha256=body_sha256,
    )

    expected_canonical_request = (
        "POST\n"
        "/api/match-engine/orders/\n"
        "\n"
        "1787150000000\n"
        "550e8400-e29b-41d4-a716-446655440000\n"
        "1083fdc285bdc191b41eab6e6396adcf32f86bcf7cbd56ea66926a38e69f1d52"
    )

    assert canonical_request == expected_canonical_request

    signature = sign_request(
        api_secret=api_secret,
        canonical_request=canonical_request,
    )

    assert (
        signature
        == "9155b6ff3becb5426c486e7f61f7703cb35360ae93f95a46721df674f1dce208"
    )