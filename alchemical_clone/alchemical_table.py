import typing

from sqlalchemy import Table

from .alchemical_column import AlchemicalColumn
from .alchemical_constraint import AlchemicalConstraint
from .alchemical_index import AlchemicalIndex
from .generated_code import CodeLocation
from .utils import pascal_case, quoted_string

if typing.TYPE_CHECKING:
    from .alchemical_lab import AlchemicalLab


class Relationship(typing.NamedTuple):
    from_: AlchemicalColumn
    to: AlchemicalColumn

class AlchemicalTable:
    """An intermediate representation of a SQLAlchemy table."""
    def __init__(self, table: Table, parent: "AlchemicalLab"):
        self._table = table
        self.parent = parent

        self.name: str = table.name
        self.class_name: str = None
        self.schema: typing.Optional[str] = None
        self.comment: typing.Optional[str] = None
        self.columns: typing.List[AlchemicalColumn] = None
        self.constraints: typing.List[AlchemicalConstraint] = None
        self.indexes: typing.List[AlchemicalIndex] = None
        self.relationships: typing.List[Relationship] = []
    
    def __repr__(self) -> str:
        return f"<AlchemicalTable {quoted_string(self.name)}>"
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, AlchemicalTable):
            return False
        return self.name == other.name
    
    def __hash__(self) -> int:
        return hash(self.name)

    def compute_properties(self):
        self.class_name = pascal_case(self.name)
        self.comment = quoted_string(self._table.comment) if self._table.comment is not None else None
        self.schema = self._table.schema if self._table.schema is not None else None

        self.columns = [AlchemicalColumn(column, self) for column in self._table.columns]
        for column in self.columns:
            column.compute_properties()

        self.constraints = [AlchemicalConstraint(constraint, self) for constraint in self._table.constraints]

        relationships = set()
        for constraint in self.constraints:
            constraint.compute_properties()
            if constraint.relationship_to is not None:
                new_relationsip = (constraint.referred_table.class_name, constraint.relationship_to)
                if new_relationsip not in relationships:
                    relationships.add(new_relationsip)
                    self.relationships.append(Relationship(constraint.columns[0], constraint.relationship_to.fullname))

        self.indexes = [AlchemicalIndex(index, self) for index in self._table.indexes]
        for index in self.indexes:
            index.compute_properties()

    @property
    def imports(self) -> typing.Dict[str, typing.Set[str]]:
        base_types = {"Column"}
        if len(self.indexes) > 0:
            base_types.add("Index")
        column_types = {column.type_name for column in self.columns}
        constraint_types = {constraint.type for constraint in self.constraints}
        orm_imports = set()
        for constraint in self.constraints:
            if constraint.has_relationship:
                orm_imports.add("relationship")
                break
        return { 
            "sqlalchemy": base_types.union(column_types.union(constraint_types)), 
            "sqlalchemy.orm": orm_imports 
        }

    def will_generate(self) -> bool:
        """Check if this table will generate any code."""
        
        for column in self.columns:
            if column.implicit_primary_key or column.valid_primary_key:
                return True
        return False

    def codegen(self) -> typing.Dict[CodeLocation, str]:
        """Generate SQLAlchemy ORM code for this table."""

        class_code = ""
        after_class_code = ""

        class_code =  f"class {self.class_name}(Base):\n"
        class_code += f"    __tablename__ = {quoted_string(self.name)}\n"

        table_args = {}
        if self._table.comment is not None:
            table_args["comment"] = self.comment
        if self._table.schema is not None:
            table_args["schema"] = quoted_string(self._table.schema)

        relationships = []
        relationship_tracker = set()
        has_primary_key = False

        # Generate table arguments and constraints, if any
        if len(table_args) + len(self.constraints) > 0:
            class_code += "    __table_args__ = (\n"

            # Constraints come first
            if len(self.constraints) > 0:
                for constraint in self.constraints:
                    constraint_code = constraint.codegen()
                    if constraint_code is None:
                        continue

                    relationship_code = constraint.codegen_relationship()

                    if constraint.type == "PrimaryKeyConstraint":
                        has_primary_key = True

                    class_code += f"        {constraint_code},\n"
                    if relationship_code is not None:
                        relationship_identifier = (constraint.referred_table.class_name, constraint.relationship_to.fullname)
                        if relationship_identifier not in relationship_tracker:
                            relationship_tracker.add(relationship_identifier)
                            relationships.append(relationship_code)

            # Table arguments come next
            if len(table_args) > 0:
                class_code += "        {\n"
                for arg, value in table_args.items():
                    class_code += f"            {quoted_string(arg)}: {value},\n"
                class_code += "        },\n"

            class_code += "    )\n"
        class_code += "\n"

        # Generate columns
        found_primary_key = has_primary_key
        for column in self.columns:
            column_code = column.codegen(not has_primary_key)
            if column.implicit_primary_key:
                found_primary_key = True
            class_code += f"    {column_code}\n"
        if len(self.columns):
            class_code += "\n"

        if not found_primary_key:
            raise NotImplementedError(f"Table {self.name} does not have a primary key constraint, and no suitable combination of columns could be found.")
        
        # Generate relationships
        for relationship in relationships:
            class_code += f"    {relationship}\n"
        if len(relationships):
            class_code += "\n"

        # Generate indexes
        for index in self.indexes:
            after_class_code += f"{index.codegen()}\n"
        if len(self.indexes):
            after_class_code += "\n"

        return { "table": class_code, "end": after_class_code }

    def column_from_name(self, name: str) -> AlchemicalColumn:
        return next((column for column in self.columns if column.name == name), None)
