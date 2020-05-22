from typing import List, Tuple, Callable, Dict, Optional, Type, Any, Union, Generic, TypeVar, get_args, get_origin
from dataclasses import dataclass, field


def read_csv(fp):
    import pandas as pd
    df = pd.read_csv(fp.val)
    return DataFrame(_index=df.index.dtype, _columns=df.dtypes.to_dict())

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
class IntLike(Type):
    val: int
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
class Func(Type):
    arg: Any
    ret: Any
    def __call__(self, arg):
        # XXX
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
        if type(idx) is StrLike:
            if idx.val in self.df.columns:
                return Series(_index=self.df.index, _value=self.df.columns.get(idx.val))
            else:
                raise TypeError(f'{idx.val} not in dataframe')
        elif type(idx) is ListLike:
            res = {}
            missing = []
            for label in idx.val:
                if label.val in self.df.columns:
                    res[label.val] = self.df.columns[label.val]
                else:
                    missing.append(label)
            if missing:
                raise TypeError(f'{missing!r} not in dataframe')
            return DataFrame(_index=self.df.index, _columns=res)

        else:
            raise TypeError(f'Not type checked: {idx!r}')


@dataclass
class DataFrame(Type):
    index: Type = None
    columns: Dict[str, Type] = field(default_factory=dict)

    def __init__(self, *, _index=None, _columns=None):
        self.index = _index
        self.columns = _columns

    def __getitem__(self, idx):
        return LocIndexerFrame(self).__getitem__(idx)

    def __set_item__(self, idx, value):
        new = self.assign(**{idx: value})
        self.columns = new.columns
        self.index = new.index


    @property
    def loc(self):
        return LocIndexerFrame(self.index, self.columns)

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
                    raise TypeError('Callable not returning a Series')
            elif type(v) is ListLike:
                new_cols[k] = v.value
            else:
                raise TypeError(f'Not type checked: {v._type!r}')
        return DataFrame(_index=self.index, _columns={**self.columns, **new_cols})

    def count(self, axis=None):
        if axis in [None, 0, 'index']:
            return Series(_index=str, _value=int)
        elif axis in [1, 'columns']:
            return Series(_index=self.index, _value=int)

    def describe(self):
        return DataFrame()

    def merge(self, other, on, how='left'):
        if not isinstance(other, DataFrame):
            raise TypeError('other is not a DataFrame')
        other: DataFrame = other
        on_labels = [lbl.val for lbl in on.val]
        if not all(lbl in self.columns for lbl in on_labels):
            raise TypeError('missing label')
        if not all(lbl in other.columns for lbl in on_labels):
            raise TypeError('missing label')

        left_fields  = [ self.columns[lbl] for lbl in on_labels]
        right_fields = [other.columns[lbl] for lbl in on_labels]

        if not all(t1 == t2 for t1, t2 in zip(left_fields, right_fields)):
            raise TypeError('type mismatch')

        return DataFrame(_index=self.index, _columns={**self.columns, **other.columns})

    def groupby(self, by=None):
        key = None
        if type(by) is StrLike and by.val in self.columns:
            key = [by.val]
        elif type(by) is ListLike and by.typ is StrLike:
            if not all(lbl.val in self.columns for lbl in by.val):
                raise TypeError('key not found')
            else:
                key = [lbl.val for lbl in by.val]
        if key:
            return DataFrameGroupBy(key, self)
        raise TypeError('Not type checked')


    def drop_duplicates(self, subset=None, keep=None):
        missing = []
        for label in subset.val:
            if label.val not in self.columns:
                missing.append(label.val)
        if missing:
            raise IndexError()
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
            raise NotImplemented()

    def hint_cast(self, **kwargs):
        return DataFrame(_index=self.index, _columns={**self.columns, **kwargs})

@dataclass
class DataFrameGroupBy:
    key: List[str] = None
    df: DataFrame = None

    def agg(self, func, axis=0):
        if type(func) is not Func:
            raise TypeError('not a function')

        return DataFrame(_index=tuple(self.df.columns[k] for k in self.key),
                        _columns={k: func(v) for k, v in self.df.columns.items() if k not in self.key})

        raise TypeError('Not Type checked')
