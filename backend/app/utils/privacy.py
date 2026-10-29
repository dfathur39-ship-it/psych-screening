def mask_nik(nik: str | None) -> str | None:
    """Mask NIK for display: show first 4 digits only, rest as asterisks.
    Example: 3273123456789012 -> 3273************
    """
    if not nik:
        return None
    if len(nik) <= 4:
        return "*" * len(nik)
    return nik[:4] + "*" * (len(nik) - 4)


def redact_for_log(value: str | None, keep: int = 0) -> str:
    """Never log full sensitive values. Use this wrapper wherever NIK/secret might
    end up in a log line or error message."""
    if not value:
        return ""
    return "[REDACTED]"
