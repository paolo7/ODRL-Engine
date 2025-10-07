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
        "xml",  # RDF/XML
        "json-ld",
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
    return None


def load(file_path):
    """
    Loads an RDF graph from the specified file path.
    Tries multiple RDF serializations and encodings until one succeeds, or
    all are exhausted.
    """

    rdf_formats = [
        "xml",       # RDF/XML
        "json-ld",   # JSON-LD
        "turtle",    # Turtle / TTL
        "nt",        # N-Triples
        "n3",        # Notation3
        "trig",      # TriG
        "trix",      # TriX
    ]

    # Try parsing with each format
    last_exception = None
    for rdf_format in rdf_formats:
        try:
            g = Graph()
            g.parse(file_path, format=rdf_format)
            if not(g is None or len(g) == 0):
                return g, rdf_format
            break
        except Exception as e:
            last_exception = e
    else:
        # If no parser worked, try again by reading file contents with encodings
        encodings = ["utf-8", "utf-16", "latin-1"]
        for enc in encodings:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    data = f.read()
                for rdf_format in rdf_formats:
                    try:
                        g = Graph()
                        g.parse(data=data, format=rdf_format)
                        if not (g is None or len(g) == 0):
                            return g, rdf_format
                        break
                    except Exception:
                        continue
                else:
                    continue
                break
            except Exception as e:
                last_exception = e
    return None