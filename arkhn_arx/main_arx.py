from pyarxaas import ARXaaS
from pyarxaas.privacy_models import KAnonymity, LDiversityDistinct
from pyarxaas import AttributeType, Dataset
from pyarxaas.hierarchy import IntervalHierarchyBuilder, DateHierarchyBuilder, RedactionHierarchyBuilder

import pandas as pd
import json
import os

import argparse

class Anonymizer:
    def __init__(
            self,
            df,
            config,
            url
    ):
        self.df = df
        self.config = config
        self.url = url

        self.arxaas = ARXaaS(self.url)

        self.config_params = config["anonymization"]
        self.mode = self.config_params["type"]
        self.config_attributes = config["attributes"]

        for col in self.df:
            if col not in [att["customName"] for att in self.config_attributes]:
                print(f"{col} not in config file, deleting {col} from dataframe ")
                df.drop(col, axis=1, inplace=True)

        self.q = 4

    def anonymize_dataset(self):
        """
        Main method, returns anonymized dataframe and reidentification risk metrics
        :return: anonymized dataframe and risk metrics dataframe
        """
        if self.mode == 0:
            dataset = self.create_dataset(self.df)
            dataset = self.define_attribute_type(dataset)
            metrics = self.risk_metrics(dataset)

        elif self.mode == 1:
            dataset = self.create_dataset(self.df)
            dataset = self.define_attribute_type(dataset)
            metrics = self.risk_metrics(dataset)
            self.df = self.pseudonymize_data(self.df)

        elif self.mode == 2:
            self.df = self.clean_data(self.df)
            dataset = self.create_dataset(self.df)
            dataset = self.define_attribute_type(dataset)
            dataset = self.define_hierarchies(dataset)
            print(dataset)
            an_result = self.anonymize(dataset)
            self.df = self.output_dataframe(an_result)
            metrics = self.risk_metrics(an_result)


        return self.df, metrics


    def pseudonymize_data(self):
        """Remove identifying attributes from dataset

        """
        for att in self.config_attributes:
            if att['att_type'] == 'identifying':
                self.df[att["customName"]] = '*'
        return self.df


    def clean_data(self, df):
        """
        Define attribute dtype needed for hierarchy type
        :param df: input dataframe
        :param cf: config dict containing attribute types and hierarchies types
        :return: cleaned dataframe
        """
        for att in self.config_attributes:
            if att['att_type'] == 'quasiidentifying':
                df.dropna(subset=[att["customName"]], inplace=True)
                if att['hierarchy_type'] == 'interval':
                    df[att["customName"]] = df[att["customName"]].astype(float)
                elif att['hierarchy_type'] == 'date':
                    df[att["customName"]] = pd.to_datetime(df[att["customName"]], yearfirst=True).astype(str)
                elif att['hierarchy_type'] == 'redaction' or att['hierarchy_type'] == 'order':
                    df[att["customName"]] = df[att["customName"]].astype(str)
        return df


    def create_dataset(self, df):
        """
        Returns dataset from pandas df
        :param df:
        :return:
        """
        dataset = Dataset.from_pandas(df)
        return dataset


    def define_attribute_type(self, dataset):
        """
        Define attribute types for all attributes in dataset
        :param df: initial dataframe
        :param dataset: arx dataset
        :param cf: config dict
        :return: dataset with set attributes
        """
        for att in self.config_attributes:
            if att['att_type'] == "identifying":
                dataset.set_attribute_type(AttributeType.IDENTIFYING, att["customName"])
            elif att['att_type'] == "quasiidentifying":
                dataset.set_attribute_type(AttributeType.QUASIIDENTIFYING, att["customName"])
            elif att['att_type'] == "sensitive":
                dataset.set_attribute_type(AttributeType.SENSITIVE, att["customName"])
            elif att['att_type'] == "insensitive":
                dataset.set_attribute_type(AttributeType.INSENSITIVE, att["customName"])
            else:
                raise Exception("unknow attribute type")
        return dataset

    def define_hierarchies(self, dataset):
        """
        Define hierarchies and set hierachies for datatset
        :return: dataset with set hierarchies
        """
        hierarchies = {}
        for att in self.config_attributes:
            if att["att_type"] == 'quasiidentifying':
                if att["hierarchy_type"] == 'date':
                    hierarchies[att["customName"]] = self.create_date_hierarchy(att["customName"])
                    pass
                elif att["hierarchy_type"] == "interval":
                    hierarchies[att["customName"]] = self.create_interval_hierarchy(att["customName"])
                elif att["hierarchy_type"] == "redaction":
                    hierarchies[att["customName"]] = self.create_redaction_hierarchy(att["customName"])
                else:
                    raise Exception("unknow hierarchy type")
        dataset.set_hierarchies(hierarchies)
        return dataset

    def create_date_hierarchy(self, att):
        """"""
        date_based = DateHierarchyBuilder("yyyy-MM-dd", DateHierarchyBuilder.Granularity.DECADE)
        date_hierarchy = self.arxaas.hierarchy(date_based, self.df[att].tolist())

        return date_hierarchy


    def create_interval_hierarchy(self, att):
        """"""
        bins = self.df[att].quantile([x / float(self.q) for x in range(1, self.q)]).tolist()
        interval_based = IntervalHierarchyBuilder()
        interval_based.add_interval(self.df[att].min(), bins[0], f"[{self.df[att].min()}-{bins[0]}[")
        for i in range(self.q-2):
            interval_based.add_interval(bins[i], bins[i+1], f"[{bins[i]}-{bins[i+1]}[")
        interval_based.add_interval(bins[-1], self.df[att].max()+1., f"[{bins[-1]}-{self.df[att].max()+1}[")
        interval_based.level(0).add_group(self.q//2, f"low").add_group(self.q//2, "high")
        interval_hierarchy = self.arxaas.hierarchy(interval_based, self.df[att].tolist())

        return interval_hierarchy


    def create_redaction_hierarchy(self, att):
        redaction_based = RedactionHierarchyBuilder()
        redaction_hierarchy = self.arxaas.hierarchy(redaction_based, self.df[att].tolist())

        return redaction_hierarchy


    def anonymize(self, dataset):
        """
        Returns anonymization result
        :param dataset: dataset to anonymize
        :return:
        """
        kanon = KAnonymity(self.config_params["k"])

        ldiv = []
        for att in self.config_attributes:
            if att["att_type"] == "sensitive":
                ldiv.append(LDiversityDistinct(self.config_params["l"], att["customName"]))
        anonymize_result = self.arxaas.anonymize(dataset, [kanon]+ldiv, 1)

        return anonymize_result


    def output_dataframe(self, anonymize_result):
        """"""
        return anonymize_result.dataset.to_dataframe()


    def risk_metrics(self, result):
        """
        Returns reidentification risk metrics for dataset or anonymization result object

        """
        try:
            risk_profile = self.arxaas.risk_profile(result)
        except:
            risk_profile = result.risk_profile
        re_identification_risk = risk_profile.re_identification_risk_dataframe()

        return re_identification_risk

    def anonymized_metrics(self, result):
        """"""
        return result.anonymization_metrics.attribute_generalization, result.anonymization_metrics.privacy_models