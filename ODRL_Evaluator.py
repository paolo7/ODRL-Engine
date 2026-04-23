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
    # Split it for spaces
    
    if left in row:
        resolved_left = left
    else:
        if isinstance(left, str):
            parts = left.split()

            resolved_left = None
            for part in reversed(parts):
                if part in row:
                    resolved_left = part
                    break

            if resolved_left is None:
                return False
    left = resolved_left


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
        try:
            return OPS_MAP[op_symbol](float(value), float(right))
        except Exception:
            return OPS_MAP[op_symbol](str(value), str(right))

    # --- 3️⃣ Numeric comparison ---
    try:
        #print("Value ")
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

# def compute_temporal_tracking_from_files(policy_file, SotW_file):

#     graph = rdf_utils.load(policy_file)[0]
#     policies = SotW_generator.extract_rule_list_from_policy(graph)
#     features = SotW_generator.extract_features_list_from_policy(graph)

#     FEATURE_TYPE_MAP = {f["iri"]: f["type"] for f in features}

#     df = pd.read_csv(SotW_file)

#     if "dateTime" in df.columns:
#         df["dateTime"] = pd.to_datetime(df["dateTime"], errors="coerce")

#     duties_results = []

#     for policy_idx, policy in enumerate(policies):

#         permissions = policy.get("permissions", [])
#         permission_duties_results = []   # ✅ list
#         permission_prohabation_results=[]

#         for perm_idx, permission in enumerate(permissions):

#             permission_duties = evaluate_permission_duties(
#                 permission_id=permission.get("id", perm_idx),
#                 df=df,
#                 duties=permission.get("duties", []),
#                 policy=policy,
#                 OPS_MAP=OPS_MAP,
#                 FEATURE_TYPE_MAP=FEATURE_TYPE_MAP
#             )

#             # ✅ FIX: append to the list
#             permission_duties_results.append(permission_duties)

#         # ✅ FIX: use the correct variable
        
#          duties_results.append({
#             "policy_id": policy_idx,
#             "policy_iri": policy.get("policy_iri", "unknown_policy"),
#             "permissions_duties": permission_duties_results
#         })
       
#         for idx, row in df.iterrows():
#             permission_prohabation_results = evaluate_row_policy_permission_prohabition(idx, row, policy, OPS_MAP, FEATURE_TYPE_MAP)
            
def compute_temporal_tracking_from_files(policy_file, SotW_file):

    graph = rdf_utils.load(policy_file)[0]
    policies = SotW_generator.extract_rule_list_from_policy(graph)
    features = SotW_generator.extract_features_list_from_policy(graph)

    FEATURE_TYPE_MAP = {f["iri"]: f["type"] for f in features}

    df = pd.read_csv(SotW_file)

    if "dateTime" in df.columns:
        df["dateTime"] = pd.to_datetime(df["dateTime"], errors="coerce")

    all_results = []

    for policy_idx, policy in enumerate(policies):

        permissions = policy.get("permissions", [])

        permission_duties_results = []
        permission_prohabation_results = []   # ✅ FIXED

        # ---- DUTIES ----
        for perm_idx, permission in enumerate(permissions):

            permission_duties = evaluate_permission_duties(
                permission_id=permission.get("id", perm_idx),
                df=df,
                duties=permission.get("duties", []),
                policy=policy,
                OPS_MAP=OPS_MAP,
                FEATURE_TYPE_MAP=FEATURE_TYPE_MAP
            )
            if permission_duties is not None:
                permission_duties_results.append(permission_duties)

        # ---- PERMISSION PROHIBITION / ROW LEVEL ----
        for idx, row in df.iterrows():

            result = evaluate_row_policy_permission_prohabition(
                idx, row, policy,OPS_MAP, FEATURE_TYPE_MAP, permission_duties_results
            )

            permission_prohabation_results.append(result)  # ✅ FIXED

        # ---- FINAL STORE ----
        all_results.append({
            "policy_id": policy_idx,
            "policy_iri": policy.get("policy_iri", "unknown_policy"),

            "permissions_duties": permission_duties_results,
            "row_permission_prohibitions": permission_prohabation_results
        })
        
    # result=build_tracking_report(all_results)
    return all_results
       
        

    # return all_results
