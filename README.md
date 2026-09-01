# ODRL Engine and OVAL Evaluator

The ODRL Engine provides an integrated suite of functionalities to inspect, process and use ODRL policies. 
The core components of the ODRL Engine are:
* __The OVAL Policy Evaluator__ A comprehensive and semantically-grounded ODRL Evaluator that supports both the Monitoring 
and the Access Control scenarios and includes reasoning.
  * In __Monitoring Mode__ it can parse CSV files 
containing a log of events and compute whether such events comply or not with a given ODRL policy. A list of supported 
features can be found [here](documentation/evaluator_feature_support.md). 
  * With its __Access Control Mode__, it can ingest an access 
request and a policy and provides a report, based on configurable semantics, on whether the access request can be granted, and if yes, under which conditions.
* __The DIPS ODRL Validator__ A utility validator that inspects ODRL files to determine if they are correct RDF files 
containing syntactically correct ODRL files, using SHACL shapes for validation. Generates policy macro-statistics (e.g. 
number and types of rules) if the ODRL file is valid, or else generates a SHACL validation report showing the validation 
errors.
* __The DIPS ODRL Generator__ A generator of synthetic ODRL policies that can generate ODRL policies of any size based 
on a large amount of configuration options.
* __The DIPS State of the World Generator__ A generator capable of creating synthetic logs of events of any size based 
on a specific ODRL policy passed as input. The resulting State of the World objects, along with the policy used to 
generate them, can be evaluated by the OVAL Evaluator.

For info or queries please contact Paolo Pareti p.pareti@soton.ac.uk

### Try the ODRL Engine Online

You can access a live demo of these functionalities on [DIPS](https://dips.soton.ac.uk/odrl-engine/odrl-engine-dashboard/). Selected functionalities are also available at a 
[Swagger API endpoint](https://dips.soton.ac.uk/odrl-engine/api/docs)

This repository includes a [video demonstration](resources/Policy_Evaluation_Demo_July_2026.mp4) of the OVAL Policy Evaluator using a [sample policy](test_cases/evaluation/invalid/constraints1.ttl) and [state of the world](test_cases/evaluation/invalid/constraints1.csv).

An older [Google Colab interface](https://colab.research.google.com/drive/19t7xmiLkL1RW3s77_HkhysE04W4DUNPc#scrollTo=yK6I-AKSrVZ5) is also available, but it won't be actively maintained anymore.

## Installation Instructions

This project comes with a docker image which you can start on port 8031 (or choose another port by modifying `docker-compose.yml`).

The following environment variables can be configured in the `.env` file (see the `.env.example` file). They don't need to be set on a test deployment on localhost. 
* ODRL_BASE_PATH: internal subpath your container's own nginx listens on — set this only if the upstream/server nginx forwards requests to your container WITHOUT stripping the subpath prefix (leave unset/empty if it already strips it, as at dips.soton.ac.uk).
* ODRL_EXTERNAL_PREFIX: the subpath the API is exposed at from the *browser's* point of view (e.g. "odrl-engine") — used only so FastAPI generates correct absolute URLs (/docs, /openapi.json, redirects); does not affect internal routing.

Streamlit apps found in the `apps` subfolder will be automatically loaded when the image is generated. For example, the app `odrl_generator.py` can be accessed here http://localhost:8031/odrl-generator/ (any underscore is turned into a dash in the path).

### Instructions

1. Make sure you have Docker installed and running
2. Go to the the root directory of this project and run command `docker compose up -d`
3. Wait for the image to be created
4. Open the dashboard that gives you access to all the apps here: http://localhost:8031/odrl-engine-dashboard/ or access the Swagger API here http://localhost:8031/api/docs

You can also access individual apps here:
* Navigate to http://localhost:8031/evaluator-for-monitoring/ to access the evaluator for monitoring
* Navigate to http://localhost:8031/evaluator-of-access-requests/ to access the evaluator for monitoring demo
* Navigate to http://localhost:8031/validator/ to access the validator
* Navigate to http://localhost:8031/odrl-generator/ to access the ODRL generator
* Navigate to http://localhost:8031/sotw-generator/ to access the State of the World generator
* Navigate to http://localhost:8031/api/docs to access the evaluation API swagger interface

You can test these functionalities with the sample ODRL policies and states of the world available [here](https://github.com/DIPS-Tools/ODRL-Engine/tree/main/test_cases/evaluation/valid).

#### Additional Configuration

You can set usage limit for the API in the .env file with variables:
* ODRL_MAX_BODY_SIZE_MB
* ODRL_EVAL_TIMEOUT_SECONDS
* ODRL_RATE_LIMIT_RPS
These limit the stramlit app:
* ODRL_STREAMLIT_MAX_BODY_SIZE_MB
* ODRL_STREAMLIT_WS_TIMEOUT_SECONDS
* ODRL_STREAMLIT_MAX_CONN_PER_IP

### Fast API Endpoint

When deployed, the ODRL Engine provides selected functionalities through a FastAPI Endpoint.
A demo  endpoint is available [here](https://dips.soton.ac.uk/odrl-engine/api/docs). 
Currently, the functionalities exposed are the following.

| Method | Endpoint                   | Description                                                                                                                                                                                                             |
|--------|----------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `POST` | `/evaluate_policy_on_sotw` | Evaluate whether a log of events (State of the World) is compliant with a Policy                                                                                                                                        |
| `POST` | `/evaluate_access_request` | Evaluate if an Access Request complies with a Policy                                                                                                                                                                    |
| `POST` | `/validate_ODRL`           | Validate an ODRL document to find out if 1) it contains valid RDF, 2) if it contains any ODRL policy and 3) if the ODRL policies are valid with respect to the specification.                                           |
| `POST` | `/get_policy_features`     | Utility function to extract a list of policy features (Left Operands) used in a policy file. These are the features that a State of the World or Access Request object might need to specify to be correctly evaluated. |


### Manual Installation

You can also use the ODRL Engine as a library of functions. 

#### Requirements

* Python (tested on version 3.12) 
* The python libraries defined in `requirements.txt`

#### Usage

Please see the [Python Functions](documentation/python_interface.md) document for details of the main functions you might
want to use.

## User Guides

* [User Guide for the Evaluator](documentation/user_guides/evaluator/user_guide_evaluator.md)
* [User Guide for the Validator](documentation/user_guides/validator/user_guide_validator.md)

## Additional Documentation

* [Unit Tests](documentation/unit_tests.md)
* [Experimental Evaluation of the OVAL ODRL Evaluator](documentation/experiments.md)
* [Internal JSON Data Model](documentation/internal_data_model.md)
* [Python Functions](documentation/python_interface.md)
* [Evaluator Feature Support](documentation/evaluator_feature_support.md)

## Contributors
* Paolo Pareti p.pareti@soton.ac.uk
* Adeel Aslam A.Aslam@soton.ac.uk
* Jaime Salas J.O.Salas@soton.ac.uk