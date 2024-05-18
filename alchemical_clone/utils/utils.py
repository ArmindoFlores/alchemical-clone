__all__ = ["pascal_case"]

import re
import typing
from urllib.parse import quote


def quoted_string(input_str):
    contains_double_quote = '"' in input_str
    contains_newline = '\n' in input_str

    if not contains_double_quote and not contains_newline:
        return f'"{input_str}"'
    else:
        return f'"""{input_str}"""'
    
def pascal_case(string: str) -> str:
    """Convert a string to PascalCase."""

    return re.sub(r"(_|-)+", " ", string).title().replace(" ", "")

def get_engine_url(
        dialect: str, 
        username: str, 
        password: str, 
        host: str,
        port: int = 10121,
        service_name: typing.Optional[str] = None,
        driver: typing.Optional[str] = None
    ) -> str:
    """Generate a SQLAlchemy engine URL from connection parameters."""

    engine_url = dialect
    if driver:
        engine_url += "+" + driver
    engine_url += f"://{quote(username)}:{quote(password)}@{host}:{port}"

    url_params = []
    if service_name:
        url_params.append(f"service_name={service_name}")
    if len(url_params) > 0:
        engine_url += "/?" + "&".join(url_params)

    return engine_url
