import pandas as pd


def load_complaints(path: str = "data/complaints.csv") -> pd.DataFrame:
    return pd.read_csv(path)


def load_rainfall(path: str = "data/rainfall.csv") -> pd.DataFrame:
    return pd.read_csv(path)
