from rdflib import Graph
from typing import Union
import json
import pyshacl
import os

def parse_string_to_graph(data: Union[str, bytes]) -> tuple[Graph, str] | None:
    """
    Detect the RDF serialization of a given string or bytes and return both 
    the parsed graph and the format.

    Parameters
    ----------
    data : str | bytes
        The RDF content as a string or raw bytes.

    Returns
    -------
    tuple[Graph, str] | None
        A tuple (graph, format) where:
            - graph is the rdflib.Graph containing the parsed RDF data
            - format is the name of the detected RDF serialization
        Returns None if no known format matches.
    """
    formats = [
        "json-ld",
        "xml",   # RDF/XML
        "turtle",
        "nt",
        "trig",
        "n3",
        "nquads",
    ]

    # Normalize input: ensure we always pass bytes to rdflib
    if isinstance(data, str):
        data_bytes = data.encode("utf-8")
    else:
        data_bytes = data

    for fmt in formats:
        g = Graph()
        try:
            g.parse(data=data_bytes, format=fmt)
            return g, fmt
        except Exception:
            continue

    return None, None

def validate_SHACL(graph, shacl, ont_graph=None):
    r = pyshacl.validate(graph, shacl_graph=shacl, ont_graph=ont_graph, inference='rdfs', abort_on_first=False, meta_shacl=False, debug=False)
    conforms, results_graph, results_text = r
    return conforms, results_text

def diagnose_ODRL(data: str) -> str:
    graph, format = parse_string_to_graph(data)
    errors = []
    warnings = []
    parsed_info = []
    format_report = ""
    if graph is None or len(graph) == 0:
        try:
            json.loads(data)
            errors.append("FORMAT ERROR: The provided string is plain JSON. An ODRL file should be in a graph format, like JSON-LD.")
        except (ValueError, TypeError):
            errors.append("FORMAT ERROR: The provided string is not recognised as any ODRL graph formats, such as JSON-LD, Turtle or RDF/XML. It does not appear to be plain JSON either.")
            return errors, warnings, parsed_info
    parsed_info.append("INFO: The file contains an RDF graph in the following format: "+str(format))

    # validate ODRL using SHACL
    # The SHACL shapes are based on https://github.com/woutslabbinck/ODRL-shape
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
        parsed_info.append("SHACL validation report : \n" + str(report)+"\n")
    return errors, warnings, parsed_info

def generate_ODRL_diagnostic_report(data: str) -> str:
    errors, warnings, parsed_info = diagnose_ODRL(data)
    print("Analysing the input string for ODRL compliance:")
    for error in errors:
        print(error)
    for warning in warnings:
        print(warning)
    for info in parsed_info:
        print(info)
