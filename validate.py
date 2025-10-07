from rdflib import Graph
from typing import Union
import json
import pyshacl
import os
import rdf_utils


def validate_SHACL(graph, shacl, ont_graph=None):
    r = pyshacl.validate(graph, shacl_graph=shacl, ont_graph=ont_graph, inference='rdfs', abort_on_first=False, meta_shacl=False, debug=False)
    conforms, results_graph, results_text = r
    return conforms, results_text

def diagnose_ODRL(filepath) -> str:
    graph, format = rdf_utils.load(filepath)
    errors = []
    warnings = []
    parsed_info = []
    format_report = ""
    if graph is None or len(graph) == 0:
        try:
            json.load(filepath)
            errors.append("FORMAT ERROR: The provided string is plain JSON. An ODRL file should be in a graph format, like JSON-LD.")
        except (ValueError, TypeError):
            errors.append("FORMAT ERROR: The provided string is not recognised as any ODRL graph formats, such as JSON-LD, Turtle or RDF/XML. It does not appear to be plain JSON either.")
            return errors, warnings, parsed_info
    parsed_info.append("INFO: The file contains an RDF graph in the following format: "+str(format))

    # validate ODRL using SHACL
    # The SHACL shapes graph used is derived from the one at https://github.com/woutslabbinck/ODRL-shape
    # https://github.com/woutslabbinck/ODRL-shape/blob/main/odrl-shacl.ttl
    # They are extended to allow for lists of IRIs in the right operands

    shacl_file = os.path.join("SHACL", "odrl-shacl.ttl")
    ont_file = os.path.join("ODRL", "ODRL22.ttl")
    ont_graph = Graph().parse(ont_file, format="turtle")
    conforms, report = validate_SHACL(graph, shacl_file, ont_graph=ont_graph)

    if conforms :
        parsed_info.append("SHACL validation check passed")
    else :
        parsed_info.append("\nSHACL validation failed")
        parsed_info.append("SHACL validation report : \n" + str(report))
    return errors, warnings, parsed_info

def generate_ODRL_diagnostic_report(filepath: str) -> str:
    errors, warnings, parsed_info = diagnose_ODRL(filepath)
    print("REPORT START\nAnalysing the file "+str(filepath)+" for ODRL compliance:")
    for error in errors:
        print(error)
    for warning in warnings:
        print(warning)
    for info in parsed_info:
        print(info)
    print("REPORT END\n")
