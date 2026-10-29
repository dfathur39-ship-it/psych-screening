from fastapi import HTTPException, status


class ApiError(HTTPException):
    def __init__(self, status_code: int, message: str, error_code: str):
        super().__init__(status_code=status_code, detail={
            "success": False,
            "message": message,
            "error_code": error_code,
        })


def not_found(message: str, code: str) -> ApiError:
    return ApiError(status.HTTP_404_NOT_FOUND, message, code)


def bad_request(message: str, code: str) -> ApiError:
    return ApiError(status.HTTP_400_BAD_REQUEST, message, code)


def conflict(message: str, code: str) -> ApiError:
    return ApiError(status.HTTP_409_CONFLICT, message, code)


def unauthorized(message: str, code: str = "UNAUTHORIZED") -> ApiError:
    return ApiError(status.HTTP_401_UNAUTHORIZED, message, code)


def forbidden(message: str, code: str = "FORBIDDEN") -> ApiError:
    return ApiError(status.HTTP_403_FORBIDDEN, message, code)
