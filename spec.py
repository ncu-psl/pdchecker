from typing import List, Tuple, Callable, Dict, Optional, Type, Any, Union, Generic, TypeVar, get_args, get_origin
from dataclasses import dataclass, field


@dataclass
class Typed:
    _type: Type
    lit: Any
    def __init__(self, _type: Type, lit: Any):
        self._type = _type
        self.lit = lit

        if get_origin(_type) is list:
            types = [t._type for t in lit]
            if types and all(t == types[0] for t in types):
                self._type = List[types[0]]

def in_union(t1, t2):
    if get_origin(t2) is Union:
        return t1 in get_args(t2)
    else:
        return t1 == t2

@dataclass
class Series:
    index: Type = None
    value: Type = None

StrLike = Union[str]

@dataclass
class LocIndexerFrame:
    index: Type = None
    columns: Dict[str, Type] = field(default_factory=dict)

    def __getitem__(self, idx: Typed):
        if in_union(idx._type, StrLike):
            if idx.lit in self.columns:
                return Series(index=self.index, value=self.columns.get(idx.lit))
            else:
                raise TypeError(f'{idx.lit} not in dataframe')
        elif get_origin(idx._type) is list:
            res = {}
            missing = []
            for label in idx.lit:
                if label.lit in self.columns:
                    res[label.lit] = self.columns[label.lit]
                else:
                    missing.append(label)
            if missing:
                raise TypeError(f'{missing!r} not in dataframe')
            return DataFrame(index=self.index, columns=res)

        else:
            raise TypeError(f'Not type checked: {idx!r}')



@dataclass
class DataFrame:
    index: Type = None
    columns: Dict[str, Type] = field(default_factory=dict)

    @property
    def loc(self):
        return LocIndexerFrame(self.index, self.columns)


    @staticmethod
    def ___init__(self):
        return DataFrame()

    def assign(self, **kwargs: Dict[str, Typed]):
        new_cols = {}
        for k, v in kwargs.items():
            if isinstance(get_origin(v._type), Callable):
                ret_type = get_args(v._type)[-1]
                if isinstance(ret_type, Series):
                    new_cols[k] = ret_type.value
                else:
                    raise TypeError('Callable not returning a Series')
            elif isinstance(v._type, Series):
                new_cols[k] = v._type.value
            elif get_origin(v._type) is list:
                new_cols[k] = get_args(v._type)[-1]
            else:
                raise TypeError(f'Not type checked: {v._type!r}')
        return DataFrame(self.index, {**self.columns, **new_cols})

    def count(self, axis=None):
        if axis in [None, 0, 'index']:
            return Series(str, int)
        elif axis in [1, 'columns']:
            return Series(self.index, int)

    def describe(self):
        return DataFrame()

    def merge(self, other, on, how='left'):
        if not isinstance(other, DataFrame):
            raise TypeError('other is not a DataFrame')
        other: DataFrame = other
        on_labels = [lbl.lit for lbl in on.lit]
        if not all(lbl in self.columns for lbl in on_labels):
            raise TypeError('missing label')
        if not all(lbl in other.columns for lbl in on_labels):
            raise TypeError('missing label')

        left_fields  = [ self.columns[lbl] for lbl in on_labels]
        right_fields = [other.columns[lbl] for lbl in on_labels]

        if not all(t1 == t2 for t1, t2 in zip(left_fields, right_fields)):
            raise TypeError('type mismatch')

        return DataFrame(self.index, {**self.columns, **other.columns})

    def groupby(self, by=None):
        if isinstance(by, Typed):
            key = None
            if by._type is str and by.lit in self.columns:
                key = [by.lit]
            elif get_origin(by._type) is list and get_args(by._type)[0] is str:
                if not all(lbl.lit in self.columns for lbl in by.lit):
                    raise TypeError('key not found')
                else:
                    key = [lbl.lit for lbl in by.lit]
            if key:
                return DataFrameGroupBy(key, self)
        raise TypeError('Not type checked')


@dataclass
class DataFrameGroupBy:
    key: List[str] = None
    df: DataFrame = None

    def agg(self, func, axis=0):
        if not isinstance(get_origin(func._type), Callable):
            raise TypeError('not a function')

        def apply(f, v):
            args, ret = get_args(func._type)
            #XXX check input
            return ret

        return DataFrame(tuple(self.df.columns[k] for k in self.key),
                        {k: apply(func, v) for k, v in self.df.columns.items() if k not in self.key})

        raise TypeError('Not Type checked')
