import ast

from typing import List

from spec4 import *
from collections import defaultdict

from functools import partial, partialmethod

from pdb import set_trace

import spec4 as spec

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
            body = self.interprets(a.body)
            return self.FunctionDef(a, body)
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
            return self.Slice(a, lower=lower, upper=upper, step=step)
        elif type(a) == ast.ExtSlice:
            dims = self.interprets(a.dims)
            return self.ExtSlice(a, dims)
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
        return getattr(value,attr)
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
        return f(*args, **dict(kwargs))
    def Keyword(self, a, arg, value):
        return (arg, value)
    def Subscript(self, a, v, _slice, _ctx):
        if type(_ctx) == ast.Store:
            return partial(v.__set_item__, _slice.val)
        return v[_slice]
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

class TyLog(Ty):
    def __init__(self):
        self.srcmap = {}
    def __getattribute__(self, attr):
        orig = Ty.__getattribute__(self, attr)
        if not hasattr(orig, '__call__') or not orig.__name__[0].isupper():
            return orig
        def f(a, *args, **kwargs):
            res = orig(a, *args, **kwargs)
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
                self.errors.append({
                    'node': attr,
                    'lineno': a.lineno,
                    'col_offset': a.col_offset,
                    'end_lineno': a.end_lineno,
                    'end_col_offset': a.end_col_offset,
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


# sp = Sp()
# code = '''
# class D:
#     def f(x: int) -> int: ...
# '''
# sp.interpret(ast.parse(code))
# for k,v in Sp.env.items():
#     for f, bs in v.items():
#         for b in bs:
#             print(k, f, [ast.dump(x) for x in b])

class Literal:
    def __getitem__(self, value):
        return LiteralType(value)

def check(code):
    itpr = TyError()
    # itpr.env['df1'] = DataFrame(_index=int, _columns={'x': int})
    # itpr.env['sum']     = Func(IntLike, IntLike)
    itpr.env['Literal'] = Literal()
    itpr.interpret(ast.parse(code))
    return itpr

code = '''
import pandas as pd
df = pd.read_csv('./test.csv')
df2 = pd.read_csv('./test.csv')
df.merge(df2, on='b')
'''


itpr = TyError()
itpr.env['Literal'] = Literal()
res = itpr.interpret(ast.parse(code))
print(res)
print(itpr.errors)

# print(t)
# print(itpr.env)
# print(itpr.srcmap)

