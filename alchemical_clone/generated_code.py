import dataclasses
import typing


CodeLocation = typing.Literal["table", "end"]

@dataclasses.dataclass
class GeneratedCode:
    code: str
    location: CodeLocation