def evaluate_permission_duties(permission_id, df, duties, policy, OPS_MAP, FEATURE_TYPE_MAP):
    from collections import defaultdict
    
    if not duties:
        return None
    
    if not isinstance(duties, list):
        duties = [duties]

    duty_map = defaultdict(list)
    all_times = []
    


    for duty_idx, duty in enumerate(duties):

        for row_idx, row in df.iterrows():

            if eval_rule(row, duty, OPS_MAP, FEATURE_TYPE_MAP):

                time_val = row.get("http://www.w3.org/ns/odrl/2/dateTime", None)

                duty_map[duty_idx].append({
                    "row_index": row_idx,
                    "time": time_val
                })

                if time_val is not None:
                    all_times.append(time_val)

        # ✅ If duty never satisfied → explicitly mark it
        if duty_idx not in duty_map:
            duty_map[duty_idx] = []   # empty = not satisfied

    return {
        "permission_id": permission_id,
        "policy_iri": policy.get("policy_iri", "unknown_policy"),
        "duties": dict(duty_map),
        "stats": {
            "total_duties_satisfied": sum(1 for v in duty_map.values() if len(v) > 0),
            "total_rows_matched": sum(len(v) for v in duty_map.values()),
            "earliest_time": min(all_times) if all_times else None,
            "latest_time": max(all_times) if all_times else None
        }
    }

def evaluate_row_policy_permission_prohabition(idx, row, policy, OPS_MAP, FEATURE_TYPE_MAP, duties):

    permission_matches = []
    satisfied_permissions = []
    prohibition_matches = []
    violated_prohibitions = []

    # 🔹 get time once
    time_val = row.get("http://www.w3.org/ns/odrl/2/dateTime", None)

    permission_times = []
    prohibition_times = []
    
    # ---- check permissions ----
    for i, rule in enumerate(policy.get("permissions", [])):
        
     
        
        if eval_rule(row, rule, OPS_MAP, FEATURE_TYPE_MAP):
           
              duty_evaluated = False
              if duties is None: # if no duty is associated with it 
                  duty_evaluated=True
              for perm_duty in duties: #  iterate all duties which contains permision ID -Rows which satisfying the duty 
                if perm_duty["permission_id"] == i: # If current permission and duty permission is same 
                    duty_map = perm_duty.get("duties", {}) # Fetch the map of the duty
                    #print(duty_map)
                    duty_evaluated = check_duty_map(duty_map, time_val) # Look to this method here we first check the if any duty has not satified than false ; again we check time form map checked indiviually against time_val if earliest time of duty_map<time 
                    # if all(len(rows) > 0 for rows in duty_map.values()): # is it checking all of the have length greater than 1 
                    #     earliest = perm_duty.get("stats", {}).get("earliest_time") #
                    #     if earliest is None or time_val is None or time_val >= earliest:
                    #         duty_evaluated = True
                else:
                    duty_evaluated=True
                if(duty_evaluated):
                    permission_matches.append(i)
                    satisfied_permissions.append(rule)
                if time_val is not None:
                    permission_times.append(time_val)
        # else:
        #     permission_matches.append(i)
        #     satisfied_permissions.append(rule)
        

    # ---- check prohibitions ----
    for i, rule in enumerate(policy.get("prohibitions", [])):
        if eval_rule(row, rule, OPS_MAP, FEATURE_TYPE_MAP):
            prohibition_matches.append(i)
            violated_prohibitions.append(rule)
            if time_val is not None:
                prohibition_times.append(time_val)

    # ---- decision logic ----
    if prohibition_matches:
        decision = "DENY"
        reason = "Prohibition violated"
    elif permission_matches:
        decision = "ALLOW"
        reason = "Permission satisfied"
    else:
        decision = "DENY"
        reason = "No permission satisfied"

    # ---- stats ----
    permission_stats = {
        "count": len(permission_matches),
        "earliest_time": min(permission_times) if permission_times else None,
        "latest_time": max(permission_times) if permission_times else None
    }

    prohibition_stats = {
        "count": len(prohibition_matches),
        "earliest_time": min(prohibition_times) if prohibition_times else None,
        "latest_time": max(prohibition_times) if prohibition_times else None
    }

    return {
        "decision": decision,
        "reason": reason,
        "Row_ID": idx,
        "permissions_satisfied_indices": permission_matches,
        "permissions_satisfied_rules": satisfied_permissions,

        "prohibitions_violated_indices": prohibition_matches,
        "prohibitions_violated_rules": violated_prohibitions,

        # ✅ NEW
        "permission_stats": permission_stats,
        "prohibition_stats": prohibition_stats,
    }
    
