import typing

from ..alchemical_lab import PluginImport, PluginResult
from ..generated_code import GeneratedCode
from ..utils import quoted_string

if typing.TYPE_CHECKING:
    from ..alchemical_lab import AlchemicalLab, PluginImports


def one_to_many(lab: "AlchemicalLab") -> "PluginResult":
    imports: "PluginImports" = {}
    code: typing.Dict[str, typing.List[GeneratedCode]] = {}

    for table in lab.tables:
        constraints = tuple(filter(lambda c: c.type == "ForeignKeyConstraint", table.constraints))
        constraint_counts = {}

        for constraint in constraints:
            name = constraint.referred_table.name
            constraint_counts[name] = constraint_counts.get(name, 0) + 1

        valid_constraints = tuple(filter(lambda c: constraint_counts[c.referred_table.name] == 1, constraints))

        for constraint in valid_constraints:
            if len(constraint.referenced_columns) == 1 and len(constraint.columns) == 1:
                referred_table = constraint.referred_table
                if referred_table == table:
                    continue

                if not table.will_generate():
                    continue

                plugin_imports = [
                    PluginImport("sqlalchemy.orm", {"relationship"}),
                    PluginImport(f".{table.name}", {table.class_name})
                ]

                relationship_name = f"{referred_table.name}_to_{table.name}"

                relationship_code = [
                    f"{relationship_name} = relationship({quoted_string(table.class_name)}, back_populates={quoted_string(constraint.name)}, viewonly=True)"
                ]

                imports.setdefault(referred_table.name, []).extend(plugin_imports)
                code.setdefault(referred_table.name, []).extend([GeneratedCode(c, "table") for c in relationship_code])

    return PluginResult(imports=imports, code=code)
