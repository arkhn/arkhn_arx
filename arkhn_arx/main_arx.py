from pyarxaas import ARXaaS
from pyarxaas.privacy_models import KAnonymity, LDiversityDistinct
from pyarxaas import AttributeType, Dataset
from pyarxaas.hierarchy import IntervalHierarchyBuilder, DateHierarchyBuilder, RedactionHierarchyBuilder

import pandas as pd


class Anonymizer:
    def __init__(
            self,
            url
    ):
        self.url = url
        self.arxaas = ARXaaS(self.url)

    def anonymize_dataset(self, df, config):
        """
        Main method, returns anonymized dataframe and reidentification risk metrics
        :param df: dataframe to anonymize
        :param config: config dict giving anonymization and attributes parameters
        :return: anonymized dataframe and risk metrics dataframe
        """

        config_params = config["anonymization"]
        mode = config_params["type"]
        config_attributes = config["attributes"]
        for attr in config_attributes:
            attr["anonymize"] = str(attr["anonymize"])

        # quantile to use for interval hierachy
        q = 4

        for col in df:
            if col not in [att["customName"] for att in config_attributes]:
                print(f"{col} not in config file, deleting {col} from dataframe ")
                df.drop(col, axis=1, inplace=True)

        if mode == 0:
            dataset = self.create_dataset(df)
            dataset, config_attributes = self.define_attribute_type(dataset, config_attributes)
            metrics = self.risk_metrics(dataset)["estimated_journalist_risk"]

            return df, metrics

        elif mode == 1:
            dataset = self.create_dataset(df)
            dataset, config_attributes  = self.define_attribute_type(dataset, config_attributes)
            metrics = self.risk_metrics(dataset)["estimated_journalist_risk"]
            an_df = self.pseudonymize_data(df, config_attributes)

            return an_df, metrics

        elif mode == 2:
            df = self.clean_data(df, config_attributes)
            dataset = self.create_dataset(df)
            dataset, config_attributes = self.define_attribute_type(dataset, config_attributes)
            dataset = self.define_hierarchies(df, dataset,  config_attributes, q)
            an_result = self.anonymize(dataset, config_attributes, config_params)
            an_df = self.output_dataframe(an_result)
            metrics = self.risk_metrics(an_result)["estimated_journalist_risk"]

            return an_df, metrics

    def pseudonymize_data(self, df, config_attributes):
        """Remove identifying attributes from dataset

        """
        for att in config_attributes:
            if att['att_type'] == 'identifying':
                df[att["customName"]] = '*'
        return df

    def clean_data(self, df, config_attributes):
        """
        Define attribute dtype needed for hierarchy type
        :param df: input dataframe
        :param cf: config dict containing attribute types and hierarchies types
        :return: cleaned dataframe
        """
        for att in config_attributes:
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

    def define_attribute_type(self, dataset, config_attributes):
        """
        Define attribute types for all attributes in dataset
        :param df: initial dataframe
        :param dataset: arx dataset
        :param cf: config dict
        :return: dataset with set attributes
        """
        for att in config_attributes:
            if att["anonymize"] == "False":
                att["att_type"]="insensitive"
                dataset.set_attribute_type(AttributeType.INSENSITIVE, att["customName"])
            else:
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
        return dataset, config_attributes

    def define_hierarchies(self, df, dataset, config_attributes, q):
        """
        Define hierarchies and set hierachies for datatset
        :return: dataset with set hierarchies
        """
        hierarchies = {}
        for att in config_attributes:
            if att["att_type"] == 'quasiidentifying':
                if att["hierarchy_type"] == 'date':
                    hierarchies[att["customName"]] = self.create_date_hierarchy(df, att["customName"])
                    pass
                elif att["hierarchy_type"] == "interval":
                    hierarchies[att["customName"]] = self.create_interval_hierarchy(df, att["customName"], q)
                elif att["hierarchy_type"] == "redaction":
                    hierarchies[att["customName"]] = self.create_redaction_hierarchy(df, att["customName"])
                else:
                    raise Exception("unknow hierarchy type")
        dataset.set_hierarchies(hierarchies)
        return dataset

    def create_date_hierarchy(self,df, att):
        """"""
        date_based = DateHierarchyBuilder("yyyy-MM-dd",
                                          DateHierarchyBuilder.Granularity.MONTH_YEAR,
                                          DateHierarchyBuilder.Granularity.YEAR,
                                          DateHierarchyBuilder.Granularity.DECADE
                                          )
        date_hierarchy = self.arxaas.hierarchy(date_based, df[att].tolist())

        return date_hierarchy

    def create_interval_hierarchy(self, df, att, q):
        """"""
        bins = df[att].quantile([x / float(q) for x in range(1, q)]).tolist()
        interval_based = IntervalHierarchyBuilder()
        interval_based.add_interval(df[att].min(), bins[0], f"[{df[att].min()}-{bins[0]}[")
        for i in range(q - 2):
            interval_based.add_interval(bins[i], bins[i + 1], f"[{bins[i]}-{bins[i + 1]}[")
        interval_based.add_interval(bins[-1], df[att].max() + 1., f"[{bins[-1]}-{df[att].max() + 1}[")
        interval_based.level(0).add_group(q // 2, f"[{df[att].min()}-{bins[q//2-1]}[").add_group(q // 2, f"[{bins[q//2-1]}-{df[att].max()}[")
        interval_hierarchy = self.arxaas.hierarchy(interval_based, df[att].tolist())

        return interval_hierarchy

    def create_redaction_hierarchy(self, df, att):
        redaction_based = RedactionHierarchyBuilder()
        redaction_hierarchy = self.arxaas.hierarchy(redaction_based, df[att].tolist())

        return redaction_hierarchy

    def anonymize(self, dataset, config_attributes, config_params):
        """
        Returns anonymization result
        :param dataset: dataset to anonymize
        :return:
        """
        kanon = KAnonymity(config_params["k"])

        ldiv = []
        for att in config_attributes:
            if att["att_type"] == "sensitive":
                ldiv.append(LDiversityDistinct(config_params["l"], att["customName"]))
        anonymize_result = self.arxaas.anonymize(dataset, [kanon] + ldiv, 1)

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
