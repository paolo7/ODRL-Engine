from rdflib import Graph, Namespace, RDF, RDFS, URIRef, BNode, Literal
import random, uuid, os
from owlrl import RDFS_Semantics

base_uri = "https://example.com/iri/"
ODRL_operators = [
    "http://www.w3.org/ns/odrl/2/lt",
    "http://www.w3.org/ns/odrl/2/lteq",
    "http://www.w3.org/ns/odrl/2/gt",
    "http://www.w3.org/ns/odrl/2/gteq",
    "http://www.w3.org/ns/odrl/2/eq",
    "http://www.w3.org/ns/odrl/2/neq"
]

def generate_ODRL(policy_number = 1, p_rule_n = 2, f_rule_n = 2, o_rule_n = 1,
                  constants_per_feature = 4,
                  constraint_number_min = 0, constraint_number_max = 4,
                  chance_feature_null = 0.5,
                  constraint_right_operand_min = 0,
                  constraint_right_operand_max = 100,
                  ontology_path = "sample_ontologies/ODRL_DPV.ttl") -> Graph:

    ODRL = Namespace("http://www.w3.org/ns/odrl/2/")
    EX = Namespace(base_uri)

    g = Graph()
    g.bind("odrl", ODRL)
    g.bind("ex", EX)

    # --- Load ontology
    ont = Graph()
    if not os.path.exists(ontology_path):
        raise FileNotFoundError(f"Ontology not found: {ontology_path}")
    ont.parse(ontology_path, format="ttl")

    try:
        RDFS_Semantics().run(ont)
    except Exception:
        pass

    def gather_candidates(graph, top_cls):
        subclasses = {s for s in graph.subjects(RDFS.subClassOf, top_cls)}
        added = True
        while added:
            added = False
            for s, _, o in graph.triples((None, RDFS.subClassOf, None)):
                if o in subclasses and s not in subclasses and s != top_cls:
                    subclasses.add(s)
                    added = True

        candidates = set()
        for inst in graph.subjects(RDF.type, top_cls):
            candidates.add(inst)
        for sc in subclasses:
            for inst in graph.subjects(RDF.type, sc):
                candidates.add(inst)
            candidates.add(sc)
        candidates.discard(top_cls)
        return candidates

    def sample_iris(candidates, n):
        if not candidates:
            return [URIRef(base_uri + "synthetic/" + str(uuid.uuid4())) for _ in range(n)]
        cands = list(candidates)
        return random.sample(cands, n) if len(cands) >= n else [random.choice(cands) for _ in range(n)]

    # --- Gather candidates for all features
    actions_all = gather_candidates(ont, ODRL.Action)
    parties_all = gather_candidates(ont, ODRL.Party)
    targets_all = gather_candidates(ont, ODRL.Asset)
    left_operands_all = gather_candidates(ont, ODRL.LeftOperand)

    # --- Select constants once for all policies
    selected_actions = sample_iris(actions_all, constants_per_feature)
    selected_parties = sample_iris(parties_all, constants_per_feature)
    selected_targets = sample_iris(targets_all, constants_per_feature)
    selected_left_operands = sample_iris(left_operands_all, constants_per_feature)

    # --- Helpers
    def make_rule(rule_type: URIRef, rule_idx: int):
        node = BNode()
        g.add((node, RDF.type, rule_type))
        return node

    def maybe_add_feature(subject, prop, candidates, required=True):
        if required or (random.random() > chance_feature_null):
            g.add((subject, prop, random.choice(candidates)))

    # --- Constraint creation
    def add_constraints(rule):
        n = random.randint(constraint_number_min, constraint_number_max)
        for _ in range(n):
            constraint = BNode()
            g.add((rule, ODRL.constraint, constraint))
            left = random.choice(selected_left_operands)
            operator = URIRef(random.choice(ODRL_operators))
            right = Literal(random.randint(constraint_right_operand_min, constraint_right_operand_max))
            g.add((constraint, ODRL.leftOperand, left))
            g.add((constraint, ODRL.operator, operator))
            g.add((constraint, ODRL.rightOperand, right))

    # --- Unified rule creation
    def add_rules(policy_node, rule_type, link_predicate, count):
        for i in range(count):
            rule = make_rule(rule_type, i)
            g.add((policy_node, link_predicate, rule))
            maybe_add_feature(rule, ODRL.action, selected_actions, required=True)
            maybe_add_feature(rule, ODRL.assignee, selected_parties, required=False)
            maybe_add_feature(rule, ODRL.target, selected_targets, required=False)
            add_constraints(rule)

    # --- Generate multiple policies
    for _ in range(policy_number):
        policy = URIRef(base_uri + "policy/" + str(uuid.uuid4()))
        g.add((policy, RDF.type, ODRL.Policy))
        add_rules(policy, ODRL.Permission, ODRL.permission, p_rule_n)
        add_rules(policy, ODRL.Prohibition, ODRL.prohibition, f_rule_n)
        add_rules(policy, ODRL.Duty, ODRL.obligation, o_rule_n)

    return g


# --- Example usage
#policy = generate_ODRL()
#print(policy.serialize(format="turtle").decode("utf-8") if isinstance(policy.serialize(format="turtle"), bytes) else policy.serialize(format="turtle"))
