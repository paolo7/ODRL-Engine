import Evaluation.evaluator_functions
import rdf_utils
import SotW_generator
import pandas as pd
import validate
import operator

OPS_MAP = {
    "=": operator.eq,
    "!=": operator.ne,
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
}

def evaluate_ODRL_from_files(policy_file, SotW_file):
    graph = rdf_utils.load(policy_file)[0]
    graph_rules = SotW_generator.extract_rule_list_from_policy(graph)
    df = pd.read_csv(SotW_file)
    return evaluate_ODRL_on_dataframe(graph_rules, df)


def evaluate_ODRL_on_dataframe(policies, data_frame):

    results = evaluate_all_policies_rowwise(data_frame, policies, OPS_MAP)

    has_deny = False
    messages = []

    for r in results:
        if r["decision"] == "DENY":
            has_deny = True
            messages.append(f"Row {r['row_index']} is NON-COMPLIANT")
        else:
            messages.append(f"Row {r['row_index']} is COMPLIANT")

    message_str = "\n".join(messages)

    # If any DENY → return False
    return (not has_deny), {}, message_str



def eval_constraint(row, constraint, OPS_MAP):
    """
    Evaluate a single policy constraint on a dataframe row.
    Supports equality and numeric comparison operators.
    Returns True if the constraint is satisfied, else False.
    """
    left, op_symbol, right = constraint

    if left not in row:
        return False

    value = row[left]
    if value is None or value == "":
        return False

    if op_symbol not in OPS_MAP:
        return False

    # Equality / inequality → allow string compare
    if op_symbol in ("=", "!="):
        return OPS_MAP[op_symbol](str(value), str(right))

    # Ordering operators → numeric only
    try:
        return OPS_MAP[op_symbol](float(value), float(right))
    except Exception:
        return False


def eval_rule(row, rule, OPS_MAP):
    return all(eval_constraint(row, c, OPS_MAP) for c in rule)


def eval_ruleset(row, rules, OPS_MAP):
    """
    rules = permissions OR prohibitions list
    """
    for rule in rules:
        if eval_rule(row, rule, OPS_MAP):
            return True
    return False


def evaluate_row_policy_verbose(row, policy, OPS_MAP):
    
    permission_matches = []
    prohibition_matches = []

    # check permissions
    for i, rule in enumerate(policy["permissions"]):
        if eval_rule(row, rule, OPS_MAP):
            permission_matches.append(i)

    # check prohibitions
    for i, rule in enumerate(policy["prohibitions"]):
        if eval_rule(row, rule, OPS_MAP):
            prohibition_matches.append(i)

    # decision logic
    if prohibition_matches:
        decision = "DENY"
        reason = "Prohibition violated"
    elif permission_matches:
        decision = "ALLOW"
        reason = "Permission satisfied"
    else:
        decision = "DENY"
        reason = "No permission satisfied"

    return {
        "decision": decision,
        "reason": reason,
        "permissions_satisfied": permission_matches,
        "prohibitions_satisfied": prohibition_matches,
    }


def evaluate_policy_df_rowwise(df, policy, OPS_MAP):
    results = []

    for idx, row in df.iterrows():
        row_result = evaluate_row_policy_verbose(row, policy, OPS_MAP)
        row_result.update({"row_index": idx, "policy": policy["policy_iri"]})
        results.append(row_result)

    return results


def evaluate_all_policies_rowwise(df, policies, OPS_MAP):
    all_results = []
    for policy in policies:
        row_results = evaluate_policy_df_rowwise(df, policy, OPS_MAP)
        all_results.extend(row_results)
    return all_results


# print("Evaluation: "+str(evaluate_ODRL_from_files("example_policies/exampleEvaluationPolicy.ttl","example_policies/exampleSotW.csv")))
