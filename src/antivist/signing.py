import hashlib
import hmac


def sha256_body(body: bytes) -> str:
    """
    Return the lowercase SHA256 hex digest of the raw request body bytes.
    """
    return hashlib.sha256(body).hexdigest()


def build_canonical_request(
    method: str,
    path: str,
    query_string: str,
    timestamp: str,
    nonce: str,
    body_sha256: str,
) -> str:
    """
    Build the exact canonical request expected by Antivist authentication.
    """
    return "\n".join(
        [
            method.upper(),
            path,
            query_string,
            timestamp,
            nonce,
            body_sha256,
        ]
    )


def sign_request(
    api_secret: str,
    canonical_request: str,
) -> str:
    """
    Sign the canonical request using HMAC-SHA256.

    The API secret is used directly as the HMAC key.
    """
    return hmac.new(
        api_secret.encode("utf-8"),
        canonical_request.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
