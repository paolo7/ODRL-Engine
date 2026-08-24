# Policy Engine and Evaluator

The Policy Engine provides a suite of functionality to inspect, process and use ODRL policies, including the OVAL Policy Evaluator.

You can access a live demo of these functionalities on [DIPS](https://dips.soton.ac.uk/odrl-engine/odrl-engine-dashboard/). 
An older [Google Colab interface](https://colab.research.google.com/drive/19t7xmiLkL1RW3s77_HkhysE04W4DUNPc#scrollTo=yK6I-AKSrVZ5) is also available, but it won't be actively maintained anymore.

This repository includes a [video demonstration](resources/Policy_Evaluation_Demo_July_2026.mp4) of the OVAL Policy Evaluator using a [sample policy](test_cases/evaluation/invalid/constraints1.ttl) and [state of the world](test_cases/evaluation/invalid/constraints1.csv).

## **Main Goal/Functionalities**

Currently the following main functionalities are supported: 

* Visualising an ODRL policy to inspect it
* Validating the correctness of an ODRL policy file against the specification
* Evaluating one or more ODRL policies against a State of the World (like an event log, or a data access request)
* Generating synthetic ODRL policies, and generating synthetic States of the World about policies to be used for testing purposes.

## **How To Install With Docker**

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
* Navigate to http://localhost:8031/evaluator/ to access the evaluator demo
* Navigate to http://localhost:8031/validator/ to access the validator demo
* Navigate to http://localhost:8031/odrl-generator/ to access the ODRL generator demo 
* Navigate to http://localhost:8031/sotw-generator/ to access the State of the World generator demo 
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

## **How To Install Without Docker**

### Requirements

Python, rdflib, pyshacl, pandas, matplotlib

## Usage

### Jupiter Notebook Interface

You can easily test the functions of this Policy Engine using the Jupiter Notebook `colab_notebook.ipynb`. This notebook is compatible with Google Colab, and contains instructions on how to use it. 

### Programmatic use

Currently the Policy Engine can be inported as a Python library to use its main functions.

The main functions can be found in the following files (more details in the code):

`validate.py`
* `validate_SHACL`
* `get_ODRL_macro_statistics`
* `describe_ODRL_statistics`
* `diagnose_ODRL`
* `generate_ODRL_diagnostic_report`

`rdf_utils.py`
* `parse_string_to_graph`
* `load`

`ODRL_Evaluator.py`
* `evaluate_ODRL_on_dataframe` core ODRL evaluation function, which takes as inputs an ODRL policy, a state of the world/event stream batch/access request, and optionally a previous saved state of the evaluation json object (this last parameter is only needed in online/stream evaluation) 
* `evaluate_ODRL_from_files` wrapper of the function above, which loads the inputs from files instead of using in-memory objects
* `evaluate_ODRL_from_files_merge_policies` utility function that allows for the processing of multiple policies at once, by merging their rules into a single policy
* `evaluate_ODRL_from_files_streaming` variant test function, that simulates streaming of events by breaking down a single large state of the world into multiple batches, by default containing 1 event each, and evaluates them sequentially 

`ODRL_generator.py`
* `generate_ODRL`

`SotW_generator.py`
* `extract_features_list_from_policy`
* `extract_rule_list`
* `extract_rule_list_from_policy`
* `extract_rule_list_from_policy_from_file`
* `generate_pd_state_of_the_world_from_policies`
* `generate_state_of_the_world_from_policies`
* `extract_features_list_from_policy_from_file`
* `generate_state_of_the_world_from_policies_from_file`

## Additional Documentation

* [Unit Tests](documentation/unit_tests.md)
* [Experimental Evaluation of the OVAL ODRL Evaluator](documentation/experiments.md)
* [Internal JSON Data Model](documentation/internal_data_model.md)

## Contact
* Paolo Pareti p.pareti@soton.ac.uk
* Adeel Aslam A.Aslam@soton.ac.uk
* Jaime Salas J.O.Salas@soton.ac.uk