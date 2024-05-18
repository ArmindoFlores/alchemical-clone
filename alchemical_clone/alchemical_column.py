import typing

from sqlalchemy import Column

from .utils import quoted_string

if typing.TYPE_CHECKING:
    from .alchemical_table import AlchemicalTable


class AlchemicalColumn:
    """An intermidiate representation of a SQLAlchemy column."""
    def __init__(self, column: Column, table: "AlchemicalTable"):
        self._column = column
        self._table = table

        self.name: str = column.name
        self.implicit_primary_key: bool = None
        self.type: str = None
        self.nullable: bool = None
        self.comment: typing.Optional[str] = None
        self.server_default: typing.Optional[str] = None
        self.server_onupdate: typing.Optional[str] = None

    def __repr__(self) -> str:
        return f"<AlchemicalColumn {quoted_string(self.fullname)}>"
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, AlchemicalColumn):
            return False
        return self.fullname == other.fullname
    
    def __hash__(self) -> int:
        return hash(self.fullname)

    def compute_properties(self):
        self.implicit_primary_key = False
        self.type_name = self._column.type.as_generic().__class__.__name__
        self.type = repr(self._column.type.as_generic())
        self.nullable = self._column.nullable
        self.comment = quoted_string(self._column.comment) if self._column.comment is not None else None
        self.server_default = repr(self._column.server_default.arg.text) if self._column.server_default is not None else None
        self.server_onupdate = repr(self._column.server_onupdate.arg.text) if self._column.server_onupdate is not None else None

    def codegen(self, try_set_primary_key: bool = False) -> str:
        """Generate SQLAlchemy ORM code for this column."""

        if try_set_primary_key:
            if self._column.nullable is False:
                self.implicit_primary_key = True

        optional_attributes = {
            "primary_key": self.implicit_primary_key if self.implicit_primary_key else None,
            "comment": self.comment,
            "server_default": self.server_default,
            "server_onupdate": self.server_onupdate,
        }

        code = f"""{self.name} = Column({quoted_string(self.name)}, {self.type}, nullable={repr(self.nullable)}"""
        for attr, value in optional_attributes.items():
            if value is not None:
                code += f", {attr}={value}"
        code += ")"

        return code
    
    @property
    def target_name(self) -> str:
        name = ""
        if self._table.schema is not None:
            name += f"{self._table.schema}."
        name += f"{self._table.name}.{self.name}"
        return name
    
    @property
    def class_property_name(self) -> str:
        return f"{self._table.class_name}.{self.name}"
    
    @property
    def fullname(self) -> str:
        return f"{self._table.name}.{self.name}"
