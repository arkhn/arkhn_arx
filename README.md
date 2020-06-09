# pyarxaas

arkhn_arx is a module for dataset pseudonymization or anonymization

## Install

```
pip install arkhn_arx
```

## Connection to ARXaas service
This module uses https://github.com/navikt/arxaas service. 

To run this service locally : 
1. Make sure Docker Desktop is running
2. Pull the Docker image
```
docker pull navikt/arxaas
```

3. Run the Docker image

```
docker run -p 8080:8080 navikt/arxaas
```




## Anonymization

### Principle
This module can be used in 3 modes : to evaluate reidentification risk of a dataset, pseudonymize dataset or anonymize dataset.
Anonymization is performed using k-anonymity and l-diversity algorithms. 
- k-anonymity ensures that the information for each person contained in the release cannot be distinguished from at least k-1 individuals whose information also appears in the release (defining a k-anonymity group).
- l-diversity ensures that sensitive attributes are well represented (at least l distinct values) in each k-anonymity group

### Arguments

- `input_dataframe` to anonymize
- `configuration_file` : json file containing anonymization parameters
```
config_dict = {"anonymization":{"type": 2, "k":2, "l":2},
                "attributes":[
                            {"customName":"att_1",
                             "att_type":"att_type"
                             "hierarchy_type":"hierarchy_type"}, 
                            ]
                }
```
- Anonymization parameters: 
    - type : 0 returns risk metrics for initial dataset, 1 pseudonymize dataset, 2 anonymize dataset
    - k : parameter for K-anonymity
    - l : parameter for l-diversity
- Attributes parameters: for each attribute gives : 
    - customName : column name of attribute in dataframe
    - att_type : attribute type for anonymization, can be:
        - `"insensitive"` : will be kept unmodified
        - `"sensitive"` : will be kept as-is but they can be protected using privacy models, such as t-closeness or l-diversity
        - `"quasiidentifying"` : will be transformed using hierarchies
        - `"identifying""` : will be removed from the dataset
    - hierarchy_type : type of hierarchy to apply to attribute for anonymization, can be: 
        - `"interval"` : can be used for variables with a ratio scale, intervals are defined using attribute quantiles
        - `"date"` : can be used for dates
        - `"redaction"` :  can be used for a broad spectrum of attributes, masking parts of variables
        - `"order"` : NOT IMPLEMENTED can be used for variables with an ordinal scale, defining ordered group of variables 

- `URL_link` to ARXaaS service : if ARXaas service is running locally URL is : "http://localhost:8080"


## Example

You can test this module using the example.py script