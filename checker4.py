import ast

from typing import List

from spec4 import DataFrame, Typed
from collections import defaultdict

from functools import partial, partialmethod

from pdb import set_trace

import spec4 as spec

class Interpreter:
    def interprets(self, xs):
        return [self.interpret(x) for x in xs]
    def interpret(self, a):
        if type(a) == ast.Module:
            body = self.interprets(a.body)
            return self.Module(a, body)
        elif type(a) == ast.Expression:
            return self.interpret(a.body)
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
        elif type(a) == ast.List:
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
        targets[0](value)
        return None
    def Attribute(self, a, value, attr, _ctx):
        return getattr(value,attr)
    def Constant(self, a, v):
        return Typed(type(v), v)
    def Call(self, a, f, args, kwargs):
        # TODO: align params here
        return f(*args, **dict(kwargs))
    def Keyword(self, a, arg, value):
        return (arg, value)
    def Subscript(self, a, v, _slice, _ctx):
        if type(_ctx) == ast.Store:
            return partial(v.__set_item__, _slice.lit)
        return v[_slice]
    def Index(self, a, v):
        return v
    def List(self, a, elts, v):
        return Typed(List, elts)
    def Add(self, a, left, right):
        return left + right

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
itpr = Ty()
# itpr.env['df1'] = DataFrame(__index=int, __columns={'x': int})

code = '''
import pandas as pd
df = pd.read_csv('/tmp/test.csv')
df["x"] = pd.Series([1,2,3])
df['y'] = df['x'] + 1
'''

t = itpr.interpret(ast.parse(code))
print(t)
print(itpr.env)

