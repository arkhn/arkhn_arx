from arkhn_arx.main_arx import Anonymizer

import pandas as pd
import json
import os

# Input dataframe
df = pd.read_csv("sample_test/data_test.csv")

# Input config dict
with open("sample_test/config_test.txt") as cf:
    config_dict = json.load(cf)

# ARXaaS connection url : here ARXaaS is running locally
url = "http://localhost:8080"

an_tool = Anonymizer(url)

an_df, metrics = an_tool.anonymize_dataset(df, config_dict)

if not os.path.exists("results"):
    os.mkdir("results")

an_df.to_csv("results/anonymized_df.csv")
metrics.to_csv("results/risk_metrics.csv")