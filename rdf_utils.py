import rdflib
from rdflib import Graph
from rdflib.namespace import RDF
from rdflib.collection import Collection
from typing import Union
import json
import pyshacl
import os, sys

import policy_normalisation_comparison.GraphParser

ODRL = rdflib.Namespace("http://www.w3.org/ns/odrl/2/")

logic_predicates = [
            rdflib.URIRef("http://www.w3.org/ns/odrl/2/and"),
            rdflib.URIRef("http://www.w3.org/ns/odrl/2/or"),
            rdflib.URIRef("http://www.w3.org/ns/odrl/2/xone"),
            rdflib.URIRef("http://www.w3.org/ns/odrl/2/andSequence"),
        ]
SUBRULE_PREDICATES = (
    ODRL.duty,
    ODRL.consequence,
    ODRL.remedy,
)

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


def load_normalise(file_path):
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
                graph_parser = policy_normalisation_comparison.GraphParser.GraphParser(g)
                normal_graph = graph_parser.parse().normalise().to_rdflib_graph()
                return normal_graph, rdf_format
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
                            graph_parser = policy_normalisation_comparison.GraphParser.GraphParser(g)
                            normal_graph = graph_parser.parse().normalise().to_rdflib_graph()
                            return normal_graph, rdf_format
                        break
                    except Exception:
                        continue
                else:
                    continue
                break
            except Exception as e:
                last_exception = e
    return None

base_features = [
    {"iri": "http://www.w3.org/ns/odrl/2/dateTime",
     "type": "http://www.w3.org/2001/XMLSchema#dateTime"},
    {"iri": "http://www.w3.org/ns/odrl/2/Party",
     "type": "http://www.w3.org/ns/shacl#IRI"},
    {"iri": "http://www.w3.org/ns/odrl/2/Action",
     "type": "http://www.w3.org/ns/shacl#IRI"},
    {"iri": "http://www.w3.org/ns/odrl/2/Asset",
     "type": "http://www.w3.org/ns/shacl#IRI"},
]

policy_predicates = {ODRL.permission, ODRL.prohibition, ODRL.obligation}

refinement_contexts_incoming = {
    "http://www.w3.org/ns/odrl/2/Party": ODRL.assignee,  # Party if something has an :assignee -> node
    "http://www.w3.org/ns/odrl/2/Action": ODRL.action,  # Action if something has an :action -> node
    "http://www.w3.org/ns/odrl/2/Asset": ODRL.target,  # Asset if something has a :target -> node
}

# returns an alphabetically ordered list of unique features (left operands) from the policies
# refinements of assignee/action/target have Party/Action/Asset prepended to the IRI and space separated, to distinguish them
# from constraints.
# all lists contain datetime, party, action and asset by default
def extract_features_list_from_policy(odrl_graph: rdflib.Graph):

    features = list(base_features)
    seen_iris = {f["iri"] for f in base_features}

    def add_feature(iri):
        if iri not in seen_iris:
            features.append({
                "iri": iri,
                "type": "http://www.w3.org/ns/shacl#Literal"
            })
            seen_iris.add(iri)

    def process_constraint(constraint, prefix=None):
        """
        Recursively process a constraint or logic constraint.
        """

        # -------------------------
        # Simple constraint
        # -------------------------
        left = next(odrl_graph.objects(constraint, ODRL.leftOperand), None)

        if left is not None:
            iri = str(left)
            if prefix:
                iri = f"{prefix} {iri}"
            add_feature(iri)
            return

        # -------------------------
        # Logic constraint
        # -------------------------
#       for logic_pred in LOGIC_PREDICATES:
#           for list_node in odrl_graph.objects(constraint, logic_pred):
#
#                try:
#                    members = Collection(odrl_graph, list_node)
#                except Exception:
#                    continue#
#
#                for member in members:
#                    process_constraint(member, prefix)
        for logic_pred in logic_predicates:

            children = list(odrl_graph.objects(constraint, logic_pred))

            for child in children:

                # RDF Collection?
                if (child, RDF.first, None) in odrl_graph:
                    try:
                        for member in Collection(odrl_graph, child):
                            process_constraint(member, prefix)
                    except Exception:
                        pass

                # Otherwise it is already an individual constraint
                else:
                    process_constraint(child, prefix)

    # Predicates used to decide top-level policy-like nodes
    policy_predicates = {ODRL.permission, ODRL.prohibition, ODRL.obligation}

    # Mapping for refinement context detection:
    # key = label to use as Y, value = tuple(incoming predicate to detect that context)

    # -------------------------
    # Traverse every policy rule
    # -------------------------

    def process_rule(rule):
        # Direct constraints
        for constraint in odrl_graph.objects(rule, ODRL.constraint):
            process_constraint(constraint)

        # Refinements on rule-level Party / Action / Asset
        for prefix, incoming_pred in refinement_contexts_incoming.items():
            for component in odrl_graph.objects(rule, incoming_pred):
                for refinement in odrl_graph.objects(component, ODRL.refinement):
                    process_constraint(refinement, prefix)

        # Recursively process duties, consequences and remedies
        for predicate in SUBRULE_PREDICATES:
            for subrule in odrl_graph.objects(rule, predicate):
                process_rule(subrule)

    for rule in set(
            r
            for pred in policy_predicates
            for policy in odrl_graph.subjects(pred)
            for r in odrl_graph.objects(policy, pred)
    ):
        process_rule(rule)

    features = sorted(features, key=lambda f: f["iri"])
    return features

