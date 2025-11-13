from rdflib.namespace import RDF
import rdflib
from rdflib.collection import Collection
import rdf_utils
import csv
import random
from datetime import datetime, timedelta

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

ODRL = rdflib.Namespace("http://www.w3.org/ns/odrl/2/")

refinement_contexts_incoming = {
    "http://www.w3.org/ns/odrl/2/Party": ODRL.assignee,  # Party if something has an :assignee -> node
    "http://www.w3.org/ns/odrl/2/Action": ODRL.action,  # Action if something has an :action -> node
    "http://www.w3.org/ns/odrl/2/Asset": ODRL.target,  # Asset if something has a :target -> node
}

policy_predicates = {ODRL.permission, ODRL.prohibition, ODRL.obligation}

last_seen_list_of_features = None

# LIMITATIONS
# this code does not deal with constraints expressed as lists, thus it also fails to support logic constraints
# returns an alphabetically ordered list of unique features (left operands) from the policies
# refinements of assignee/action/target have Party/Action/Asset prepended to the IRI and space separated, to distinguish them
# from constraints.
# all lists contain datetime, party, action and asset by default
def extract_features_list_from_policy(odrl_graph: rdflib.Graph):
    features = []

    # Predicates used to decide top-level policy-like nodes
    policy_predicates = {ODRL.permission, ODRL.prohibition, ODRL.obligation}

    # Mapping for refinement context detection:
    # key = label to use as Y, value = tuple(incoming predicate to detect that context)


    # Iterate over all nodes that have an outgoing odrl:leftOperand (these are constraints/refinements)
    for constraint in odrl_graph.subjects(predicate=ODRL.leftOperand):
        # get left operand (X) — use the first if multiple
        lefts = list(odrl_graph.objects(constraint, ODRL.leftOperand))
        if not lefts:
            continue
        left_operand = str(lefts[0])

        added_as_direct = False

        # Find any parent that references this constraint via odrl:constraint
        for parent in odrl_graph.subjects(predicate=ODRL.constraint, object=constraint):
            has_policy_like = any(
                next(odrl_graph.subjects(predicate=p, object=parent), None) is not None
                for p in policy_predicates
            )
            if has_policy_like:
                features.append({
                    "iri": left_operand,
                    "type": "http://www.w3.org/ns/shacl#Literal"
                })
                added_as_direct = True

        # If constraint was not attached directly to a policy-like parent, check for refinement attachments.
        # A refinement is modeled as some node R having odrl:refinement -> constraint.
        for referrer in odrl_graph.subjects(predicate=ODRL.refinement, object=constraint):
            # For each referrer R, decide whether R is a Party/Action/Asset by checking incoming edges
            matched = False
            for iri_prefix, incoming_pred in refinement_contexts_incoming.items():
                # If there exists any triple (?s, incoming_pred, referrer), then referrer is of that context
                if any(odrl_graph.subjects(predicate=incoming_pred, object=referrer)):
                    features.append({
                        "iri": f"{iri_prefix} {left_operand}",
                        "type": "http://www.w3.org/ns/shacl#Literal"
                    })
                    matched = True
                    # could be multiple context types, don't break; allow multiple if RDF encodes them
            # If referrer is attached to something that itself is a node used in permission/prohibition/obligation,
            # it's possible the referrer is nested under a rule — the above incoming-edge checks cover the requested detection.



    # 1. Sort features alphabetically by iri, to have deterministic lists of features
    features = sorted(features, key=lambda f: f["iri"])

    # 2. Prepend the base features
    all_features = base_features + features

    # 3. Deduplicate by (iri, type)
    seen = set()
    unique_features = []
    for f in all_features:
        key = f["iri"]  # only compare by IRI
        if key not in seen:
            seen.add(key)
            unique_features.append(f)

    last_seen_list_of_features = unique_features
    return unique_features

