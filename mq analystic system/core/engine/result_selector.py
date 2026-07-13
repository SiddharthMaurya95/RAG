import pandas as pd

def select_data(result, env):
    if isinstance(result, (pd.DataFrame, pd.Series)):
        return result

    for v in env.values():
        if isinstance(v, (pd.DataFrame, pd.Series)):
            return v

    return result