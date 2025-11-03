from google.colab import files
from rdflib import Graph, BNode
import rdf_utils
import codecs

def clean_file(filename: str) -> bytes:
    """Read a file as bytes and strip UTF-8 BOM if present."""
    with open(filename, "rb") as f:
        content = f.read()
    if content.startswith(codecs.BOM_UTF8):
        content = content[len(codecs.BOM_UTF8):]
    return content

def triple_in_graph(triple, graph):
    """Check if triple is in graph, treating blank nodes as wildcards."""
    s, p, o = triple
    for (s2, p2, o2) in graph:
        if (isinstance(s, BNode) or s == s2) and \
           (isinstance(p, BNode) or p == p2) and \
           (isinstance(o, BNode) or o == o2):
            return True
    return False

def compare_rdf_files():
    """Main function to compare two RDF files uploaded by the user."""

    # Prompt user to upload two RDF files
    print("Please upload the first RDF file:")
    first_upload = files.upload()
    first_filename = next(iter(first_upload))

    print("Please upload the second RDF file:")
    second_upload = files.upload()
    second_filename = next(iter(second_upload))

    # Read and clean file contents as bytes
    data1 = clean_file(first_filename)
    data2 = clean_file(second_filename)

    # Parse to graphs
    graph1, _ = rdf_utils.parse_string_to_graph(data1)
    graph2, _ = rdf_utils.parse_string_to_graph(data2)

    # Compare graphs with blank nodes as wildcards
    only_in_first = [t for t in graph1 if not triple_in_graph(t, graph2)]
    only_in_second = [t for t in graph2 if not triple_in_graph(t, graph1)]

    if not only_in_first and not only_in_second:
        print("✅ Both RDF files contain the same data (treating blank nodes as wildcards).")
    else:
        if only_in_first:
            print("\nTriples only in first file:")
            for triple in only_in_first:
                print(triple)
        if only_in_second:
            print("\nTriples only in second file:")
            for triple in only_in_second:
                print(triple)
