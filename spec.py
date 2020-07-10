from typing import List, Tuple, Callable, Dict, Optional, Type, Any, Union, Generic, TypeVar
from dataclasses import dataclass, field

class CheckerError(Exception):
    def __init__(self, message, ast=None):
        self.message = message
        self.ast = ast
    def __str__(self):
        return self.message

class CheckerTypeError(CheckerError):
    def __init__(self, ast=None, expected=None, actual=None):
        self.ast = ast
        self.message = f'TypeError: expected {expected!r} but got {actual!r}'

class CheckerNotImplementedError(CheckerError):
    def __init__(self, ast=None, obj=None):
        self.obj = obj
        self.ast = ast
        self.message = f'Not implemented for {obj !r}.'

class CheckerIndexError(CheckerError):
    def __init__(self, index, df=None, ast=None):
        self.index = index
        self.ast = ast
        self.message = f'Index {index !r} not found.'


class CheckerLackOfInfo(CheckerError):
    def __init__(self, ast):
        self.message = 'Lack of column types.'
        self.ast = ast

class CheckerParamError(CheckerError):
    def __init__(self, p, ps, ast=None):
        self.mesage = f'Parameter {p !r} is not in {ps !r}'
        self.ast = ast

def ensure_labels(df, col):
    missing = []
    for label in col:
        if label not in df.columns:
            missing.append(label)
    if missing:
        raise CheckerIndexError(missing, df)

def from_dtype(dt):
    if dt.kind == 'i':
        return IntLike(None)
    elif dt.kind == 'f':
        return FloatLike()
    elif dt.kind == 'O':
        # XXX
        return StrLike(None)
    else:
        raise CheckerNotImplementedError(obj=dt)


def read_csv(fp):
    import pandas as pd
    df = pd.read_csv(fp.val)
    return DataFrame(_index=from_dtype(df.index.dtype),
                     _columns={k: from_dtype(v)
                                  for k, v in df.dtypes.to_dict().items()})

class Type:
    def subtype_of(self, other):
        return other.subtype(self)
    def subtype(self, other):
        return NotImplemented
    def binop(self, other):
        return NotImplemented
    def rbinop(self, other):
        return NotImplemented

    def __add__(self, other):  return self.binop(other)
    def __sub__(self, other):  return self.binop(other)
    def __mul__(self, other):  return self.binop(other)
    def __div__(self, other):  return self.binop(other)
    def __radd__(self, other): return self.rbinop(other)
    def __rsub__(self, other): return self.rbinop(other)
    def __rmul__(self, other): return self.rbinop(other)
    def __rdiv__(self, other): return self.rbinop(other)


class NoneType(Type):
    __single = None

    def __new__(clz):
        if not NoneType.__single:
            NoneType.__single = object.__new__(clz)
        return NoneType.__single


@dataclass
class LiteralType(Type):
    kinds: List[Type]
    def __init__(self, vs):
        if type(vs) is ListLike:
            self.kinds = vs.val
        else:
            self.kinds = vs
    def subtype(other):
        return any(other.val == k.val for k in kinds)

@dataclass
class Bool(Type):
    val: bool
    def __bool__(self):
        return bool(self.val)


@dataclass
class FloatLike(Type):
    pass

@dataclass
class IntLike(Type):
    val: int
    def __bool__(self):
        return bool(self.value)
    def empty(self):
        return IntLike(None)
    def subtype(self, other):
        if type(other) is IntLike:
            return True
        return False
    def binop(self, other):
        if type(other) is IntLike:
            return self.empty()
        else:
            return NotImplemented

@dataclass
class StrLike(Type):
    val: str

@dataclass
class ListLike(Type):
    val: Any
    typ: Type


@dataclass
class DictLike(Type):
    val: Any


@dataclass
class Func(Type):
    arg: Any
    ret: Any
    def __call__(self, arg):
        if arg != self.arg:
            raise CheckerError()
        return self.ret

@dataclass
class Series(Type):
    index: Type = None
    value: Type = None
    def __init__(self, data = None, index=None, *, _index=None, _value=None):
        self.index = _index
        self.value = _value
        if type(data) is ListLike:
            self.value = data.typ

    def apply(self, func):
        return Series(_index=self.index, _value=func(self.value))

    def binop(self, other):
        return Series(_index=self.index, _value=self.value.binop(other))

    __add__ = binop
    __sub__ = binop
    __mul__ = binop
    __truediv__ = binop

@dataclass
class LocIndexerFrame(Type):
    df: 'DataFrame'

    def __getitem__(self, idx):
        if type(idx) is not list:
            return #XXX

        col = idx[1]
        if type(col) is StrLike:
            if col.val in self.df.columns:
                return Series(_index=self.df.index, _value=self.df.columns.get(col.val))
            else:
                raise CheckerIndexError(index=col.val, df=self.df, ast=idx.ast)
        elif type(col) is ListLike:
            res = {}
            missing = []
            for label in col.val:
                if label.val in self.df.columns:
                    res[label.val] = self.df.columns[label.val]
                else:
                    missing.append(label)
            if missing:
                raise CheckerIndexError(index=missing)
            return DataFrame(_index=self.df.index, _columns=res)
        elif type(col) is slice:
            return self
        else:
            raise CheckerNotImplementedError(col)


