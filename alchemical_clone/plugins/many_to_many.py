import typing

from ..alchemical_lab import PluginImport, PluginResult
from ..generated_code import GeneratedCode
from ..utils import quoted_string

if typing.TYPE_CHECKING:
    from ..alchemical_lab import AlchemicalLab, PluginImports


def many_to_many(lab: "AlchemicalLab") -> "PluginResult":
    imports: "PluginImports" = {}
    code: typing.Dict[str, typing.List[GeneratedCode]] = {}

    for table in lab.tables:
        foreign_key_constraints = tuple(filter(lambda c: c.type == "ForeignKeyConstraint", table.constraints))
        if len(foreign_key_constraints) == 2:
            referred_table1, referred_table2 = foreign_key_constraints[0].referred_table, foreign_key_constraints[1].referred_table

            if referred_table1 == table or referred_table2 == table:
                continue

            if not table.will_generate():
                    continue

            plugin_imports = [
                PluginImport("sqlalchemy.orm", {"relationship"}),
                PluginImport(f".{table.name}", {table.class_name})
            ]

            t1_mtm_name = f"{referred_table2.name}_through_{table.name}"
            t2_mtm_name = f"{referred_table1.name}_through_{table.name}"

            table1_code = [
                f"{t1_mtm_name} = relationship({quoted_string(referred_table2.class_name)}, secondary={table.class_name}.__table__, back_populates={quoted_string(t2_mtm_name)}, viewonly=True)"
            ]
            
            table2_code = [
                f"{t2_mtm_name} = relationship({quoted_string(referred_table1.class_name)}, secondary={table.class_name}.__table__, back_populates={quoted_string(t1_mtm_name)}, viewonly=True)"
            ]

            imports.setdefault(referred_table1.name, []).extend(plugin_imports) 
            imports.setdefault(referred_table2.name, []).extend(plugin_imports) 

            code.setdefault(referred_table1.name, []).extend([GeneratedCode(c, "table") for c in table1_code])
            code.setdefault(referred_table2.name, []).extend([GeneratedCode(c, "table") for c in table2_code])

    return PluginResult(imports=imports, code=code)