# This file modifies an ODRL policy if we need to make it work with a tool that only supports
# purpose equality in constraints, and needs every rule to specify one such purpose constraint
# naturally, information will be lost, such as any constraint on purposes that use other operators
# like the not-equal-to.

import sys
import os
import json
from pyld import jsonld
import datetime

# Add parent folder to Python path
parent_folder = os.path.abspath(os.path.join(os.getcwd(), ".."))
if parent_folder not in sys.path:
    sys.path.insert(0, parent_folder)

import rdf_utils
import setup_colab
import rdflib
from rdflib import Graph, Namespace, RDF, RDFS, SKOS
from IPython.display import display, HTML
from google.colab import files

def transform_odrl_rules_and_download():
    """
    Parse uploaded ODRL file, transform rules according to constraints,
    and download the modified graph as TTL.
    """
    global g, format

    # --- Load uploaded file ---
    if setup_colab.UploadState.content is None:
        raise ValueError("No file uploaded yet!")

    policy_content = setup_colab.UploadState.content.decode("utf-8")
    g, format = rdf_utils.parse_string_to_graph(policy_content)

    # Namespaces
    ODRL = rdflib.Namespace("http://www.w3.org/ns/odrl/2/")
    DPV = rdflib.Namespace("https://w3id.org/dpv/owl#")

    # --- Collect all policies ---
    policy_types = [ODRL.Policy, ODRL.Set, ODRL.Agreement, ODRL.Offer]
    policy_nodes = []
    for t in policy_types:
        policy_nodes.extend(list(g.subjects(RDF.type, t)))

    # Each policy can have permissions, prohibitions, and duties
    rule_predicates = [ODRL.permission, ODRL.prohibition, ODRL.duty]

    for pol in policy_nodes:
        for rule_pred in rule_predicates:
            for rule in g.objects(pol, rule_pred):

                # --- Step 1: Convert odrl:isAnyOf → odrl:eq for odrl:purpose constraints ---
                for constraint in g.objects(rule, ODRL.constraint):
                    left = g.value(constraint, ODRL.leftOperand)
                    operator = g.value(constraint, ODRL.operator)
                    if left == ODRL.purpose and operator == ODRL.isAnyOf:
                        g.remove((constraint, ODRL.operator, operator))
                        g.add((constraint, ODRL.operator, ODRL.eq))

                # --- Step 2: Split rules with multiple right operands for odrl:purpose ---
                purpose_constraints = [
                    c for c in g.objects(rule, ODRL.constraint)
                    if g.value(c, ODRL.leftOperand) == ODRL.purpose and g.value(c, ODRL.operator) == ODRL.eq
                ]
                for constraint in purpose_constraints:
                    right_operands = list(g.objects(constraint, ODRL.rightOperand))
                    if len(right_operands) > 1:
                        # For each extra operand, create a new rule copy
                        for obj in right_operands[1:]:
                            new_rule = rdflib.BNode()
                            g.add((pol, rule_pred, new_rule))
                            # Copy all predicates except constraint
                            for p, o in g.predicate_objects(rule):
                                if p != ODRL.constraint:
                                    g.add((new_rule, p, o))
                            # Add one constraint with a single right operand
                            new_constraint = rdflib.BNode()
                            g.add((new_rule, ODRL.constraint, new_constraint))
                            g.add((new_constraint, ODRL.leftOperand, ODRL.purpose))
                            g.add((new_constraint, ODRL.operator, ODRL.eq))
                            g.add((new_constraint, ODRL.rightOperand, obj))
                        # Keep only first operand in original constraint
                        for obj in right_operands[1:]:
                            g.remove((constraint, ODRL.rightOperand, obj))

                # --- Step 4: Remove purpose constraints with operator ≠ odrl:eq ---
                for constraint in list(g.objects(rule, ODRL.constraint)):
                    left = g.value(constraint, ODRL.leftOperand)
                    operator = g.value(constraint, ODRL.operator)
                    if left == ODRL.purpose and operator and operator != ODRL.eq:
                        # Remove all triples about this constraint
                        for p, o in list(g.predicate_objects(constraint)):
                            g.remove((constraint, p, o))
                        g.remove((rule, ODRL.constraint, constraint))

                # --- Step 5: Add default odrl:purpose=DPV:Purpose if missing ---
                has_purpose_constraint = any(
                    g.value(c, ODRL.leftOperand) == ODRL.purpose and g.value(c, ODRL.operator) == ODRL.eq
                    for c in g.objects(rule, ODRL.constraint)
                )
                if not has_purpose_constraint:
                    new_constraint = rdflib.BNode()
                    g.add((rule, ODRL.constraint, new_constraint))
                    g.add((new_constraint, ODRL.leftOperand, ODRL.purpose))
                    g.add((new_constraint, ODRL.operator, ODRL.eq))
                    g.add((new_constraint, ODRL.rightOperand, DPV.Purpose))


      # --- Step 5: Build nested JSON-LD structure manually and save ---
    for s, p, o in list(g):
        if isinstance(o, datetime.date):
            g.remove((s, p, o))
            g.add((s, p, Literal(o.isoformat(), datatype=XSD.date)))
    import json
    from pyld import jsonld

    ODRL = rdflib.Namespace("http://www.w3.org/ns/odrl/2/")
    DPV = rdflib.Namespace("https://w3id.org/dpv/owl#")

    # helper to turn constraint node into dict
    def constraint_to_dict(c):
        left = g.value(c, ODRL.leftOperand)
        op = g.value(c, ODRL.operator)
        right = g.value(c, ODRL.rightOperand)
        return {
            "odrl:leftOperand": str(left),
            "odrl:operator": str(op),
            "odrl:rightOperand": str(right) if isinstance(right, rdflib.URIRef) else (right.toPython() if isinstance(right, rdflib.Literal) else str(right))
        }

    # helper to turn rule (permission/prohibition/duty) into dict
    def rule_to_dict(rule):
        rule_obj = {}
        for p, o in g.predicate_objects(rule):
            if p == ODRL.constraint:
                # list of constraints
                rule_obj.setdefault("odrl:constraint", []).append(constraint_to_dict(o))
            elif p in [ODRL.action, ODRL.target, ODRL.assigner, ODRL.assignee]:
                # single-value links
                if isinstance(o, rdflib.URIRef):
                    rule_obj[str(p)] = str(o)
                else:
                    # nested blank node → extract rdf:value if present
                    val = g.value(o, rdflib.term.URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#value"))
                    rule_obj[str(p)] = str(val) if val else str(o)
            else:
                rule_obj[str(p)] = str(o)
        return rule_obj

    # build nested policies
    policies_json = []
    policy_types = [ODRL.Policy, ODRL.Set, ODRL.Agreement, ODRL.Offer]
    rule_predicates = [ODRL.permission, ODRL.prohibition, ODRL.duty]

    for t in policy_types:
        for pol in g.subjects(RDF.type, t):
            pol_dict = {
                "@id": str(pol),
                "@type": str(t),
            }
            for rp in rule_predicates:
                rules = [rule_to_dict(r) for r in g.objects(pol, rp)]
                if rules:
                    pol_dict[str(rp)] = rules
            policies_json.append(pol_dict)

    # build final compacted JSON-LD
    context = {
        "odrl": "http://www.w3.org/ns/odrl/2/",
        "dpv": "https://w3id.org/dpv/owl#",
        "foaf": "http://xmlns.com/foaf/0.1/",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "cactus": "https://www.cactusweb.gr/vocab/",
    }

    jsonld_data = {"@context": context, "@graph": policies_json}

    # compact (optional, but safe)
    compacted = jsonld.compact(jsonld_data, context)

    temp_filename = setup_colab.UploadState.filename.replace(".ttl", "_nested.json")
    with open(temp_filename, "w", encoding="utf-8") as f:
        json.dump(compacted, f, indent=2, ensure_ascii=False)

    files.download(temp_filename)
    print(f"✅ Nested, clean JSON-LD saved as {temp_filename}")