@dataclass
class DataFrame(Type):
    index: Type = None
    columns: Dict[str, Type] = field(default_factory=dict)


    def __getattr__(self, attr):
        if attr in self.columns:
                return Series(_index=self.index, _value=self.columns.get(attr))
        raise CheckerNotImplementedError(attr.ast, attr)

    def __init__(self, data=None, index=None, columns=None, *, _index=None, _columns=None):
        self.index = _index
        self.columns = _columns
        if type(data) is ListLike and type(data.typ) is ListLike:
            if not index:
                self.index = IntLike(None)
            if not columns:
                self.columns = {i:x for i, x in enumerate(data.typ.val)}
            else:
                self.columns = {i.val:x for i, x in zip(columns.val, data.typ.val)}



    def __getitem__(self, idx):
        if type(idx) is StrLike:
            if idx.val in self.columns:
                return Series(_index=self.index, _value=self.columns.get(idx.val))
            else:
                raise CheckerIndexError(index=idx.val, df=self, ast=idx.ast)
        elif type(idx) is ListLike:
            res = {}
            missing = []
            for label in idx.val:
                if label.val in self.columns:
                    res[label.val] = self.columns[label.val]
                else:
                    missing.append(label.val)
            if missing:
                raise CheckerIndexError(index=missing, ast=idx.ast)
            return DataFrame(_index=self.index, _columns=res)
        elif type(idx) is slice:
            return self
        else:
            raise CheckerNotImplementedError(idx.ast, idx)

    def __setitem__(self, idx, value):
        new = self.assign(**{idx: value})
        self.columns = new.columns
        self.index = new.index


    @property
    def loc(self):
        return LocIndexerFrame(self)

    def assign(self, **kwargs: Dict[str, Type]):
        new_cols = {}
        for k, v in kwargs.items():
            if isinstance(v, Series):
                new_cols[k] = v.value
            elif type(v) is Func:
                ret_type = v.ret
                if isinstance(ret_type, Series):
                    new_cols[k] = ret_type.value
                else:
                    raise CheckerError('Callable not returning a Series')
            elif type(v) is ListLike:
                new_cols[k] = v.value
            # else:
            #     raise Exception(f'Not type checked: {v!r}')
        return DataFrame(_index=self.index, _columns={**self.columns, **new_cols})

    def count(self, axis=None):
        if axis in [None, 0, 'index']:
            return Series(_index=str, _value=int)
        elif axis in [1, 'columns']:
            return Series(_index=self.index, _value=int)

    def describe(self):
        return DataFrame()

    def merge(self, other, on=None, how=None):
        possible_how = ['inner', 'left', 'right', 'outer']
        if how and how.val not in possible_how:
            raise CheckerParamError(how.val, possible_how)
        if not isinstance(other, DataFrame):
            raise CheckerError('other is not a DataFrame')
        other: DataFrame = other
        if type(on) is not ListLike:
            on = ListLike([on], on)
        on_labels = [lbl.val for lbl in on.val]
        ensure_labels(self, on_labels)
        ensure_labels(other, on_labels)

        left_fields  = [ self.columns[lbl] for lbl in on_labels]
        right_fields = [other.columns[lbl] for lbl in on_labels]

        if not all(t1.subtype(t2) for t1, t2 in zip(left_fields, right_fields)):
            raise CheckerError('type mismatch')

        overlapped = set(self.columns.keys()).intersection(set(other.columns.keys())) - set(on_labels)
        new = {}

        for lbl, typ in self.columns.items():
            if lbl in overlapped:
                lbl += '_x'
            new[lbl] = typ

        for lbl, typ in other.columns.items():
            if lbl in overlapped:
                lbl += '_y'
            new[lbl] = typ

        for lbl in on_labels:
            new[lbl] = self.columns[lbl]

        return DataFrame(_index=self.index, _columns=new)

    def groupby(self, by=None):
        key = None
        if type(by) is StrLike and by.val in self.columns:
            key = [by.val]
        elif type(by) is ListLike and by.typ is StrLike:
            if not all(lbl.val in self.columns for lbl in by.val):
                raise CheckerError('key not found')
            else:
                key = [lbl.val for lbl in by.val]
        if key:
            return DataFrameGroupBy(key, self)
        raise CheckerError('Not type checked')


    def drop_duplicates(self, subset=None, keep=None):
        missing = []
        for label in subset.val:
            if label.val not in self.columns:
                missing.append(label.val)
        if missing:
            raise CheckerIndexError(index=missing)
        return self

    def sort_values(self, by, axis=None, ascending=None, inplace=None, kind=None, na_position=None, ignore_index=None):
        if type(by) is not ListLike:
            by = ListLike([by], by)
        missing = []
        for label in by.val:
            if label.val not in self.columns:
                missing.append(label.val)
        if missing:
            raise CheckerIndexError(index=missing)

        if inplace:
            return None

        return self


    def pivot(self, index, columns, values):
        # TODO multiple column/values
        idx    = self.columns[index.val]
        col    = self.columns[columns.val]
        value  = self.columns[values.val]
        if type(col) is LiteralType:
            new_labels = col.kinds
            new_col    = {l.val:value for l in new_labels}
            return DataFrame(_index=idx, _columns=new_col)
        else:
            # try ask a LiteralType
            raise CheckerNotImplementedError()

    def hint_cast(self, **kwargs):
        return DataFrame(_index=self.index, _columns={**self.columns, **kwargs})

@dataclass
class DataFrameGroupBy:
    key: List[str] = None
    df: DataFrame = None

    def agg(self, func, axis=0):
        if type(func) is not Func and not hasattr(func, '__call__'):
            raise CheckerError('not a function')

        return DataFrame(_index=tuple(self.df.columns[k] for k in self.key),
                        _columns={k: func(v) for k, v in self.df.columns.items() if k not in self.key})

        raise CheckerError('Not Type checked')