def extract_rule_list(odrl_graph, rule_node, features):
    """
    Extract all components (action, target, assignee) and constraints/refinements
    of a rule, returning triplets <A, B, C>.
    Handles nested refinements inside components.
    """
    triplets = []

    # Map ODRL operators to standard symbols
    operator_map = {
        ODRL.eq: "=",
        ODRL.neq: "!=",
        ODRL.lt: "<",
        ODRL.gt: ">",
        ODRL.lteq: "<=",
        ODRL.gteq: ">="
    }

    # Helper to extract values from a node (URI, literal, or complex node with rdf:value/odrl:source)
    def extract_values(node):
        if isinstance(node, rdflib.term.URIRef) or isinstance(node, rdflib.term.Literal):
            return [str(node)]
        values = list(odrl_graph.objects(node, RDF.value)) + list(odrl_graph.objects(node, ODRL.source))
        return [str(v) for v in values] if values else [str(node)]

    def append_triplet(node, prefix=None):
        lefts = list(odrl_graph.objects(node, ODRL.leftOperand))
        rights = list(odrl_graph.objects(node, ODRL.rightOperand))
        operators = list(odrl_graph.objects(node, ODRL.operator))
        if lefts:
            left = f"{prefix} {str(lefts[0])}" if prefix else str(lefts[0])
            op = operator_map.get(operators[0], str(operators[0])) if operators else str(operators[0])
            right = str(rights[0]) if rights else ""
            triplets.append([left, op, right])

    # --- 1. Extract Action, Asset, Party components ---
    for component_type, predicate in refinement_contexts_incoming.items():
        for comp_node in odrl_graph.objects(rule_node, predicate):
            # Add the component itself
            for val in extract_values(comp_node):
                triplets.append([component_type, "=", val])
            # Nested refinements inside component
            for refinement in odrl_graph.objects(comp_node, ODRL.refinement):
                append_triplet(refinement, prefix=component_type)

    # --- 2. Extract constraints directly attached to the rule ---
    for constraint in odrl_graph.objects(rule_node, ODRL.constraint):
        append_triplet(constraint)

        # --- 3. Handle refinements attached to this constraint ---
        for refinement in odrl_graph.subjects(predicate=ODRL.refinement, object=constraint):
            for iri_prefix, incoming_pred in refinement_contexts_incoming.items():
                if any(odrl_graph.subjects(predicate=incoming_pred, object=refinement)):
                    append_triplet(constraint, prefix=iri_prefix)

    # Deduplicate triplets by all three fields
    seen = set()
    unique_triplets = []
    for t in triplets:
        key = tuple(t)
        if key not in seen:
            seen.add(key)
            unique_triplets.append(t)

    return unique_triplets



def extract_rule_list_from_policy(odrl_graph: rdflib.Graph):
    policy_list = []

    # Find all policies in the graph
    for policy in set(s for p in policy_predicates for s in odrl_graph.subjects(predicate=p)):
        permissions = []
        prohibitions = []
        obligations = []

        # Permissions
        for perm in odrl_graph.objects(policy, ODRL.permission):
            permissions.append(extract_rule_list(odrl_graph, perm, last_seen_list_of_features))

        # Prohibitions
        for prohib in odrl_graph.objects(policy, ODRL.prohibition):
            prohibitions.append(extract_rule_list(odrl_graph, prohib, last_seen_list_of_features))

        # Obligations
        for oblig in odrl_graph.objects(policy, ODRL.obligation):
            obligations.append(extract_rule_list(odrl_graph, oblig, last_seen_list_of_features))

        policy_list.append({"policy_iri": str(policy), "permissions": permissions, "prohibitions": prohibitions,
                            "obligations": obligations})


    return policy_list


