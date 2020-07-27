"""Functionality to generate and work with the directory structure of a project

.. versionchanged:: 4.0
   ``Callable[[dict], str]`` and :obj:`string.Template` objects can also be used as file
   contents. They will be called with PyScaffold's ``opts`` (:obj:`string.Template` via
   :obj:`~string.Template.safe_substitute`)
"""

from pathlib import Path
from string import Template
from typing import Callable, Dict, Tuple, Union

from . import templates
from .file_system import create_directory
from .operations import (
    FileContents,
    FileOp,
    ScaffoldOpts,
    create,
    no_overwrite,
    skip_on_update,
)
from .templates import get_template

NO_OVERWRITE = no_overwrite()
SKIP_ON_UPDATE = skip_on_update()


AbstractContent = Union[FileContents, Callable[..., FileContents], Template]
StructureLeaf = Tuple[AbstractContent, FileOp]

# TODO: replace `dict` when recursive types are processed by mypy
Structure = Dict[str, Union[StructureLeaf, dict]]
"""Dictionary representation of the project structure with string keys representing
file/dir names.

In this representation a nested dictionary represent a nested directory, while
:obj:`str`, :obj:`string.Template` and :obj:`callable` values represent a file to be
created. :obj:`tuple` values are also allowed, and in that case, the first element of
the tuple represents the file content while the second element is a
:mod:`pyscaffold.operations <file operation>` (which can be seen as a recipe on how to
create a file with the given content).  :obj:`callable <Callable>` file contents are
transformed into strings by calling them with :obj:`PyScaffold's option dict as argument
<pyscaffold.api.create_structure>`. Similarly, :obj:`string.Template.safe_substitute`
are called with PyScaffold's opts.  :obj:`None` file contents are ignored and not
created in disk.

The top level keys in the dict are file/dir names relative to the project root, while
keys in nested dicts are relative to the parent's key/location.
"""


def define_structure(_, opts):
    """Creates the project structure as dictionary of dictionaries

    Args:
        _ (dict): previous directory structure (ignored)
        opts (dict): options of the project

    Returns:
        tuple(dict, dict):
            structure as dictionary of dictionaries and input options

    .. versionchanged:: 4.0
       :obj:`string.Template` and functions added directly to the file structure.
    """
    struct = {
        ".gitignore": (get_template("gitignore"), NO_OVERWRITE),
        "src": {
            opts["package"]: {
                "__init__.py": templates.init,
                "skeleton.py": (get_template("skeleton"), SKIP_ON_UPDATE),
            }
        },
        "tests": {
            "conftest.py": (get_template("conftest_py"), NO_OVERWRITE),
            "test_skeleton.py": (get_template("test_skeleton"), SKIP_ON_UPDATE),
        },
        "docs": {
            "conf.py": get_template("sphinx_conf"),
            "authors.rst": get_template("sphinx_authors"),
            "index.rst": (get_template("sphinx_index"), NO_OVERWRITE),
            "license.rst": get_template("sphinx_license"),
            "changelog.rst": get_template("sphinx_changelog"),
            "Makefile": get_template("sphinx_makefile"),
            "_static": {".gitignore": get_template("gitignore_empty")},
        },
        "README.rst": (get_template("readme"), NO_OVERWRITE),
        "AUTHORS.rst": (get_template("authors"), NO_OVERWRITE),
        "LICENSE.txt": (templates.license, NO_OVERWRITE),
        "CHANGELOG.rst": (get_template("changelog"), NO_OVERWRITE),
        "setup.py": get_template("setup_py"),
        "setup.cfg": (templates.setup_cfg, NO_OVERWRITE),
        ".coveragerc": (get_template("coveragerc"), NO_OVERWRITE),
    }

    return struct, opts


def structure_leaf(contents: Union[AbstractContent, StructureLeaf]) -> StructureLeaf:
    """Normalize project structure leaf to be a Tuple[AbstractContent, FileOp]"""
    if isinstance(contents, tuple):
        return contents
    return (contents, create)


def reify_content(content: AbstractContent, opts: ScaffoldOpts) -> FileContents:
    """Make content string (via __call__ or safe_substitute with opts if necessary)"""
    if callable(content):
        return content(opts)
    if isinstance(content, Template):
        return content.safe_substitute(opts)
    return content


def create_structure(struct, opts, prefix=None):
    """Manifests/reifies a directory structure in the filesystem

    Args:
        struct (dict): directory structure as dictionary of dictionaries
        opts (dict): options of the project
        prefix (pathlib.PurePath): prefix path for the structure

    Returns:
        tuple(dict, dict):
            directory structure as dictionary of dictionaries (similar to
            input, but only containing the files that actually changed) and
            input options

    Raises:
        TypeError: raised if content type in struct is unknown

    .. versionchanged:: 4.0
       Also accepts :obj:`string.Template` and :obj:`callable` objects as file contents.
    """
    update = opts.get("update") or opts.get("force")
    pretend = opts.get("pretend")

    if prefix is None:
        prefix = opts.get("project_path", ".")
        create_directory(prefix, update, pretend)
    prefix = Path(prefix)

    changed = {}

    for name, node in struct.items():
        path = prefix / name
        if isinstance(node, dict):
            create_directory(path, update, pretend)
            changed[name], _ = create_structure(node, opts, prefix=path)
        else:
            template, file_op = structure_leaf(node)
            content = reify_content(template, opts)
            if file_op(path, content, opts):
                changed[name] = content

    return changed, opts
