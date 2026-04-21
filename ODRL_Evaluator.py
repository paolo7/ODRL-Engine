from pyexpat import features
import Evaluation.evaluator_functions
import rdf_utils
import SotW_generator
import pandas as pd
import validate
import operator
import sys

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




# def eval_rule(row, rule, OPS_MAP, FEATURE_TYPE_MAP):
#     return all(eval_constraint(row, c, OPS_MAP, FEATURE_TYPE_MAP) for c in rule)

def eval_rule(row, rule, OPS_MAP, FEATURE_TYPE_MAP):

    # 🔒 ensure rule is dict and has conditions
    if not isinstance(rule, dict):
        return False

    conditions = rule.get("conditions", [])

    if not isinstance(conditions, list):
        return False

    return all(
        eval_constraint(row, c, OPS_MAP, FEATURE_TYPE_MAP)
        for c in conditions
    )


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
    print("\n Results....")
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

def compute_temporal_tracking_from_files(policy_file, SotW_file):

    # 1. Load RDF policy graph
    graph = rdf_utils.load(policy_file)[0]

    # 2. Extract policies
    policies = SotW_generator.extract_rule_list_from_policy(graph)

    # 3. Extract feature metadata
    features = SotW_generator.extract_features_list_from_policy(graph)

    FEATURE_TYPE_MAP = {
        f["iri"]: f["type"] for f in features
    }

    # 4. Load CSV data (state of the world)
    df = pd.read_csv(SotW_file)

    # 5. Call core evaluation engine
    return evaluate_policy_with_tracking(
        df,
        policies,
        OPS_MAP,
        FEATURE_TYPE_MAP
    )

# Compute temporal tracking per rule (matches count, earliest/latest match, required status) keep track of time
def evaluate_policy_with_tracking(df, policies, OPS_MAP, FEATURE_TYPE_MAP):
    """
    Full row-by-row evaluation with temporal tracking + validity report
    """

    def init_tracking(rule, rule_type, parent=None):
        return {
            "type": rule_type,
            "parent": parent,
            "rule": rule,
            "matches_count": 0,
            "earliestMatch": None,
            "latestMatch": None,
            "required": 1
        }

    # ---------- HELPERS ----------
    def check_match(row, entry, OPS_MAP, FEATURE_TYPE_MAP):
        if eval_rule(row, entry["rule"], OPS_MAP, FEATURE_TYPE_MAP):
            entry["matches_count"] += 1

            row_time = row.get("http://www.w3.org/ns/odrl/2/dateTime")

            if entry["earliestMatch"] is None:
                entry["earliestMatch"] = row_time

            entry["latestMatch"] = row_time
            entry["required"] = 0
            return True
        return False

    def extract_all(rule, parent_key, tracking, prefix, key_name):
        for j, r in enumerate(rule.get(key_name, [])):
            key = f"{prefix}_{key_name}_{j}"
            tracking[key] = init_tracking(r, key_name[:-1], parent=parent_key)
            extract_all(r, key, tracking, key, key_name)

    # ---------- MAIN ----------
    results = []

    for policy_idx, policy in enumerate(policies):

        policy_iri = policy.get("policy_iri", f"policy_{policy_idx}")

        rule_tracking_permissions = {}
        rule_tracking_duties = {}
        rule_tracking_prohibitions = {}
        rule_tracking_consequences = {}
        rule_tracking_remedies = {}

        # ---------- INIT ----------
        for i, rule in enumerate(policy.get("permissions", [])):
            perm_key = f"perm_{i}"
            rule_tracking_permissions[perm_key] = init_tracking(rule, "permission")

            extract_all(rule, perm_key, rule_tracking_duties, perm_key, "duties")
            extract_all(rule, perm_key, rule_tracking_consequences, perm_key, "consequences")

        for i, rule in enumerate(policy.get("prohibitions", [])):
            prohib_key = f"prohib_{i}"
            rule_tracking_prohibitions[prohib_key] = init_tracking(rule, "prohibition")

            extract_all(rule, prohib_key, rule_tracking_remedies, prohib_key, "remedies")

        # ---------- STATE ----------
        rows_violating_permissions = []
        rows_violating_prohibitions = []
        validity = 1

        # ---------- ROW LOOP ----------
        for _, row in df.iterrows():

            matched_permissions = []
            matched_prohibitions = []

            # ---- PERMISSIONS ----
            for key, entry in rule_tracking_permissions.items():
                if check_match(row, entry, OPS_MAP, FEATURE_TYPE_MAP):
                    matched_permissions.append(key)

                    # check duties
                    related_duties = [
                        d for d in rule_tracking_duties.values()
                        if d["parent"] == key
                    ]

                    for duty in related_duties:
                        duty_match = check_match(row, duty, OPS_MAP, FEATURE_TYPE_MAP)

                        if not duty_match:
                            # check consequences
                            related_cons = [
                                c for c in rule_tracking_consequences.values()
                                if c["parent"] == duty
                            ]

                            if not related_cons:
                                rows_violating_permissions.append(row)
                                validity = 0
                            else:
                                duty["required"] = 1
                                for c in related_cons:
                                    c["required"] = 1

            if not matched_permissions:
                rows_violating_permissions.append(row)
                validity = 0

            # ---- DUTIES (independent tracking) ----
            for duty in rule_tracking_duties.values():
                check_match(row, duty, OPS_MAP, FEATURE_TYPE_MAP)

            # ---- PROHIBITIONS ----
            for key, entry in rule_tracking_prohibitions.items():
                if check_match(row, entry, OPS_MAP, FEATURE_TYPE_MAP):
                    matched_prohibitions.append(key)

            # ---- PROHIBITION VIOLATIONS ----
            for key in matched_prohibitions:
                related_remedies = [
                    r for r in rule_tracking_remedies.values()
                    if r["parent"] == key
                ]

                if not related_remedies:
                    rows_violating_prohibitions.append(row)
                    validity = 0
                else:
                    for r in related_remedies:
                        r["required"] = 1

        # ---------- FINAL CHECK ----------
        temporary_validity = validity

        obligations_not_satisfied = []
        unfulfilled_duties_with_consequences = []
        unfulfilled_consequences = []
        unfulfilled_remedies = []

        # obligations = duties without parent
        for duty in rule_tracking_duties.values():
            if duty["parent"] is None and duty["matches_count"] < 1:
                obligations_not_satisfied.append(duty)
                temporary_validity = 0

        for duty in rule_tracking_duties.values():
            if duty["required"] == 1:
                unfulfilled_duties_with_consequences.append(duty)
                temporary_validity = 0

        for c in rule_tracking_consequences.values():
            if c["required"] == 1:
                unfulfilled_consequences.append(c)
                temporary_validity = 0

        for r in rule_tracking_remedies.values():
            if r["required"] == 1:
                unfulfilled_remedies.append(r)
                temporary_validity = 0

        # ---------- RESULT ----------
        results.append({
            "policy_iri": policy_iri,
            "evaluation_state": {
                "permissions": rule_tracking_permissions,
                "duties": rule_tracking_duties,
                "prohibitions": rule_tracking_prohibitions,
                "consequences": rule_tracking_consequences,
                "remedies": rule_tracking_remedies
            },
            "temporary_validity": temporary_validity,
            "rows_violating_permissions": rows_violating_permissions,
            "rows_violating_prohibitions": rows_violating_prohibitions,
            "obligations_not_satisfied": obligations_not_satisfied,
            "unfulfilled_duties_with_consequences": unfulfilled_duties_with_consequences,
            "unfulfilled_consequences": unfulfilled_consequences,
            "unfulfilled_remedies": unfulfilled_remedies
        })

    return results
