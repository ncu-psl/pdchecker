import ast

from typing import List

from spec import *
from collections import defaultdict

from functools import partial, partialmethod

from pdb import set_trace

import spec

def with_ast(node, ast_node):
    if type(node) is list:
        class list_with_ast(list):
            def __init__(self, *args, **kwargs):
                list.__init__(*args, **kwargs)
        node = list_with_ast(node)
    elif type(node) is str:
        class str_with_ast(str):
            def __init__(self, *args, **kwargs):
                str.__init__(*args, **kwargs)
        node = str_with_ast(node)
    setattr(node, 'ast', ast_node)
    return node

def mark_slice(subs, s):
    setattr(s, 'lineno', subs.value.end_lineno)
    setattr(s, 'col_offset', subs.value.end_col_offset)
    setattr(s, 'end_lineno', subs.end_lineno)
    setattr(s, 'end_col_offset', subs.end_col_offset)



class Annotator(ast.NodeTransformer):
    def visit_Subscript(self, node: ast.Subscript):
        slice = node.slice
        if type(slice) is ast.Index:
            ast.copy_location(node, node.value)
        return node

class Interpreter:
    def interprets(self, xs):
        return [self.interpret(x) for x in xs]
    def interpret(self, a):
        if not a:
            return
        elif type(a) == ast.Module:
            body = self.interprets(a.body)
            return self.Module(a, body)
        elif type(a) == ast.Expression:
            return self.Expression(a.body)
        elif type(a) == ast.ClassDef:
            body = self.interprets(a.body)
            return self.ClassDef(a, a.name, a.bases, a.keywords, body, a.decorator_list)
        elif type(a) == ast.FunctionDef:
            # body = self.interprets(a.body)
            return self.FunctionDef(a, a.body)
        elif type(a) == ast.Expr:
            return self.interpret(a.value)
        elif type(a) == ast.Call:
            f = self.interpret(a.func)
            args = self.interprets(a.args)
            kws = self.interprets(a.keywords)
            return self.Call(a, f, args, kws)
        elif type(a) == ast.Constant:
            v = a.value
            return self.Constant(a, v)
        elif type(a) == ast.Dict:
            keys = self.interprets(a.keys)
            values = self.interprets(a.values)
            return self.Dict(a, keys, values)
        elif type(a) == ast.List:
            elts = self.interprets(a.elts)
            return self.List(a, elts, a.ctx)
        elif type(a) == ast.Tuple:
            # XXX
            elts = self.interprets(a.elts)
            return self.List(a, elts, a.ctx)
        elif type(a) == ast.Name:
            _id = a.id
            ctx = a.ctx
            return self.Name(a, _id, ctx)
        elif type(a) == ast.keyword:
            v = self.interpret(a.value)
            return self.Keyword(a, a.arg, v)
        elif type(a) == ast.Attribute:
            v = self.interpret(a.value)
            return self.Attribute(a, v, a.attr, a.ctx)
        elif type(a) == ast.Subscript:
            v = self.interpret(a.value)
            _slice = self.interpret(a.slice)
            return self.Subscript(a, v, _slice, a.ctx)
        elif type(a) == ast.Index:
            v = self.interpret(a.value)
            return self.Index(a, v)
        elif type(a) == ast.Import:
            return self.Import(a, a.names)
        elif type(a) == ast.Assign:
            targets = self.interprets(a.targets)
            values = self.interpret(a.value)
            return self.Assign(a, targets, values)
        elif type(a) == ast.BinOp:
            left = self.interpret(a.left)
            right = self.interpret(a.right)
            return getattr(self, type(a.op).__name__)(a, left, right)
        elif type(a) == ast.Slice:
            lower = self.interpret(a.lower)
            upper = self.interpret(a.upper)
            step  = self.interpret(a.step)
            s = self.Slice(a, lower=lower, upper=upper, step=step)
            return 
        elif type(a) == ast.ExtSlice:
            dims = self.interprets(a.dims)
            return self.ExtSlice(a, dims)
        elif type(a) == ast.Return:
            value = self.interpret(a.value)
            return self.Return(a, value)
        else:
            if type(a) is list:
                if a:
                    raise Exception(ast.dump(a[0]))
                else:
                    raise Exception([])
            else:
                raise Exception(ast.dump(a))


