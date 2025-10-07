import rdflib
import pyshacl

import validate

validate.generate_ODRL_diagnostic_report("example_policies/example_valid.json")

validate.generate_ODRL_diagnostic_report("example_policies/example_invalid.json")