def check_duty_map(duty_map, time_val):
    
    for duty_idx, rows in duty_map.items():

        # ❌ rule 1: duty must have at least one match
        if len(rows) == 0:
            return False

        # ❌ rule 2: check time constraint per duty
        times = [r["time"] for r in rows if r["time"] is not None]

        if not times:
            return False

        earliest = min(times)

        if time_val is not None and time_val < earliest:
            return False

    # ✅ if ALL duties pass
    return True

def build_tracking_report(tracking_results):

    if not isinstance(tracking_results, list):
        return f"ERROR: expected list, got {type(tracking_results)}"

    lines = []

    lines.append("\n" + "🧭" * 30)
    lines.append("      ODRL TEMPORAL TRACKING REPORT")
    lines.append("🧭" * 30)

    for p_idx, policy in enumerate(tracking_results):

        if not isinstance(policy, dict):
            continue

        lines.append("\n" + "═" * 80)
        lines.append(f"📘 POLICY {p_idx}")
        lines.append(f"IRI: {policy.get('policy_iri', 'unknown')}")
        lines.append("═" * 80)

        # ---------------- DUTIES ----------------
        lines.append("\n🟦 DUTIES SUMMARY")

        permissions = policy.get("permissions_duties", [])

        if not permissions:
            lines.append("  ⚠️ No permissions found")
        else:
            for perm in permissions:

                if not isinstance(perm, dict):
                    continue

                perm_id = perm.get("permission_id")

                lines.append(f"\n🔹 Permission {perm_id}")

                duties = perm.get("duties", {})

                if not duties:
                    lines.append("   • No duties satisfied")
                    continue

                for duty_id, rows in duties.items():

                    row_ids = [r.get("row_index") for r in rows if isinstance(r, dict)]
                    times = [r.get("time") for r in rows if isinstance(r, dict) and r.get("time")]

                    start = min(times) if times else "N/A"
                    end = max(times) if times else "N/A"

                    lines.append(
                        f"   • Duty {duty_id}: "
                        f"Rows={row_ids} | Time={start} → {end}"
                    )

                stats = perm.get("stats", {})

                lines.append(
                    f"   📊 Duties={stats.get('total_duties_satisfied', 0)} | "
                    f"Rows={stats.get('total_rows_matched', 0)} | "
                    f"{stats.get('earliest_time')} → {stats.get('latest_time')}"
                )

        # ---------------- ROW LEVEL ----------------
        lines.append("\n🟥 ROW LEVEL DECISIONS")

        rows = policy.get("row_permission_prohibitions", [])

        if not rows:
            lines.append("  ⚠️ No row evaluations found")

        for r in rows:

            if not isinstance(r, dict):
                continue

            decision = r.get("decision")
            reason = r.get("reason")
            row_id = r.get("Row_ID")

            emoji = "🟢" if decision == "ALLOW" else "🔴"

            lines.append(f"\n{emoji} Row {row_id} → {decision}")
            lines.append(f"   Reason: {reason}")

            perm_stats = r.get("permission_stats", {})
            proh_stats = r.get("prohibition_stats", {})

            lines.append(
                f"   Permissions: {perm_stats.get('count', 0)} | "
                f"{perm_stats.get('earliest_time')} → {perm_stats.get('latest_time')}"
            )

            lines.append(
                f"   Prohibitions: {proh_stats.get('count', 0)} | "
                f"{proh_stats.get('earliest_time')} → {proh_stats.get('latest_time')}"
            )

    lines.append("\n" + "🧭" * 30)
    lines.append("          END OF REPORT")
    lines.append("🧭" * 30)

    return "\n".join(lines)
