# Python Functions 


The ODRL Engine can be imported as a Python library to use its main functions.

The main functions can be found in the following files (more details in the code):

#### Validation Functions
`validate.py`
* `validate_ODRL` validates an rdflib graph object against SHACL shapes to determine whether valid ODRL policies are 
contained in it. Returns a validation report, including policy macro statistics, if valid, or a SHACL violations report
if invalid.
* `validate_ODRL_from_file` wrapper of the above, taking an RDF file as input
* `validate_ODRL_from_string` wrapper of the above, taking a string representation of an RDF graph as input

#### Utility Functions

`rdf_utils.py`
* `parse_string_to_graph` tries to load a string representation of an RDF graph (in any serialisation) into an rdflib graph object
* `load` tries to load an RDF file (in any serialisation) into an rdflib graph object
* `extract_features_list_from_policy` extract the components and left operands in an rdflib graph object containing an ODRL policy
* `extract_rule_list_from_policy_from_file` wrapper of the above, taking an RDF file as input
* `extract_rule_list_from_policy` converts a policy in rdflib graph format into an equivalent (for the purpose of evaluation)
JSON object representing its set of compliance conditions. More details on this [JSON Data Model here](../documentation/internal_data_model.md)
* `extract_features_list_from_policy_from_file` wrapper of the above, taking an RDF file as input

#### Evaluation Functions

`ODRL_Evaluator.py`
* `evaluate_ODRL_on_dataframe` core ODRL evaluation function, which takes as inputs an ODRL policy, a state of the world/event stream batch/access request, and optionally a previous saved state of the evaluation json object (this last parameter is only needed in online/stream evaluation) 
* `evaluate_ODRL_from_files` wrapper of the function above, which loads the inputs from files instead of using in-memory objects
* `evaluate_ODRL_from_strings` another wrapper function that accepts string representations of a policy RDF graph and 
a state of the world object as inputs
* `evaluate_ODRL_from_files_merge_policies` utility function that allows for the processing of multiple policies at once, by merging their rules into a single policy
* `evaluate_ODRL_from_files_streaming` variant test function, that simulates streaming of events by breaking down a single large state of the world into multiple batches, by default containing 1 event each, and evaluates them sequentially 

#### ODRL Generation Functions

`ODRL_generator.py`
* `generate_ODRL`

#### State of the World Generation Functions

`SotW_generator.py`
* `generate_pd_state_of_the_world_from_policies`
* `generate_state_of_the_world_from_policies`
* `generate_state_of_the_world_from_policies_from_file`