def build_tracking_report(results):
    report = []

    for r in results:
        policy_id = r["policy_iri"]
        state = r["evaluation_state"]

        permissions = state["permissions"]
        duties = state["duties"]
        prohibitions = state["prohibitions"]
        consequences = state["consequences"]
        remedies = state["remedies"]

        lines = []
        lines.append(f"\n==============================")
        lines.append(f" POLICY: {policy_id}")
        lines.append(f"Validity: {' VALID' if r['temporary_validity'] else '❌ INVALID'}")
        lines.append(f"==============================\n")

        # ---------- PERMISSIONS ----------
        lines.append(" PERMISSIONS")
        for k, v in permissions.items():
            lines.append(
                f"  • {k} | matches={v['matches_count']} | "
                f"first={v['earliestMatch']} | last={v['latestMatch']}"
            )

        # ---------- PROHIBITIONS ----------
        lines.append("\n PROHIBITIONS")
        for k, v in prohibitions.items():
            lines.append(
                f"  • {k} | matches={v['matches_count']} | "
                f"required={v['required']}"
            )

        # ---------- DUTIES ----------
        lines.append("\n DUTIES")
        for k, v in duties.items():
            status = "DONE" if v["matches_count"] > 0 else "MISSING"
            lines.append(
                f"  • {k} | {status} | matches={v['matches_count']}"
            )

        # ---------- CONSEQUENCES ----------
        lines.append("\n CONSEQUENCES (required ones)")
        for c in consequences.values():
            if c["required"] == 1:
                lines.append(f"  • {c['rule']}")

        # ---------- REMEDIES ----------
        lines.append("\n REMEDIES (required ones)")
        for r2 in remedies.values():
            if r2["required"] == 1:
                lines.append(f"  • {r2['rule']}")

        # ---------- VIOLATIONS ----------
        lines.append("\n VIOLATIONS")

        lines.append(f"  Permissions violations: {len(r['rows_violating_permissions'])}")
        lines.append(f"  Prohibitions violations: {len(r['rows_violating_prohibitions'])}")

        report.append("\n".join(lines))

    return "\n\n".join(report)