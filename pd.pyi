from typing import Generic, TypeVar

def fulfills(arg):
    def d(f):
        def g(*args, **kwargs):
            print(arg)
            f(*args, **kwargs)
        return g
    return d


class Series:
    pass

class DataFrame(Generic[X]):

    @fulfills("Y = X[sel]")
    def loc(self, sel: Label) -> Series[Y]: ...

    def iloc(self, sel: Label) -> Series[Y]: ...

    def dropna(
            self,
            inplace: Literal[False] = ...,
            axis: int = ...,
            how: _str = ...,
            subset: _ColSubsetType = ...,) -> DataFrame[X]: ...

    @overload
    @fulfills("labels in X.keys, Y = X.delete(labels)")
    def drop(self, labels: List[Label], axis: Literal[1]= ...) -> DataFrame[Y]: ...
