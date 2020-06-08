from arkhn_arx import Anonymizer

import pandas as pd
import json
import os

df = pd.read_csv("sample_test/data_test.csv")
with open("sample_test/config_test.txt") as cf:
    config_dict = json.load(cf)
url = "http://localhost:8080"

an_tool = Anonymizer(df, config_dict, url)

an_df, metrics = an_tool.anonymize_dataset()

if not os.path.exists("results"):
    os.mkdir("results")

an_df.to_csv("results/anonymized_df.csv")
metrics.to_csv("results/risk_metrics.csv")