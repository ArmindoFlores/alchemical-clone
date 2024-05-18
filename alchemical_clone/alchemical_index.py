import typing

from sqlalchemy import Column, Index

from .utils import quoted_string

if typing.TYPE_CHECKING:
    from .alchemical_column import AlchemicalColumn
    from .alchemical_table import AlchemicalTable


class AlchemicalIndex:
    """An intermediate representation of a SQLAlchemy index."""
    def __init__(self, index: Index, table: "AlchemicalTable"):
        self._index = index
        self._table = table

        self.name: str = index.name
        self.columns: typing.List["AlchemicalColumn"] = None
        self.unique: bool = None

    def __repr__(self) -> str:
        return f"<AlchemicalIndex {quoted_string(self.name)}>"
    
    def compute_properties(self):
        self.columns = [self._table.column_from_name(column.name) for column in self._index.columns]
        self.unique = self._index.unique

    def codegen(self) -> str:
        """Generate SQLAlchemy ORM code for this index."""
        for expression in self._index.expressions:
            if not isinstance(expression, Column):
                raise NotImplementedError("Only columns are supported in index expressions.")

        code = f"Index({quoted_string(self.name)}, {', '.join([column.class_property_name for column in self.columns])}, unique={self.unique})"
        return code