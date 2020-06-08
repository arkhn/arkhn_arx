# pyarxaas

arkhn_arx is a module for dataset pseudonymization or anonymization

## Install

```
pip install arkhn_arx
```

## Connection to ARXaas
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

### Arguments

- input dataframe to anonymize
- configuration file : json file containing anonymization parameters
```
config_dict = {"anonymization":{"type": 2, "k":2, "l":2},
                "attributes":[
                            {"officialName":"att_1",
                             "customName":"att_1",
                             "att_type":"att_type"
                                "hierarchy_type":"hierarchy_type"}]
                }
```

- URL link to ARXaaS service : if ARXaas service is running locally URL is : "http://localhost:8080"


## Example

You can test this module using the example.py script