def extract_features_list_from_string(graph_string):
    graph, _ = parse_string_to_graph(
        graph_string
    )
    return extract_features_list_from_policy(graph)

def extract_features_list_from_policy_from_file(file_path):
    g = load(file_path)[0]
    return extract_features_list_from_policy(g)


def extract_rule_list(
    odrl_graph,
    rule_node,
    policy_target=None,
    policy_assignee=None,
    policy_action=None
):
    """
    Extract all components (action, target, assignee) and constraints/refinements
    of a rule, returning triplets <A, B, C>.
    Handles nested refinements inside components.
    """
    triplets = []

    # Map ODRL operators to standard symbols
    # This may be unnecessary. We could keep the original IRIs and handle them in the evaluator.
    operator_map = {
        ODRL.eq: "=",
        ODRL.neq: "!=",
        ODRL.lt: "<",
        ODRL.gt: ">",
        ODRL.lteq: "<=",
        ODRL.gteq: ">=",
        # We need to extract set operators, membership operators, etc.
    }

    # Helper to extract values from a node (URI, literal, or complex node with rdf:value/odrl:source)
    def extract_values(node):
        if isinstance(node, rdflib.term.URIRef) or isinstance(node, rdflib.term.Literal):
            return [str(node)]
        values = list(odrl_graph.objects(node, RDF.value)) + list(odrl_graph.objects(node, ODRL.source))
        return [str(v) for v in values] if values else [str(node)]

    def append_triplet(node, prefix=None):
        """
        Handles both simple constraints and logical constraints recursively.
        Returns either:
          - a triplet [left, op, right]
          - or a logic structure [logic_operator, [sub_constraints]]
        """

        # --- 1. SIMPLE CONSTRAINT ---
        lefts = list(odrl_graph.objects(node, ODRL.leftOperand))
        if lefts:
            rights = list(odrl_graph.objects(node, ODRL.rightOperand))
            operators = list(odrl_graph.objects(node, ODRL.operator))

            left = f"{prefix} {str(lefts[0])}" if prefix else str(lefts[0])
            op = str(operators[0]) if operators else ""
            right = str(rights[0]) if rights else ""

            return [left, op, right]

        # --- 2. LOGIC CONSTRAINT ---

        for logic_op in logic_predicates:
            for collection_node in odrl_graph.objects(node, logic_op):
                # RDF list → Python list
                try:
                    items = list(Collection(odrl_graph, collection_node))
                except Exception:
                    items = []

                sub_constraints = []

                for item in items:
                    result = append_triplet(item, prefix)
                    if result:
                        sub_constraints.append(result)

                return [str(logic_op), sub_constraints]

        return None

    # --- 1. Extract Action, Asset, Party components ---
    #
    # Rule-level values take precedence.
    # If a component is not defined at rule level, fall back to the
    # corresponding value defined directly on the policy.

    component_policy_fallbacks = {
        "http://www.w3.org/ns/odrl/2/Action": policy_action,
        "http://www.w3.org/ns/odrl/2/Asset": policy_target,
        "http://www.w3.org/ns/odrl/2/Party": policy_assignee,
    }

    for component_type, predicate in refinement_contexts_incoming.items():

        rule_components = list(odrl_graph.objects(rule_node, predicate))

        if rule_components:
            # Rule-level component exists: use it.
            for comp_node in rule_components:
                for val in extract_values(comp_node):
                    triplets.append([
                        component_type,
                        "http://www.w3.org/ns/odrl/2/eq",
                        val
                    ])

                # Nested refinements inside component
                for refinement in odrl_graph.objects(comp_node, ODRL.refinement):
                    result = append_triplet(
                        refinement,
                        prefix=component_type
                    )
                    if result:
                        triplets.append(result)

        else:
            # No rule-level component: fall back to policy-level value.
            policy_value = component_policy_fallbacks.get(component_type)

            if policy_value is not None:
                triplets.append([
                    component_type,
                    "http://www.w3.org/ns/odrl/2/eq",
                    policy_value
                ])

    # --- 2. Extract constraints directly attached to the rule ---
    for constraint in odrl_graph.objects(rule_node, ODRL.constraint):
        #append_triplet(constraint)
        result = append_triplet(constraint)
        if result:
            triplets.append(result)

        # --- 3. Handle refinements attached to this constraint --- TODO: this part might not be needed
        for refinement in odrl_graph.subjects(predicate=ODRL.refinement, object=constraint):
            for iri_prefix, incoming_pred in refinement_contexts_incoming.items():
                if any(odrl_graph.subjects(predicate=incoming_pred, object=refinement)):
                    #append_triplet(constraint, prefix=iri_prefix)
                    result = append_triplet(constraint, prefix=iri_prefix)
                    if result:
                        triplets.append(result)

    def make_hashable(x):
        if isinstance(x, list):
            return tuple(make_hashable(i) for i in x)
        return x

    # Deduplicate triplets by all three fields
    seen = set()
    unique_triplets = []
    for t in triplets:
        key = make_hashable(t)
        if key not in seen:
            seen.add(key)
            unique_triplets.append(t)

    return unique_triplets

