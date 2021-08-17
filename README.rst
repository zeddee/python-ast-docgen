Generate documentation from Python AST
****************************************

..  WARNING::

    Experimental package. Certain ast.AST node types
    remain unimplemented. Use at your own risk.

The ``astparser`` python module parses
individual python files and generates
JSON representing the AST tree
of the parsed python file.

Useful when you need to:

- document a list of attribute names and their expected
  values.
- document a specific python file without having to import
  or install its dependency tree.

Usage
========

``astparser.parse_ast`` returns a python dict
that you can iterate over and extract
information from.

Run ``python astparser`` to parse a file (hardcoded path for
now) and dump the resulting dict as JSON to stdout.
