# Policy Engine

The Policy Engine provides a suite of functionality to inspect, process and use ODRL policies.

## **Main Goal/Functionalities**

Currently the following main functionalities are supported: 

* Visualising an ODRL policy to inspect it
* Validating the correctness of an ODRL policy file against the specification
* Evaluating one or more ODRL policies against a State of the World (like an event log, or a data access request)
* Generating synthetic ODRL policies, and generating synthetic States of the World about policies to be used for testing purposes.

## **How To Install**

### Requirements

Python, rdflib, pyshacl, pandas

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
* `evaluate_ODRL_from_files`
* `evaluate_ODRL_on_dataframe`
* `evaluate_ODRL_from_files_merge_policies`

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

## How to test

To test, run the `test.py` script. After the tests are run, the output of the tests will be print to console.

### How to add evaluation tests

To add an evaluation test, create the following files, where X is a filename of your choosing 
(make sure this name is unique in the folder you will copy them in):
* X.ttl
* X.csv
* X.txt (optional)

If this is a test that should result in a "valid" output place the files under `test_cases\evaluation\valid`, 
otherwise under `test_cases\evaluation\invalid`.

Tests placed here will be run automatically when `test.py` is run.

In the X.txt file you can optionally add additional information about your test:
* First line: you can add here a message describing the test, which will be printed if the test fails
* Second line: you can add here a single keyword, to group similar types of tests together. The test output will show a breakdown for each keyword.

## Contact
* Paolo Pareti p.pareti@soton.ac.uk
* Adeel Aslam A.Aslam@soton.ac.uk
* Jaime Salas J.O.Salas@soton.ac.uk