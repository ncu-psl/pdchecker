import pandas as pd
from dataclasses import dataclass

__ALL__ = ['Series', 'DataFrame']



@fulfills("test")
class Series:
    pass

@dataclass
class DataFrame:
    df: pd.DataFrame = None

    def iloc(self:DataFrame[X], selector):
        res = self.iloc[selector]
        return DataFrame(res)


