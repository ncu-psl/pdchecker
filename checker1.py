import libcst as cst
from spec import *


test_code = '''
import pandas as pd
df = pd.read_csv('/tmp/test.csv')
(df
 .loc[['x']] #
 .describe()
 )
'''

test = '''
(df
 .loc[['x']]
 .describe()
 )
'''

from pdb import set_trace

class TypingTransformer(cst.CSTTransformer):
    def visit_FunctionDef(self, origin_node):
        return False
    def leave_FunctionDef(self, origin_node: cst.FunctionDef, updated_node):
        ret_type = origin_node.returns.annotation
        args_type = cst.List([cst.Element(param.annotation.annotation)
                              for param in origin_node.params.params])
        return cst.helpers.parse_template_expression('Typed(Callable[{args_type}, {ret_type}], None)',
                                                     args_type=args_type,
                                                     ret_type=ret_type)
    def leave_Integer(self, origin_node, updated_node):
        return cst.parse_expression('Typed(int, None)')
    def leave_SimpleString(self, origin_node, updated_node):
        return cst.helpers.parse_template_expression('Typed(str, {x})', x=updated_node)
    def visit_List(self, origin_node): return True
    def leave_List(self, origin_node, updated_node: cst.List):
        return cst.helpers.parse_template_expression('Typed(List[Any], {x})', x=updated_node)


ast = cst.parse_module('''(df.loc[['x', 'y']])''')
ast1 = ast.visit(TypingTransformer())
print(ast1.code)

test='''
def f(x: int, y: float) -> str:
    pass
'''

def tr(code):
    if type(code) is str:
        ast = cst.parse_module(code)
    return ast.visit(TypingTransformer()).code


def tc(code):
    return eval(tr(code),
                globals(),
                dict(df=DataFrame(int, {'x': int}),
                    df1=DataFrame(int, {'x': int, 'y': int}),
                    sum1=Typed(Callable[[int], int], None)
                    ))
