from typing import Literal, Mapping
import platform

type OS = Literal["linux", "macos", "windows", "*"]

_system = platform.system()
_OS_map: dict[str, OS] = {
    "Linux": "linux",
    "Darwin": "macos",
    "Windows": "windows",
}
os: OS = _OS_map.get(_system, "linux")


def get_os_matrix(matrix: Mapping[OS, str]) -> str | None:
    """Get a value from a mapping where the key is an OS, falling back to a wildcard ("*").

    Args:
        matrix: A mapping where an OS literal is the key.

    Returns:
        The value, if one is found, or `None`.
    """
    if (result := matrix.get(os)) is None:
        result = matrix.get("*")
    return result
