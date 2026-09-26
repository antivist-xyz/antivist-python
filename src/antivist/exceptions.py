class AntivistError(Exception):
    """
    Base exception for all Antivist SDK errors.
    """


class AntivistAPIError(AntivistError):
    """
    Raised when the Antivist API returns a non-successful HTTP response.
    """

    def __init__(
        self,
        *,
        status_code: int,
        code: str | None = None,
        message: str | None = None,
        response_body=None,
    ):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.response_body = response_body

        error_message = f"Antivist API error ({status_code})"

        if code:
            error_message += f" [{code}]"

        if message:
            error_message += f": {message}"

        super().__init__(error_message)
