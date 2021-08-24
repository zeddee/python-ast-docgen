import ast
from typing import Optional, List, Any, Dict, Union

def load_ast_from_file(filename: str) -> ast.AST:
    with open(filename, "r") as f:
        contents = f.read()
        # Danger! Running ``exec()`` because
        # there is no way to reliably
        # install and load the platform-backend repo
        # as a dependency.
        ast_tree = ast.parse(contents)
        f.close()

    return ast_tree


def walk_ast_children(node: ast.AST) -> Optional[List]:
    out = list()
    out.append(node.__dict__)

    if ast.iter_child_nodes(node) == []:
        return None

    for i in ast.iter_child_nodes(node):
        out.append(walk_ast_children(i))

    return out

def get_name_str(node: ast.AST) -> str:
    if not isinstance(node, ast.Name):
        return None

    return node.id


def parse_primitive(node: ast.AST) -> Union[str, int]:
    """
    Parse primitive nodes and return their values.

    If not an expected primitive, then
    just return the ast.dump.
    """
    if isinstance(node, ast.Str):
        return node.s

    if isinstance(node, ast.Num):
        return node.n


def parse_func_args(node: ast.AST) -> Dict[str, Any]:
    assert(isinstance(node, ast.arguments)), f"{node} is not an ast.arguments node"

    def parse_arglist(
        arglist: Union[ast.arg, List[ast.arg]],
        arg_type: str) -> List[Dict[str,Any]]:

        if not arglist:
            # Check if node is empty first
            return []
        
        args = []

        if isinstance(arglist, ast.arg):
            # if dealing with vararg and kwarg,
            # we expect only a single ast.arg

            return [{
                "type": arg_type,
                "name": arglist.arg,
                "arg_type": \
                    parse_ast(arglist.annotation) \
                    if arglist.annotation else None,
            }]

        for i in arglist:
            this_arg = {
                "type": arg_type,
                "name": i.arg,
                "arg_type": \
                    parse_ast(i.annotation) \
                    if i.annotation else None,
            }
            args.append(this_arg)

        return args


    return {
      "args": parse_arglist(node.args, "ARG"),
      "vararg": parse_arglist(node.vararg, "VARARG"),
      "kwonlyargs": parse_arglist(node.kwonlyargs, "KWONLYARG"),
      "kw_defaults": ast.dump(node.kw_defaults) if node.kw_defaults else None,
      "kwarg": parse_arglist(node.kwarg, "KWARG"),
      "defaults": [ast.dump(i) for i in node.defaults],
    }


def parse_ast(ast_tree: ast.AST) -> List[Dict[str, Any]]:
    out = list()

    for node in ast.iter_child_nodes(ast_tree):

        if isinstance(node, ast.Assign):

            this_name = []

            for target in node.targets:
                # Handle how key/value names are
                # found in ast.Assign.targets[]
                if isinstance(target, ast.Name):
                    this_name.append(target.id)

                if isinstance(target, ast.Tuple):
                    for el in target.elts:
                        this_name.append(ast.dump(el))

            this_node = {
              "type": "ASSIGN",
              "name": this_name,
              "value": parse_primitive(node.value),
              }
            
            out.append(this_node)

        if isinstance(node, ast.AnnAssign):

            this_name = node.target.id

            # AnnAssign are assignments with type annotations.
            # We can process these to add type
            # information for the values assigned.
            if isinstance(node.annotation, ast.Subscript):
                this_type = node.annotation.value.id

            out.append(
              {
                  "type": "ANNASSIGN",
                  "name": [this_name],
                  "value": parse_primitive(node.value),
                  "assign_type": this_type,
              }
            )


        if isinstance(node, ast.Attribute):
            this_node = {
                "type": "ATTRIBUTE",
                "name": node.body.value.id,
                "attr": node.body.attr,
            }
            pass

        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            this_node = {
                "type": "FUNCTION",
                "name": node.name,
                "args": parse_func_args(node.args),
                "body": parse_ast(node),
                "decorator_list": parse_ast(node),
                "doc": ast.get_docstring(node),
            }
            out.append(this_node)

        if isinstance(node, ast.ClassDef):
            this_node = {
                "type": "CLASS",
                "name": node.name,
                "body": parse_ast(node),
                "doc": ast.get_docstring(node),
            }
            out.append(this_node)

        if isinstance(node, ast.Tuple):
            this_node = list()
            for el in node.elts:
                out.append(el.id)
            out.append(this_node)

    return out