def extract_rule_list_from_policy(odrl_graph: rdflib.Graph):
    policy_list = []

    # --------------------------------------------------------
    # ODRL conflict strategy
    #
    # -1 = permission takes precedence
    #  0 = no conflict strategy / invalid / unsupported
    #  1 = prohibition takes precedence
    # --------------------------------------------------------

    ODRL_CONFLICT = ODRL.conflict
    ODRL_PERM = ODRL.perm
    ODRL_PROHIBIT = ODRL.prohibit
    ODRL_INVALID = ODRL.invalid

    def get_policy_conflict(policy_node):
        """
        Read the ODRL conflict strategy from a policy node and
        convert it to the simplified evaluator representation.

        Returns:
            1 : perm
            0 : invalid
            -1 : prohibit
        """

        conflict_value = next(
            odrl_graph.objects(
                policy_node,
                ODRL_CONFLICT
            ),
            None
        )

        if conflict_value == ODRL_PERM:
            return 1

        elif conflict_value == ODRL_PROHIBIT:
            return -1

        elif (
                conflict_value == ODRL_INVALID
                or conflict_value is None
        ):
            return 0

        # Unknown / unsupported conflict value
        return 0

    def build_rule_structure(
            rule_node,
            policy_target=None,
            policy_assignee=None,
            policy_action=None
    ):
        """
        Recursively build a rule structure in case there are nested duties, consequences or remedies
        """

        rule_dict = {
            "conditions": extract_rule_list(
                odrl_graph,
                rule_node,
                policy_target=policy_target,
                policy_assignee=policy_assignee,
                policy_action=policy_action
            )
        }

        # ---- DUTIES (permission → duty) ----
        duties = []
        for duty in odrl_graph.objects(rule_node, ODRL.duty):
            duties.append(build_rule_structure(duty,
                    policy_target=policy_target,
                    policy_assignee=policy_assignee,
                    policy_action=policy_action))

        if duties:
            rule_dict["duties"] = duties

        # ---- CONSEQUENCES (duty or obligation → consequence) ----
        consequences = []
        for consequence in odrl_graph.objects(rule_node, ODRL.consequence):
            consequences.append(build_rule_structure(consequence,
                policy_target=policy_target,
                policy_assignee=policy_assignee,
                policy_action=policy_action))

        if consequences:
            rule_dict["consequences"] = consequences

        # ---- REMEDIES (prohibition → remedy) ----
        remedies = []
        for remedy in odrl_graph.objects(rule_node, ODRL.remedy):
            remedies.append(build_rule_structure(remedy,
                policy_target=policy_target,
                policy_assignee=policy_assignee,
                policy_action=policy_action))

        if remedies:
            rule_dict["remedies"] = remedies

        return rule_dict

    # ----------------------------------------------------

    # Find all policies in the graph
    for policy in set(
        s for p in policy_predicates
        for s in odrl_graph.subjects(predicate=p)
    ):

        conflict = get_policy_conflict(policy)

        permissions = []
        prohibitions = []
        obligations = []

        # Policy-level defaults

        policy_target = next(
            (str(value) for value in odrl_graph.objects(policy, ODRL.target)),
            None
        )

        policy_assignee = next(
            (str(value) for value in odrl_graph.objects(policy, ODRL.assignee)),
            None
        )

        policy_action = next(
            (str(value) for value in odrl_graph.objects(policy, ODRL.action)),
            None
        )

        # ---- PERMISSIONS ----
        for perm in odrl_graph.objects(policy, ODRL.permission):
            permissions.append(
                build_rule_structure(perm,
                    policy_target=policy_target,
                    policy_assignee=policy_assignee,
                    policy_action=policy_action)
            )

        # ---- PROHIBITIONS ----
        for prohib in odrl_graph.objects(policy, ODRL.prohibition):
            prohibitions.append(
                build_rule_structure(prohib,
                    policy_target=policy_target,
                    policy_assignee=policy_assignee,
                    policy_action=policy_action)
            )

        # ---- OBLIGATIONS ----
        for oblig in odrl_graph.objects(policy, ODRL.obligation):
            obligations.append(
                build_rule_structure(oblig,
                    policy_target=policy_target,
                    policy_assignee=policy_assignee,
                    policy_action=policy_action)
            )

        policy_list.append({
            "policy_iri": str(policy),
            "conflict": conflict,
            "permissions": permissions,
            "prohibitions": prohibitions,
            "obligations": obligations
        })

    return policy_list


def extract_rule_list_from_policy_from_file(file_path):
    g = load(file_path)[0]
    return extract_rule_list_from_policy(g)