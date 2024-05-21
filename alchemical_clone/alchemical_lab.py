import dataclasses
import os
import typing

from sqlalchemy import MetaData

from .alchemical_table import AlchemicalTable
from .generated_code import GeneratedCode
from .utils import pascal_case

_BASE_FILE_CODE = """\
__all__ = ["Base"]

from sqlalchemy.orm import declarative_base


Base = declarative_base()
"""


@dataclasses.dataclass
class PluginImport:
    package: str
    modules: typing.Set[str]

PluginImports = typing.Dict[str, typing.List[PluginImport]]

PluginResult = typing.NamedTuple(
    "PluginResult", 
    [("imports", PluginImports), ("code", typing.Dict[str, typing.List[GeneratedCode]])], 
)
Plugin = typing.Callable[["AlchemicalLab"], PluginResult]

class AlchemicalLab:
    def __init__(self, metadata: MetaData):
        self._metadata = metadata
        self.tables = [AlchemicalTable(table, self) for table in metadata.sorted_tables]
        for table in self.tables:
            table.compute_properties()

    def create_clone(self, directory: typing.Union[str, bytes, os.PathLike], plugins: typing.Optional[typing.List[Plugin]] = None):
        """Generate a package with SQLAlchemy ORM classes for the given metadata."""

        plugin_code: typing.Dict[str, typing.List[GeneratedCode]] = {}
        plugin_imports: typing.Dict[str, typing.Dict[str, typing.List[str]]] = {}
        for plugin in plugins or []:
            result = plugin(self)
            for table_name, code in result.code.items():
                plugin_code.setdefault(table_name, []).extend(code)
            for table, import_list in result.imports.items():
                plugin_imports.setdefault(table, {})
                for import_item in import_list:
                    plugin_imports[table].setdefault(import_item.package, set()).update(import_item.modules)

        os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, "_base.py"), "w") as f:
            f.write(_BASE_FILE_CODE)

        generated_tables = []
        for table in self.tables:
            try:
                code = table.codegen()
            except NotImplementedError as e:
                print(f"Error generating table {table.name}: {e}")
                continue
            
            with open(os.path.join(directory, f"{table.name}.py"), "w") as f:
                imports = table.imports
                table_plugin_imports = plugin_imports.get(table.name, {})
                for package, modules in table_plugin_imports.items():
                    imports.setdefault(package, set()).update(modules)

                import_packages = sorted([key.split(".") for key in imports.keys()])
                for package in import_packages:
                    package_name = ".".join(package)
                    modules = sorted(imports[package_name])
                    if len(modules) > 0:
                        f.write(f"from {package_name} import {', '.join(modules)}\n")
                f.write("\n")
                f.write("from ._base import Base\n\n\n")
                f.write(code["table"])

                for segment in plugin_code.get(table.name, []):
                    if segment.location == "table":
                        f.write("    " + segment.code + "\n")

                f.write("\n")
                f.write(code["end"])

                for segment in plugin_code.get(table.name, []):
                    if segment.location == "end":
                        f.write(segment.code + "\n")
            
            generated_tables.append(table)

        with open(os.path.join(directory, "__init__.py"), "w") as f:
            f.write("__all__ = [\n")
            f.write("""    "_base",\n""")
            for table in generated_tables:
                class_name = pascal_case(table.name)
                f.write(f"""    "{class_name}",\n""")
            f.write("]\n\n")
            f.write(f"from . import _base\n")
            for table in generated_tables:
                class_name = pascal_case(table.name)
                f.write(f"from .{table.name} import {class_name}\n")
    
    def table_from_name(self, name: str) -> typing.Optional[AlchemicalTable]:
        return next((table for table in self.tables if table.name == name), None)
