from pyexpat import features
import Evaluation.evaluator_functions
import rdf_utils
import SotW_generator
import pandas as pd
import validate
import operator
# if dateutil is not install then install it using (!pip install python-dateutil)
from dateutil import parser

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
    features = SotW_generator.extract_features_list_from_policy(graph)
    FEATURE_TYPE_MAP = {f["iri"]: f["type"] for f in features}
    df = pd.read_csv(SotW_file)
    return evaluate_ODRL_on_dataframe(graph_rules, df, FEATURE_TYPE_MAP)


def evaluate_ODRL_on_dataframe(policies, data_frame, FEATURE_TYPE_MAP):
    results = evaluate_all_policies_rowwise(
        data_frame, policies, OPS_MAP, FEATURE_TYPE_MAP
    )

    total_rows = len(data_frame)
    compliant_count = 0
    not_permitted = []
    prohibited = []

    # --- Classify results ---
    for r in results:
        if r["decision"] == "DENY":
            if r["reason"] == "No permission satisfied":
                not_permitted.append(r)
            elif r["reason"] == "Prohibition violated":
                prohibited.append(r)
        else:
            compliant_count += 1

    not_permitted_count = len(not_permitted)
    prohibited_count = len(prohibited)

    overall_compliant = (compliant_count == total_rows)
    verdict = "YES" if overall_compliant else "NO"

    # --- Build message ---
    message_lines = [
        f"State of the World valid? {verdict}",
        "",
        "Evaluation report:",
    ]

    if overall_compliant:
        message_lines.append(
            f"Compliant log entries: {total_rows}/{total_rows} (100%)."
        )
    else:
        compliant_percentage = round(compliant_count / total_rows * 100, 2)
        message_lines.append(
            f"Compliant log entries: {compliant_count}/{total_rows} ({compliant_percentage}%)."
        )

        if not_permitted_count > 0:
            np_pct = round(not_permitted_count / total_rows * 100, 2)
            message_lines.append(
                f" - {not_permitted_count}/{total_rows} ({np_pct}%) are non compliant "
                f"because the logged event is not permitted"
            )

        if prohibited_count > 0:
            p_pct = round(prohibited_count / total_rows * 100, 2)
            message_lines.append(
                f" - {prohibited_count}/{total_rows} ({p_pct}%) are non compliant "
                f"because the logged event is prohibited"
            )

        message_lines.append("")
        message_lines.append("Details of non-compliance:")

        for r in not_permitted:
            idx = r["row_index"]
            message_lines.append(
                f" - The following logged event (row {idx}) is non-compliant because it is NOT PERMITTED"
            )
            message_lines.append(str(data_frame.iloc[idx].to_dict()))

        for r in prohibited:
            idx = r["row_index"]
            message_lines.append(
                f" - The following logged event (row {idx}) is non-compliant because it is PROHIBITED"
            )
            message_lines.append(str(data_frame.iloc[idx].to_dict()))

    message_str = "\n".join(message_lines)

    return overall_compliant, {}, message_str



def eval_constraint(row, constraint, OPS_MAP, FEATURE_TYPE_MAP):
    left, op_symbol, right = constraint

    if left not in row:
        return False

    value = row[left]
    if value is None or value == "":
        return False

    if op_symbol not in OPS_MAP:
        return False

    column_type = FEATURE_TYPE_MAP.get(left)

    # --- 1️⃣ DateTime handling ---
    if column_type == "http://www.w3.org/2001/XMLSchema#dateTime":
        try:
            left_date = parser.parse(str(value)).date()
            right_date = parser.parse(str(right)).date()

            # Normalize timezone (avoid naive vs aware errors)
            # if left_date.tzinfo and not right_date.tzinfo:
            #     right_date = right_date.replace(tzinfo=left_date.tzinfo)
            # elif right_date.tzinfo and not left_date.tzinfo:
            #     left_date = left_date.replace(tzinfo=right_date.tzinfo)

            return OPS_MAP[op_symbol](left_date, right_date)

        except Exception:
            return False

    # --- 2️⃣ Equality / inequality → string compare ---
    if op_symbol in ("=", "!="):
        return OPS_MAP[op_symbol](str(value), str(right))

    # --- 3️⃣ Numeric comparison ---
    try:
        return OPS_MAP[op_symbol](float(value), float(right))
    except Exception:
        return False




def eval_rule(row, rule, OPS_MAP, FEATURE_TYPE_MAP):
    return all(eval_constraint(row, c, OPS_MAP, FEATURE_TYPE_MAP) for c in rule)


def eval_ruleset(row, rules, OPS_MAP, FEATURE_TYPE_MAP):
    """
    rules = permissions OR prohibitions list
    """
    for rule in rules:
        if eval_rule(row, rule, OPS_MAP, FEATURE_TYPE_MAP):
            return True
    return False