class Ty(Interpreter):
    env = {}
    def Module(self, a, body):
        return body[-1]
    def Expression(self, a, body):
        return self.interpret(body)
    def Import(self, a, names):
        for n in a.names:
            if type(n) == ast.alias:
                if n.name == 'pandas':
                    self.env[n.asname] = spec
    def Name(self, a, _id, ctx):
        if type(ctx) == ast.Store:
            return partial(self.env.__setitem__, _id)
        return self.env[_id]
    def Assign(self, a, targets, value):
        if len(targets) > 1:
            return None
        return targets[0](value)
    def Attribute(self, a, value, attr, _ctx):
        attr = with_ast(attr, a)
        if not value:
            raise CheckerNotImplementedError(a, attr)
        return getattr(value, attr)
    def Constant(self, a, v):
        if type(v) is str:
            return StrLike(v)
        elif type(v) is int:
            return IntLike(v)
        elif type(v) is bool:
            return Bool(v)
        else:
            raise TypeError(f'unsupport constant: {v !r}')
    def Call(self, a, f, args, kwargs):
        # TODO: align params here
        args = [with_ast(n, an) for n, an in zip(args, a.args)]
        kwargs = [(k, with_ast(n, an)) for (k, n), an in zip(kwargs, a.keywords)]
        return f(*args, **dict(kwargs))
    def Keyword(self, a, arg, value):
        return (arg, value)
    def Subscript(self, a, v, _slice, _ctx):

        mark_slice(a, a.slice)
        if type(_ctx) == ast.Store:
            return partial(v.__setitem__, _slice.val)
        s = with_ast(_slice, a.slice)
        if v:
            return v[s]
        raise CheckerError('')
    def Index(self, a, v):
        return v
    def Dict(self, a, keys, values):
        # XXXX
        return DictLike({k.val:v for k, v in zip(keys, values)})
    def List(self, a, elts, v):
        # XXX
        if elts:
            return ListLike(elts, elts[0])
        else:
            return ListLike([], None)
    def Add(self, a, left, right):
        return left + right
    def Sub(self, a, left, right):
        return left - right
    def Mul(self, a, left, right):
        return left * right
    def Div(self, a, left, right):
        return left / right
    def Slice(self, a, lower, upper, step):
        return slice(lower, upper, step)
    def ExtSlice(self, a, dims):
        return dims
    def FunctionDef(self, a: ast.FunctionDef, body):
        ret_type = self.from_annotation(a.returns)
        arg_type = [self.from_annotation(arg.annotation) for arg in a.args.args]
        class Func:
            def __call__(self, *args):
                for arg, expected in zip(args, arg_type):
                    if not arg.subtype_of(expected):
                        raise CheckerTypeError(None, expected, arg)
                return ret_type
            def __repr__(self):
                return f'Func({a.name}: {arg_type} -> {ret_type})'
        f = Func()
        self.env[a.name] = f
        return None
    def Return(self, *args):
        return
    def from_annotation(self, a: ast.Expr):
        #XXX
        assert type(a) == ast.Name
        e = a.id
        if e == 'int':
            return IntLike(None)
        elif e == 'str':
            return StrLike(None)
        elif e == 'float':
            return FloatLike()
        else:
            raise CheckerNotImplementedError(a, a)

class TyLog(Ty):
    def __init__(self):
        self.srcmap = {}
    def __getattribute__(self, attr):
        orig = Ty.__getattribute__(self, attr)
        if not hasattr(orig, '__call__') or not orig.__name__[0].isupper():
            return orig
        if attr != 'Name':
            def f(a, *args, **kwargs):
                res = orig(a, *args, **kwargs)
                self.srcmap[a] = res
                return res
        else:
            def f(a, _id, ctx):
                res = orig(a, _id, ctx)
                if type(ctx) != ast.Store:
                    self.srcmap[a] = res
                return res
        f.__name__ = attr
        return f



class TyError(TyLog):
    def __init__(self):
        TyLog.__init__(self)
        self.errors = []



    def __getattribute__(self, attr):
        orig = TyLog.__getattribute__(self, attr)
        if not hasattr(orig, '__call__') or not orig.__name__[0].isupper():
            return orig
        def f(a, *args, **kwargs):
            try:
                res = orig(a, *args, **kwargs)
                return res
            except CheckerError as e:
                def info(e, a, attr):
                    if hasattr(e, 'ast') and hasattr(e.ast, attr):
                        return getattr(e.ast, attr)
                    return getattr(a, attr)
                self.errors.append({
                    'node': attr,
                    'lineno':         info(e, a, 'lineno'),
                    'col_offset':     info(e, a, 'col_offset'),
                    'end_lineno':     info(e, a, 'end_lineno'),
                    'end_col_offset': info(e, a, 'end_col_offset'),
                    'error': e
                    })
        f.__name__ = attr
        return f

class Sp(Interpreter):
    env = {}
    def Module(self, a, body):
        pass
    def Name(self, a, _id, ctx):
        pass
    def ClassDef(self, a, name, bases, keywords, body, decorator_list):
        self.env[name] = defaultdict(list)
        for k, v in body:
            self.env[name][k].append(v)
    def FunctionDef(self, a: ast.FunctionDef, body):
        return (a.name, match)
    def Constant(self, a, v):
        return

class Literal:
    def __getitem__(self, value):
        return LiteralType(value)

def check(code):
    itpr = TyError()
    itpr.env['Literal'] = Literal()
    itpr.interpret(ast.parse(code))
    return itpr

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        code = open(sys.argv[1]).read()
    else:
        code = sys.stdin.read()
    itpr = check(code)
    for e in itpr.errors:
        print(e['lineno'], e['col_offset'], e['error'].message, sep='\t')
