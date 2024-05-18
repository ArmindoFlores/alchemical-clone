import typing

from ..alchemical_lab import PluginResult

if typing.TYPE_CHECKING:
    from ..alchemical_lab import AlchemicalLab


def many_to_many(lab: "AlchemicalLab") -> "PluginResult":
    for table in lab.tables:
        foreign_key_constraints = tuple(filter(lambda c: c.type == "ForeignKeyConstraint", table.constraints))
        if len(foreign_key_constraints) == 2:
            print(f"Many-to-many relationship detected between {table.name} and {foreign_key_constraints[0].referred_table.name}")
    return PluginResult(imports={}, code={})