# Unit Tests

Automated tests have been created and are automatically run upon commits to the repository.

## How to Manually Test for Correctness

To manually trigger the tests, run the `test.py` script. After the tests are run, the output of the tests will be print to console. 

The main test routine checks each main feature of the evaluator against curated test cases, along tests of the validator, 
and outputs the number of 
tests passed, along with the average time for evaluation. It also tests the streaming capabilities of the evaluator
by using simulating streaming using the `evaluate_ODRL_from_files_streaming` function.

### How to Add Evaluation Tests

To add an evaluation test, create the following files, where X is a filename of your choosing 
(make sure this name is unique in the folder you will copy them in):
* `X.ttl` (a Turtle file containing a single ODRL policy)
* `X.csv` (a State of the World)
* `X.txt` (optional file, with information about the test)

If this is a test that should result in a "valid" output (if the ODRL policy in X.ttl is valid in State of the World X.csv) 
place the files under `test_cases\evaluation\valid`, 
otherwise under `test_cases\evaluation\invalid`.

Tests placed here will be run automatically when `test.py` is run.

In the X.txt file you can optionally add additional information about your test:
* First line: you can add here a message describing the test, which will be printed if the test fails
* Second line: you can add here a single keyword, to group similar types of tests together. The test output will show a breakdown for each keyword.

### How to Add Validation Tests

To add a validation test, simply place an RDF file containing one or more ODRL policies in one of the following folders.
When the tests are run, all the files in these folders will be automatically tested.

* `test_cases\validation\valid_ODRL` place valid ODRL files in this folder
* `test_cases\validation\invalid_ODRL` place invalid ODRL files in this folder

The following folders can be used to store variations of ODRL policy syntax ([compound or compact](https://www.w3.org/TR/odrl-model/#composition) policies) 
for future testing, but they are not currently being used:

* `test_cases\validation\valid_compact_ODRL` place valid ODRL files with compact policies (with rule components defined at the policy level, e.g target defined for the policy instead of within each rule) in this folder
* `test_cases\validation\valid_compound_ODRL` place valid ODRL files with compound policies (rules with multiple values for the same component, e.g. multiple actions) in this folder