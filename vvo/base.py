import requests as _requests
import re as _re
from datetime import datetime
from logging import getLogger as _getLogger

_BASE_URL = "https://webapi.vvo-online.de/"

logger = _getLogger()


class Response:
    def __init__(self, data, parameters):
        if not isinstance(data, dict):
            raise ValueError
        self.status = data["Status"]["Code"] == "Ok"
        self.ok = self.status


def _do_request(endpoint: str, data: dict = None, cls=Response):
    if not issubclass(cls, Response):
        raise ValueError("Class must be derived from Response class")

    r = _requests.post(f"{_BASE_URL}{endpoint}", json=data)
    if r.status_code != 200:
        logger.debug(f"Request to {endpoint} failed with status code {r.status_code}")
        try:
            status = r.json()["Status"]
            raise RuntimeError(f"{status['Code']}: {status['Message']}")
        except (_requests.exceptions.JSONDecodeError, KeyError):
            pass
        raise RuntimeError

    return cls(r.json(), data)


def _parse_time(time: str):
    """Parse time string to datetime"""

    pattern = _re.compile(r"Date\((\d+)+?([-]\d{4})\)")
    res = pattern.search(time)
    if not res:
        raise ValueError("Invalid date string given")

    ts, tz = res.group(1, 2)
    return datetime.fromtimestamp(int(ts) / 1000 + int(tz) * 60)
