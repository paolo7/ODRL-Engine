import sys
import os

# Add parent folder to Python path
parent_folder = os.path.abspath(os.path.join(os.getcwd(), ".."))
if parent_folder not in sys.path:
    sys.path.insert(0, parent_folder)

import rdf_utils
import setup_colab
from rdflib import Graph, Namespace, RDF, RDFS, SKOS
from IPython.display import display, HTML
from google.colab import files

fn = None
policy_content = None
g = None
format = None

# --- Ontologies ---
ODRL = rdflib.Namespace("http://www.w3.org/ns/odrl/2/")

odrl_ontology = rdflib.Graph()
odrl_ontology.parse("https://www.w3.org/ns/odrl/2/ODRL22.ttl", format="turtle")

odrl_dpv_ontology = rdflib.Graph()
odrl_dpv_ontology.parse("https://raw.githubusercontent.com/EU-UPCAST/ODRL-DPV-Ontology/refs/heads/main/ODRL_DPV.rdf", format="xml")


# Collect all properties to use to expand the tree
allowed_relations = set(odrl_ontology.subjects(RDF.type, RDF.Property))
allowed_relations.add(ODRL.source)
allowed_relations.add(RDF.value)
allowed_relations.add(RDF.type)
allowed_relations.add(RDF.rest)
allowed_relations.add(RDF.first)

# --- Helper functions ---

LEVEL_COLORS = {
    1: "white",           # top-level policy
    2: "#cce5ff",         # pastel blue
    3: "#d4edda",         # light green
    4: "#ffe5b4",         # light orange
}

INDENT_PER_LEVEL = 8

def get_label(node):
    """Get a human-readable label for a node if available,
       checking policy graph, ODRL ontology, and DPV ontology."""
    if isinstance(node, rdflib.term.Literal):
        return str(node)

    # --- check in main policy graph ---
    for lbl in g.objects(node, RDFS.label):
        return str(lbl)
    for lbl in g.objects(node, rdflib.URIRef("http://purl.org/dc/terms/title")):
        return str(lbl)
    for lbl in g.objects(node, SKOS.prefLabel):
        return str(lbl)

    # --- check in DPV/ODRL ontologies ---
    for lbl in odrl_dpv_ontology.objects(node, RDFS.label):
        return str(lbl)
    for lbl in odrl_dpv_ontology.objects(node, rdflib.URIRef("http://purl.org/dc/terms/title")):
        return str(lbl)
    for lbl in odrl_dpv_ontology.objects(node, SKOS.prefLabel):
        return str(lbl)

    # optionally: check in odrl_ontology too if you load it separately
    for lbl in odrl_ontology.objects(node, RDFS.label):
        return str(lbl)
    for lbl in odrl_ontology.objects(node, SKOS.prefLabel):
        return str(lbl)

    # fallback: use last part of URI
    if isinstance(node, rdflib.term.URIRef):
        return node.split("/")[-1]
    return str(node)

def build_html_tree(node, visited=None, level=1, parent_predicate=None):
    if visited is None:
        visited = set()
    visited.add(node)

    bg_color = LEVEL_COLORS.get(level, "white")
    indent = level * INDENT_PER_LEVEL

    # --- Detect if this node is the head of an RDF list ---
    if (node, RDF.first, None) in g:
        # It's a list head, iterate through list
        items_html = []
        current = node
        while current != RDF.nil:
            first_objs = list(g.objects(current, RDF.first))
            if first_objs:
                first_node = first_objs[0]
                # render first_node recursively, but mark as list item
                items_html.append(f"<li>{build_html_tree(first_node, visited.copy(), level=level+1, parent_predicate=RDF.first)}</li>")
            rest_objs = list(g.objects(current, RDF.rest))
            current = rest_objs[0] if rest_objs else RDF.nil
        return f'<ul style="margin-left:{indent}px;">{"".join(items_html)}</ul>'

    children_html = ""
    for p, o in g.predicate_objects(node):
        if p not in allowed_relations:
            continue
        pname = get_label(p)
        label_text = f"{pname}: {get_label(o)}"

        is_expandable = (o, None, None) in g
        border_style = "1px solid black" if bg_color == "white" and is_expandable else "none"

        if is_expandable:
            sub_html = build_html_tree(o, visited.copy(), level=level+1, parent_predicate=p)
            children_html += f'''
            <details style="
                background-color:{bg_color};
                padding:6px;
                margin-left:{indent}px;
                margin-bottom:4px;
                border:{border_style};
                border-radius:3px;">
                <summary>{label_text}</summary>
                {sub_html}
            </details>
            '''
        else:
            children_html += f'''
            <div style="
                background-color:{bg_color};
                padding:6px;
                margin-left:{indent}px;
                margin-bottom:4px;
                border:{border_style};
                border-radius:3px;">
                {label_text}
            </div>
            '''

    if not children_html:
        border_style = "1px solid black" if bg_color == "white" else "none"
        return f'''
        <div style="
            background-color:{bg_color};
            padding:6px;
            margin-left:{indent}px;
            margin-bottom:4px;
            border:{border_style};
            border-radius:3px;">
            {get_label(node)}
        </div>
        '''

    return children_html


def explore_policies_html():
    fn = setup_colab.UploadState.filename
    policy_content = setup_colab.UploadState.content.decode('utf-8')
    g, format = rdf_utils.parse_string_to_graph(policy_content)

    policy_types = [ODRL.Policy, ODRL.Set, ODRL.Agreement, ODRL.Offer]
    policy_nodes = []
    for t in policy_types:
        policy_nodes.extend(list(g.subjects(RDF.type, t)))

    for pol in policy_nodes:
        # Add the policy IRI at the top (without a black border)
        policy_iri_html = f'''
        <div style="
            padding:4px 0px;
            font-weight:bold;
            margin-bottom:6px;">
            Policy: {pol}
        </div>
        '''
        # Build the tree for this policy
        policy_tree_html = policy_iri_html + build_html_tree(pol, level=1)

        # Wrap each policy in its own top-level box
        top_box_html = f'''
        <div style="
            padding:10px;
            border:2px solid black;
            border-radius:5px;
            background-color:white;
            margin-bottom:10px;">
            {policy_tree_html}
        </div>
        '''
        display(HTML(top_box_html))

