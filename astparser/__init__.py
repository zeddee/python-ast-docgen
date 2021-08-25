import ast
from astunparse import unparse #: polyfill for pre-3.9
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


def parse_literal(node: ast.AST) -> \
    Union[str, int, Dict[Any, Any], List[Any]]:
    """
    Parse primitive nodes and return their values.

    If not an expected primitive, then
    just return the ast.dump.
    """
    if isinstance(node, ast.Name):
        # ast.Name are technically strings
        # So treat as literal
        return node.id

    if isinstance(node, ast.Str):
        return node.s

    if isinstance(node, ast.Num):
        return node.n

    if isinstance(node, ast.Dict):
        out = {}
        zipped = zip(node.keys, node.values)
        for i in zipped:
            out[parse_literal(i[0])] = parse_literal(i[1])
        return out

    if isinstance(node, (ast.Tuple, ast.List)):
        return \
            [parse_literal(i) for i in node.elts]

    if isinstance(node, (ast.BinOp, ast.BoolOp)):
        return parse_op(node)

    if isinstance(node, ast.Call):
        return unparse(node)

    else:
        return unparse(node)


def parse_op(node: ast.AST) -> str:
    """
    Parse an operation e.g. 1 * 2

    Returns:
        String, because we don't want to handle
        the complexity of calculating an op.
    """
    assert(isinstance(node, (ast.BinOp, ast.BoolOp, ast.operator))), \
        f"Unexpected: {node} is not ast.operator"

    OPS = {
            ast.Add: '+',
            ast.Sub: '-',
            ast.Mult: '*',
            ast.Div: '/',
            ast.FloorDiv: '//',
            ast.Mod: '%',
            ast.Pow: '**',
            ast.LShift: '<<',
            ast.RShift: '>>',
            ast.BitOr: '|',
            ast.BitXor: '^',
            ast.BitAnd: '&',
            ast.MatMult: '@',
            ast.Or: "or",
            ast.And: "and",
        }

    if isinstance(node, ast.BinOp):
        return " ".join([
          str(parse_literal(node.left)),
          parse_op(node.op),
          str(parse_literal(node.right)),
        ])


    if isinstance(node, ast.BoolOp):
        op = ast.dump(node.op)
        return f" {op} ".join(
          [str(parse_literal(i)) for i in node.values],
        )

    else:
        for op, val in OPS.items():
            if isinstance(node, op):
                return val


def parse_func_args(node: ast.AST) -> Dict[str, Any]:
    assert(isinstance(node, ast.arguments)),\
        f"{node} is not an ast.arguments node"

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
                    parse_literal(arglist.annotation) \
                    if arglist.annotation else None,
            }]

        for i in arglist:
            this_arg = {
                "type": arg_type,
                "name": i.arg,
                "arg_type": \
                    parse_literal(i.annotation) \
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
                this_name.append(parse_literal(target))

            this_node = {
              "type": "ASSIGN",
              "name": this_name,
              "value": parse_literal(node.value),
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
                "value": parse_literal(node.value),
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

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            this_node = {
              "type": "FUNCTION",
              "name": node.name,
              "args": parse_func_args(node.args),
              "body": parse_ast(node),
              "decorator_list": parse_ast(node),
              "doc": ast.get_docstring(node, clean=True),
            }
            out.append(this_node)

        if isinstance(node, ast.ClassDef):
            this_node = {
                "type": "CLASS",
                "name": node.name,
                "body": parse_ast(node),
                "doc": ast.get_docstring(node, clean=True),
            }
            out.append(this_node)

        else:
            this_node = {
              "type": str(type(node)),
              "name": "",
              "body": ast.dump(node),
            }

    return out
