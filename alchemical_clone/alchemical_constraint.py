import typing

from sqlalchemy import (CheckConstraint, Constraint, ForeignKeyConstraint,
                        PrimaryKeyConstraint, UniqueConstraint)

from .utils import quoted_string

if typing.TYPE_CHECKING:
    from .alchemical_column import AlchemicalColumn
    from .alchemical_table import AlchemicalTable


class AlchemicalConstraint:
    """An intermediate representation of a SQLAlchemy constraint."""
    def __init__(self, constraint: Constraint, table: "AlchemicalTable"):
        if not isinstance(constraint, (CheckConstraint, ForeignKeyConstraint, PrimaryKeyConstraint, UniqueConstraint)):
            raise NotImplementedError(f"Unsupported constraint type: {constraint.__class__.__name__}")
        
        self._constraint = constraint
        self._table = table

        self.name: str = constraint.name
        self.type: str = None
        self.columns: typing.List["AlchemicalColumn"] = None
        self.referenced_columns: typing.Optional[typing.List["AlchemicalColumn"]] = None
        self.ondelete: typing.Optional[str] = None
        self.onupdate: typing.Optional[str] = None
        self.relationship_to: typing.Optional["AlchemicalColumn"] = None
        
    def __repr__(self) -> str:
        return f"<AlchemicalConstraint {self.type} {quoted_string(self.name)}>"

    def compute_properties(self):
        self.columns = []
        if isinstance(self._constraint, ForeignKeyConstraint):
            self.columns = [self._table.column_from_name(column) for column in self._constraint.column_keys]
        else:
            self.columns = [self._table.column_from_name(column.name) for column in self._constraint.columns]
        self.type = self._constraint.__class__.__name__

        if isinstance(self._constraint, ForeignKeyConstraint):
            fk = next(iter(self._constraint.elements))
            self.referred_table = self._table.parent.table_from_name(fk.column.table.name)
            self.referenced_columns = [self.referred_table.column_from_name(element.column.name) for element in self._constraint.elements]
            if len(self.columns) == 1 and len(self.referenced_columns) == 1:
                self.relationship_to = self.referenced_columns[0]
        
        self.ondelete = quoted_string(self._constraint.ondelete) if hasattr(self._constraint, "ondelete") and self._constraint.ondelete is not None else None
        self.onupdate = quoted_string(self._constraint.onupdate) if hasattr(self._constraint, "onupdate") and self._constraint.onupdate is not None else None

    def codegen(self) -> str:
        """Generate SQLAlchemy ORM code for this constraint."""
        constraint_type = self._constraint.__class__.__name__

        optional_attrs = {}

        if len(self._constraint.columns) == 0 and not isinstance(self._constraint, CheckConstraint):
            return None
        
        if self.name is not None:
            optional_attrs["name"] = quoted_string(self.name)
        if self.ondelete is not None:
            optional_attrs["ondelete"] = self.ondelete
        if self.onupdate is not None:
            optional_attrs["onupdate"] = self.onupdate

        if isinstance(self._constraint, ForeignKeyConstraint):
            constraint_inner_code = f"[{', '.join([quoted_string(column.name) for column in self.columns])}]"
        elif isinstance(self._constraint, CheckConstraint):
            constraint_inner_code = quoted_string(self._constraint.sqltext.text)
        else:
            constraint_inner_code = f"{', '.join([quoted_string(column.name) for column in self.columns])}"
        
        code = f"{constraint_type}({constraint_inner_code}"

        if isinstance(self._constraint, ForeignKeyConstraint):
            code += f", [{', '.join([quoted_string(column.target_name) for column in self.referenced_columns])}]"

        for attr, value in optional_attrs.items():
            code += f", {attr}={value}"
        code += ")"

        return code
    
    def codegen_relationship(self) -> str:
        if self.has_relationship:
            return f"{self.name} = relationship({quoted_string(self.referred_table.class_name)}, foreign_keys=[{', '.join([column.name for column in self.columns])}])"
        return None

    @property
    def has_relationship(self) -> bool:
        return isinstance(self._constraint, ForeignKeyConstraint) and len(self.columns) == 1
