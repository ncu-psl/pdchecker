import libcst as cst
from libcst import matchers as m
from typing import List, Tuple, Dict, Optional, Type, Any, Union, Generic, TypeVar, get_args, get_origin
from dataclasses import dataclass, field

class TypingCollector(cst.CSTVisitor):
    def __init__(self):
        # stack for storing the canonical name of the current function
        self.stack: List[Tuple[str, ...]] = []
        # store the annotations
        self.annotations: Dict[
            Tuple[str, ...],  # key: tuple of cononical class/function name
            Tuple[cst.Parameters, Optional[cst.Annotation]],  # value: (params, returns)
        ] = {}

    def visit_ClassDef(self, node: cst.ClassDef) -> Optional[bool]:
        self.stack.append(node.name.value)

    def leave_ClassDef(self, node: cst.ClassDef) -> None:
        self.stack.pop()

    def visit_FunctionDef(self, node: cst.FunctionDef) -> Optional[bool]:
        self.stack.append(node.name.value)
        self.annotations[tuple(self.stack)] = (node.params, node.returns)
        return (
            False
        )  # pyi files don't support inner functions, return False to stop the traversal.

    def leave_FunctionDef(self, node: cst.FunctionDef) -> None:
        self.stack.pop()


class TypingTransformer(cst.CSTTransformer):
    def __init__(self, annotations):
        # stack for storing the canonical name of the current function
        self.stack: List[Tuple[str, ...]] = []
        # store the annotations
        self.annotations: Dict[
            Tuple[str, ...],  # key: tuple of cononical class/function name
            Tuple[cst.Parameters, Optional[cst.Annotation]],  # value: (params, returns)
        ] = annotations

    def visit_ClassDef(self, node: cst.ClassDef) -> Optional[bool]:
        self.stack.append(node.name.value)

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.CSTNode:
        self.stack.pop()
        return updated_node

    def visit_FunctionDef(self, node: cst.FunctionDef) -> Optional[bool]:
        self.stack.append(node.name.value)
        return (
            False
        )  # pyi files don't support inner functions, return False to stop the traversal.

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.CSTNode:
        key = tuple(self.stack)
        self.stack.pop()
        if key in self.annotations:
            annotations = self.annotations[key]
            return updated_node.with_changes(
                params=annotations[0], returns=annotations[1]
            )
        return updated_node

stub_tree = cst.parse_module(open("pd.pyi").read())
visitor = TypingCollector()
stub_tree.visit(visitor)


R = TypeVar("R")
V = TypeVar("V")

class TDataFrame(Generic[R]):
    pass
class TSeries(Generic[V]):
    pass

@dataclass
class DataFrameType:
    index: Type = None
    columns: Dict[str, Type] = field(default_factory=dict)

@dataclass
class GroupedDataFrameType:
    key: Type = None
    df_type: Type = None


@dataclass
class SeriesType:
    index: Type
    value: Type

@dataclass
class DfLoc:
    df:DataFrameType = None
    indexer: Any = None

@dataclass
class DfSelector:
    df:DataFrameType = None
    indexer: Any = None

@dataclass
class DfJoin:
    df:DataFrameType = None
    other:DataFrameType = None
    on: Optional[List[str]] = None

@dataclass
class DfMelt:
    df:DataFrameType = None
    idvars = None
    vals = None

@dataclass
class DfGroup:
    df:DataFrameType = None
    by: List[str]    = None

def typeof_loc(df_type, indexer):
    if isinstance(indexer, list):
        if not all(idx in df_type.columns for idx in indexer):
            raise TypeError("")
        return DataFrameType(
                index=df_type.index,
                columns={k: v for k, v in df_type.columns.items() if k in indexer})
    elif isinstance(indexer, str):
        if indexer not in df_type.columns:
            raise TypeError("")
        return SeriesType(index = df_type.index, value = df_type.columns[indexer])

def typeof(expr):
    if isinstance(expr, DfLoc):
        return typeof_loc(typeof(expr.df), expr.indexer)
    elif isinstance(expr, DfJoin):
        if expr.on:
            df1 = typeof(expr.df)
            df2 = typeof(expr.other)
            on = expr.on
            assert all(o in df1.columns for o in on) and all(o in df2.columns for o in on)
            assert all(t1 == t2 for t1,t2 in zip(
                [t for k, t in df1.columns.items() if k in on],
                [t for k, t in df2.columns.items() if k in on]))
            return DataFrameType(Union[df1.index, df2.index], {**df1.columns, **df2.columns})
    elif isinstance(expr, DataFrameType):
        return expr
    elif isinstance(expr, DfGroup):
        assert all(b in expr.df.columns for b in expr.by)
        by_types = [v for k, v in expr.df.columns.items() if k in expr.by]
        return GroupedDataFrameType(key=by_types, df_type=expr.df)

df1 = DataFrameType(index=int, columns={"x": int, "y": int})
df2 = DataFrameType(index=int, columns={"x": int, "z": int})
expr = DfJoin(df=df1, other=df2, on=['x'])


class Collector(cst.CSTVisitor):
    def __init__(self, m):
        self.m = m
    def visit_Call(self, node: cst.Call):
        print(self.m.code_for_node(node))

class Expr:
    pass


@dataclass
class Stmt:
    name: str
    val:  Expr


def convert_stmt(stmt, env):
    try:
        name = stmt.targets[0].target.value
        val  = convert_expr(stmt.value, env)
    finally:
        pass
    return


# parse in reverse-direction
# check in forward-direction
loc_matcher = m.Subscript(value=m.Attribute(value=m.SaveMatchedNode(m.DoNotCare(), 'value'),
                                        attr=m.Name(value='loc')),
                                        slice=m.SaveMatchedNode(m.DoNotCare(), "slice"))
iloc_matcher = m.Subscript(value=m.Attribute(value=m.SaveMatchedNode(m.DoNotCare(), 'value'),
                                        attr=m.Name(value='iloc')),
                                        slice=m.SaveMatchedNode(m.DoNotCare(), "slice"))


# generate matchers by rule files

# extend pyi to pass type info around