def generate_state_of_the_world_from_policies(
    odrl_graph: rdflib.Graph,
    number_of_records=100,
    valid=True,
    chance_feature_empty=0.5,
    csv_file="sotw.csv"
):
    features = extract_features_list_from_policy(odrl_graph)
    policy_list = extract_rule_list_from_policy(odrl_graph)

    feature_iris = [f["iri"] for f in features]

    rows = []
    now = datetime.now()

    # ---------------------------------------------------------
    # PRECOMPUTE which rows will be invalid (if valid=False)
    # ---------------------------------------------------------
    if not valid:
        n_invalid = max(1, int(0.10 * number_of_records))
        invalid_indices = set(random.sample(range(number_of_records), n_invalid))
    else:
        invalid_indices = set()

    for i in range(number_of_records):

        # whether this row should invert the rule logic
        invert_condition = (i in invalid_indices)

        row = {}
        if not policy_list:
            continue
        policy = random.choice(policy_list)
        if not policy["permissions"]:
            continue

        permission_triplets_lists = random.choice(policy["permissions"])
        permission_triplets = [t for sublist in permission_triplets_lists for t in sublist]

        for feature in features:
            iri = feature["iri"]
            ftype = feature["type"]

            # datetime column
            if iri == "http://www.w3.org/ns/odrl/2/dateTime":
                row[iri] = (now - timedelta(minutes=i * 10)).isoformat()
                continue

            matching_triplets = [t for t in permission_triplets_lists if t[0] == iri]

            if matching_triplets:
                _, op, val = random.choice(matching_triplets)

                try:
                    # Try integer first
                    val_int = int(val)

                    # Integer operator with inversion logic
                    if (op == "=" and not invert_condition) or (op == "!=" and invert_condition):
                        row[iri] = val_int
                    elif (op == "!=" and not invert_condition) or (op == "=" and invert_condition):
                        row[iri] = val_int + random.randint(1, 100)
                    elif (op == "<" and not invert_condition) or (op == ">=" and invert_condition):
                        row[iri] = val_int - random.randint(1, 100)
                    elif (op == "<=" and not invert_condition) or (op == ">" and invert_condition):
                        row[iri] = val_int - random.randint(0, 100)
                    elif (op == ">" and not invert_condition) or (op == "<=" and invert_condition):
                        row[iri] = val_int + random.randint(1, 100)
                    elif (op == ">=" and not invert_condition) or (op == "<" and invert_condition):
                        row[iri] = val_int + random.randint(0, 100)
                    else:
                        row[iri] = val_int

                except ValueError:
                    # Try float
                    try:
                        val_float = float(val)

                        # Float operator with inversion logic
                        if (op == "=" and not invert_condition) or (op == "!=" and invert_condition):
                            row[iri] = val_float
                        elif (op == "!=" and not invert_condition) or (op == "=" and invert_condition):
                            row[iri] = val_float + random.uniform(1, 100)
                        elif (op == "<" and not invert_condition) or (op == ">=" and invert_condition):
                            row[iri] = val_float - random.uniform(1, 100)
                        elif (op == "<=" and not invert_condition) or (op == ">" and invert_condition):
                            row[iri] = val_float - random.uniform(0, 100)
                        elif (op == ">" and not invert_condition) or (op == "<=" and invert_condition):
                            row[iri] = val_float + random.uniform(1, 100)
                        elif (op == ">=" and not invert_condition) or (op == "<" and invert_condition):
                            row[iri] = val_float + random.uniform(0, 100)
                        else:
                            row[iri] = val_float

                    except ValueError:
                        # Non-numeric fallback
                        if (op == "=" and not invert_condition) or (op == "!=" and invert_condition):
                            row[iri] = val
                        elif (op == "!=" and not invert_condition) or (op == "=" and invert_condition):
                            row[iri] = f"https://example.com/iri/sotw#{random.randint(1, 100000)}"
                        else:
                            row[iri] = ""

            else:
                # No constraint exists for this feature
                if random.random() < chance_feature_empty:
                    row[iri] = ""
                else:
                    if ftype == "http://www.w3.org/ns/shacl#IRI":
                        row[iri] = f"https://example.com/iri/sotw#{random.randint(1, 100000)}"
                    else:
                        row[iri] = random.randint(0, 100)

        rows.append(row)

    # Write CSV
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=feature_iris)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    #print(f"CSV file '{csv_file}' generated with {len(rows)} rows and {len(feature_iris)} columns.")

def extract_features_list_from_policy_from_file(file_path):
    g = rdf_utils.load(file_path)[0]
    return extract_features_list_from_policy(g)
def extract_rule_list_from_policy_from_file(file_path):
    g = rdf_utils.load(file_path)[0]
    return extract_rule_list_from_policy(g)
def generate_state_of_the_world_from_policies_from_file(
        file_path,
        number_of_records=100,
        valid=True,
        chance_feature_empty=0.5,
        csv_file="sotw.csv"
    ):
    g = rdf_utils.load(file_path)[0]
    return generate_state_of_the_world_from_policies(g, number_of_records, valid, chance_feature_empty, csv_file)

# Example usage
#g = rdf_utils.load("example_policies/example_valid2.ttl")[0]
#file_path = "example_policies/example_valid2.ttl"
#print(*extract_features_list_from_policy_from_file(file_path), sep ="\n")
#print("\nPolicies with rules:")
#print(*extract_rule_list_from_policy_from_file(file_path), sep="\n")

#csv = generate_state_of_the_world_from_policies_from_file(file_path, number_of_records=50, chance_feature_empty=0.3)

#print(csv)