def evaluate_row_policy_verbose(row, policy, OPS_MAP, FEATURE_TYPE_MAP):
    permission_matches = []
    satisfied_permissions = []
    prohibition_matches = []
    violated_prohibitions = []

    # check permissions
    for i, rule in enumerate(policy["permissions"]):
        if eval_rule(row, rule, OPS_MAP, FEATURE_TYPE_MAP):
            permission_matches.append(i)
            satisfied_permissions.append(rule)

    # check prohibitions
    for i, rule in enumerate(policy["prohibitions"]):
        if eval_rule(row, rule, OPS_MAP, FEATURE_TYPE_MAP):
            prohibition_matches.append(i)
            violated_prohibitions.append(rule)

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
        "permissions_satisfied_indices": permission_matches,
        "permissions_satisfied_rules": satisfied_permissions,
        "prohibitions_violated_indices": prohibition_matches,
        "prohibitions_violated_rules": violated_prohibitions,
    }


def evaluate_policy_df_rowwise(df, policy, OPS_MAP, FEATURE_TYPE_MAP):
    results = []

    for idx, row in df.iterrows():
        row_result = evaluate_row_policy_verbose(row, policy, OPS_MAP, FEATURE_TYPE_MAP)
        row_result.update(
            {
                "row_index": idx,
                "policy_iri": policy.get("policy_iri", "unknown_policy"),
                "row_data": row.to_dict(),  # optional, include actual row values
            }
        )
        results.append(row_result)

    return results


def evaluate_all_policies_rowwise(df, policies, OPS_MAP, FEATURE_TYPE_MAP):
    all_results = []

    for policy in policies:
        row_results = evaluate_policy_df_rowwise(df, policy, OPS_MAP, FEATURE_TYPE_MAP)
        all_results.extend(row_results)

    return all_results


def extract_deny_details(results):
    deny_details = []

    for r in results:
        if r["decision"] == "DENY":
            deny_details.append(
                {
                    "row_index": r["row_index"],
                    "row_data": r["row_data"],
                    "policy_iri": r["policy_iri"],
                    "reason": r["reason"],
                    "prohibitions_violated": r["prohibitions_violated_rules"],
                    "permissions_satisfied": r.get("permissions_satisfied_rules", []),
                }
            )

    return deny_details


def detailed_evaluation_from_files(policy_file, SotW_file):
    graph = rdf_utils.load(policy_file)[0]
    policies = SotW_generator.extract_rule_list_from_policy(graph)
    features = SotW_generator.extract_features_list_from_policy(graph)
    FEATURE_TYPE_MAP = {f["iri"]: f["type"] for f in features}

    df = pd.read_csv(SotW_file)

    results = evaluate_all_policies_rowwise(df, policies, OPS_MAP, FEATURE_TYPE_MAP)

    return {
        "overall_compliant": all(r["decision"] != "DENY" for r in results),
        "deny_details": extract_deny_details(results),
        "raw_results": results,
    }

    results = evaluate_all_policies_rowwise(df, policies, OPS_MAP, FEATURE_TYPE_MAP)
def compute_policy_statistics_rowwise(df, policies, OPS_MAP, FEATURE_TYPE_MAP):
    """
    Returns a list of results per row, per policy:
    {
        'row_index': i,
        'policy_iri': policy_iri,
        'permission_satisfied_percentage': float,
        'prohibition_violated_percentage': float,
        'permissions_satisfied_indices': [...],
        'prohibitions_violated_indices': [...]
    }
    """
    results = []

    for policy_idx, policy in enumerate(policies):
        policy_iri = policy.get("policy_iri", f"policy_{policy_idx}")
        num_permissions = len(policy.get("permissions", []))
        num_prohibitions = len(policy.get("prohibitions", []))

        for idx, row in df.iterrows():
            satisfied_perm_indices = [
                i for i, rule in enumerate(policy.get("permissions", []))
                if eval_rule(row, rule, OPS_MAP, FEATURE_TYPE_MAP)
            ]
            violated_prohib_indices = [
                i for i, rule in enumerate(policy.get("prohibitions", []))
                if eval_rule(row, rule, OPS_MAP, FEATURE_TYPE_MAP)
            ]

            perm_percentage = round(
                len(satisfied_perm_indices) / num_permissions * 100, 2
            ) if num_permissions > 0 else 0.0

            prohib_percentage = round(
                len(violated_prohib_indices) / num_prohibitions * 100, 2
            ) if num_prohibitions > 0 else 0.0

            results.append({
                "row_index": idx,
                "policy_iri": policy_iri,
                "permission_satisfied_percentage": perm_percentage,
                "prohibition_violated_percentage": prohib_percentage,
                "permissions_satisfied_indices": satisfied_perm_indices,
                "prohibitions_violated_indices": violated_prohib_indices
            })

    return results

def compute_statistics_from_files(policy_file, SotW_file):
    graph = rdf_utils.load(policy_file)[0]
    policies = SotW_generator.extract_rule_list_from_policy(graph)
    features = SotW_generator.extract_features_list_from_policy(graph)
    FEATURE_TYPE_MAP = {f["iri"]: f["type"] for f in features}
    df = pd.read_csv(SotW_file)

    return compute_policy_statistics_rowwise(df, policies, OPS_MAP, FEATURE_TYPE_MAP)
# print("Evaluation: "+str(evaluate_ODRL_from_files("example_policies/exampleEvaluationPolicy.ttl","example_policies/exampleSotW.csv")))
