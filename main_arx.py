from pyarxaas import ARXaaS
from pyarxaas.privacy_models import KAnonymity, LDiversityDistinct
from pyarxaas import AttributeType, Dataset
from pyarxaas.hierarchy import IntervalHierarchyBuilder, DateHierarchyBuilder, RedactionHierarchyBuilder

import pandas as pd
import json
import os

import argparse


def psuedonymize_data(df, cf):
    """Remove identifying attributes from dataset

    """
    for att, config in cf.items():
        if config['att_type'] == 'identifying':
            df[att] = '*'
    return df


def clean_data(df, cf):
    """
    Define attribute dtype needed for hierarchy type
    :param df: input dataframe
    :param cf: config dict containing attribute types and hierarchies types
    :return: cleaned dataframe
    """
    for att, config in cf.items():
        if config['att_type'] == 'quasiidentifying':
            df.dropna(subset=[att], inplace=True)
            if config['hierarchy_type'] == 'interval':
                df[att] = df[att].astype(float)
            elif config['hierarchy_type'] == 'date':
                df[att] = pd.to_datetime(df[att], yearfirst=True).astype(str)
            elif config['hierarchy_type'] == 'redaction' or config['hierarchy_type'] == 'order':
                df[att] = df[att].astype(str)
    return df


def create_dataset(df):
    """
    Returns dataset from pandas df
    :param df:
    :return:
    """
    dataset = Dataset.from_pandas(df)
    return dataset


def define_attribute_type(df, dataset, cf):
    """
    Define attribute types for all attributes in dataset
    :param df: initial dataframe
    :param dataset: arx dataset
    :param cf: config dict
    :return: dataset with set attributes
    """
    for att in list(df.columns):
        dataset.set_attribute_type(AttributeType.INSENSITIVE, att)
    for att, config in cf.items():
        if config['att_type'] == "identifying":
            dataset.set_attribute_type(AttributeType.IDENTIFYING, att)
        elif config['att_type'] == "quasiidentifying":
            dataset.set_attribute_type(AttributeType.QUASIIDENTIFYING, att)
        elif config['att_type'] == "sensitive":
            dataset.set_attribute_type(AttributeType.SENSITIVE, att)
    return dataset

def create_hierarchies(df, dataset, cf, q, arxaas):
    """
    Define hierarchies and set hierachies for datatset
    :param df: initial dataframe
    :param dataset: arx dataset
    :param cf: config dict
    :param q: number of quantiles to compute
    :return: dataset with set hierarchies
    """
    hierarchies = {}
    for att, config in cf.items():
        if config["att_type"] == 'quasiidentifying':
            if config["hierarchy_type"] == 'date':
                hierarchies[att] = create_date_hierarchy(df, att, arxaas)
                pass
            elif config["hierarchy_type"] == "interval":
                hierarchies[att] = create_interval_hierarchy(df, att, q, arxaas)
            elif config["hierarchy_type"] == "redaction":
                hierarchies[att] = create_redaction_hierarchy(df, att, arxaas)
            else:
                pass
    dataset.set_hierarchies(hierarchies)
    return dataset

def create_date_hierarchy(df, att, arxaas):
    """"""
    date_based = DateHierarchyBuilder("yyyy-MM-dd", DateHierarchyBuilder.Granularity.DECADE)
    date_hierarchy = arxaas.hierarchy(date_based, df[att].tolist())

    return date_hierarchy


def create_interval_hierarchy(df, att, q, arxaas):
    """"""
    bins = df[att].quantile([x / float(q) for x in range(1, q)]).tolist()
    interval_based = IntervalHierarchyBuilder()
    interval_based.add_interval(df[att].min(), bins[0], f"[{df[att].min()}-{bins[0]}[")
    for i in range(q-2):
        interval_based.add_interval(bins[i], bins[i+1], f"[{bins[i]}-{bins[i+1]}[")
    interval_based.add_interval(bins[-1], df[att].max()+1., f"[{bins[-1]}-{df[att].max()+1}[")
    interval_based.level(0).add_group(q//2, f"low").add_group(q//2, "high")
    interval_hierarchy = arxaas.hierarchy(interval_based, df[att].tolist())

    return interval_hierarchy


def create_redaction_hierarchy(df, att, arxaas):
    redaction_based = RedactionHierarchyBuilder()
    redaction_hierarchy = arxaas.hierarchy(redaction_based, df[att].tolist)

    return redaction_hierarchy


def anonymize(dataset, cf, arxaas):
    """
    Returns anonymization result
    :param dataset: dataset to anonymize
    :return:
    """
    kanon = KAnonymity(2)

    ldiv = []
    for att, config in cf.items():
        if config["att_type"] == "sensitive":
            ldiv.append(LDiversityDistinct(2, att))
    anonymize_result = arxaas.anonymize(dataset, [kanon]+ldiv, 0.2)

    return anonymize_result


def output_dataframe(result):
    """"""
    return result.dataset.to_dataframe()


def risk_metrics(result, arxaas):
    """"""
    try:
        risk_profile = arxaas.risk_profile(result)
    except:
        risk_profile = result.risk_profile
    re_identification_risk = risk_profile.re_identification_risk_dataframe()

    return re_identification_risk


def __set_argparse():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input_path",
        type=str,
        help="path to input csv"
    )
    parser.add_argument(
        "--config",
        type=str,
        help="path to config file for anonymization: Attribute type and hierarchies for each attribute"
    )
    parser.add_argument(
        "--output_path",
        type=str,
        help="path to store anonymized csv and reidentification scores"
    )
    parser.add_argument(
        "--url",
        type=str,
        default="http://localhost:8080",
        help="url to Aaas web service"
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="pseudo",
        help= "anonymization mode : pseudo for pseudonimyzation of dataset or anon for anonymization of dataset or eval for risk evaluation"
    )
    return parser

def anonymized_metrics(result):
    """"""
    return result.anonymization_metrics.attribute_generalization, result.anonymization_metrics.privacy_models


if __name__ ==  '__main__':
    parser = __set_argparse()
    args = parser.parse_args()

    input_path = args.input_path
    config = args.config
    output_path = args.output_path
    url = args.url
    mode = args.mode

    arxaas_url = ARXaaS(url)

    input_df = pd.read_csv(input_path)
    with open(config) as cf:
        config_dict = json.load(cf)

    # Create dataset
    input_df = clean_data(input_df, config_dict)
    input_dataset = define_attribute_type(input_df, create_dataset(input_df), config_dict)
    # Evaluate risk before anonymization
    risk_before_an = risk_metrics(input_dataset, arxaas_url)
    risk_before_an.to_csv(os.path.join(output_path, "risk_before_an.csv"))
    if mode == "eval":
        pass
    # Pseudonymize
    elif mode == "pseudo":
        psuedonymize_data(input_df, config_dict).to_csv(os.path.join(output_path, "pseudo_output.csv"))
    # Anonymize
    elif mode == "anon":
        # Set config
        dataset_fin = create_hierarchies(input_df, input_dataset, config_dict, 4, arxaas_url)
        # Anonymize
        an_result = anonymize(dataset_fin, config_dict, arxaas_url)
        output_dataframe(an_result).to_csv(os.path.join(output_path, "anon_output.csv"))
        # Evaluate risk after anonymization
        risk_metrics(an_result, arxaas_url).to_csv(os.path.join(output_path, "risk_after_an.csv"))