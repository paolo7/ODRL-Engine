import rdf_utils
import SotW_generator
import pandas as pd
import os
import shutil
import json
import math
import operator


# if dateutil is not install then install it using (!pip install python-dateutil)
from dateutil import parser
import uuid

OPS_MAP = {
    "http://www.w3.org/ns/odrl/2/eq": operator.eq,
    "http://www.w3.org/ns/odrl/2/neq": operator.ne,
    "http://www.w3.org/ns/odrl/2/lt": operator.lt,
    "http://www.w3.org/ns/odrl/2/lteq": operator.le,
    "http://www.w3.org/ns/odrl/2/gt": operator.gt,
    "http://www.w3.org/ns/odrl/2/gteq": operator.ge,
    # Missing operators:
    # odrl.isAnyOf: lambda a, b: a in b,
    # odrl.isNoneOf: lambda a, b: a not in b,
    # odrl.hasPart: lambda a, b: all(item in a for item in b) if isinstance(b, list) else b in a,
    # odrl.isPartOf: lambda a, b: all(item in b for item in a) if isinstance(a, list) else a in b,
    # odrl.isAllOf: lambda a, b: set(a) == set(b) if isinstance(a, list) and isinstance(b, list) else False,
}

def evaluate_ODRL_from_files_merge_policies(policy_files, SotW_file):
    graph_rules = []
    features = []
    for file in policy_files:
        graph = rdf_utils.load(file)[0]
        graph_rules.append(SotW_generator.extract_rule_list_from_policy(graph))
        features.append(SotW_generator.extract_features_list_from_policy(graph))

    # temporary merge code, TODO should be updated when a more stable merge function is created
    merged_permissions = []
    merged_prohibitions = []
    merged_obligations = []
    for policy_list in graph_rules:  # each element is a list of policies
        for policy in policy_list:
            merged_permissions.extend(policy.get("permissions", []))
            merged_prohibitions.extend(policy.get("prohibitions", []))
            merged_obligations.extend(policy.get("obligations", []))

    merged_policy_iri = graph_rules[0][0]["policy_iri"]
    merged_graph_rules = [{
        "policy_iri": merged_policy_iri,
        "permissions": merged_permissions,
        "prohibitions": merged_prohibitions,
        "obligations": merged_obligations
    }]
    merged_feature_map = {}

    for feature_list in features:
        for f in feature_list:
            iri = f["iri"]
            if iri not in merged_feature_map:
                merged_feature_map[iri] = f["type"]

    df = pd.read_csv(SotW_file)

    return evaluate_ODRL_on_dataframe(merged_graph_rules[0], df, merged_feature_map)

def eval_count(value, constraint, OPS_MAP):
    left, op_symbol, right = constraint

    if left != "http://www.w3.org/ns/odrl/2/count":
        return False

    if op_symbol not in OPS_MAP:
        return False

    try:
        return OPS_MAP[op_symbol](float(value), float(right))
    except Exception:
        return False

def eval_constraint(row, rule, constraint, OPS_MAP, FEATURE_TYPE_MAP):

    left, op_symbol, right = constraint  
    # Split it for spaces
    if left == "http://www.w3.org/ns/odrl/2/count":
        # Count will be handled separately.
        return True
    
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

    if pd.isna(value) or value == "":
        return False

    #if value is None or value == "":
    #    return False

    if op_symbol not in OPS_MAP:
        return False

    column_type = FEATURE_TYPE_MAP.get(left)

    # TODO: fix issues with timezones.
    # --- 1️⃣ DateTime handling ---
    if column_type == "http://www.w3.org/2001/XMLSchema#dateTime" or left == "http://www.w3.org/ns/odrl/2/dateTime":
        try:
            left_date = parser.parse(str(value)).timestamp()
            right_date = parser.parse(str(right)).timestamp()

            # This is important in the case where we normalised.
            # left_date = datetime.fromisoformat(str(value))
            # right_date = datetime.fromisoformat(str(right))

            # Normalize timezone (avoid naive vs aware errors)
            # if left_date.tzinfo and not right_date.tzinfo:
            #     right_date = right_date.replace(tzinfo=left_date.tzinfo)
            # elif right_date.tzinfo and not left_date.tzinfo:
            #     left_date = left_date.replace(tzinfo=right_date.tzinfo)
            ans = OPS_MAP[op_symbol](left_date, right_date)
            return ans

        except Exception:
            return False

    # --- 2️⃣ Equality / inequality → string compare ---
    if op_symbol in ("http://www.w3.org/ns/odrl/2/eq", "http://www.w3.org/ns/odrl/2/neq"):
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

def eval_rule(row, rule, OPS_MAP, FEATURE_TYPE_MAP):

    if not isinstance(rule, dict):
        return False

    conditions = rule.get("conditions", [])
 
    if not isinstance(conditions, list):
        return False

    return all(
        eval_constraint(row, rule, c, OPS_MAP, FEATURE_TYPE_MAP)
        for c in conditions
    )

def initialise_evaluation_state(policy):

    if isinstance(policy, list):
        policy = policy[0]

    def init_rule(rule):
        return {
            "rule_id": rule.get("id", str(uuid.uuid4())),
            "matches_count": 0,
            "match_count": 0,  # 🔧 compatibility with old tests
            "earliestMatch": None,
            "latestMatch": None,
            "conditions": rule.get("conditions", []),
            "required": 0
        }

    def init_duty(duty):
        return {
            **init_rule(duty),
            "consequences": [init_rule(c) for c in duty.get("consequences", [])]
        }

    def init_prohibition(rule):
        return {
            **init_rule(rule),
            "remedies": [init_rule(r) for r in rule.get("remedies", [])]
        }

    state = {
        "policy_iri": policy.get("policy_iri"),
        "permissions": [],
        "prohibitions": [],
        "obligations": [],
        "rows_violating_permissions": [],
        "rows_violating_prohibitions": []
    }

    for p in policy.get("permissions", []):
        state["permissions"].append({
            **init_rule(p),
            "duties": [init_duty(d) for d in p.get("duties", [])]
        })

    for pr in policy.get("prohibitions", []):
        state["prohibitions"].append(init_prohibition(pr))

    for ob in policy.get("obligations", []):
        state["obligations"].append(init_rule(ob))

    return state

def check_match(row, rule_state, OPS_MAP, FEATURE_TYPE_MAP):

    if eval_rule(row, rule_state, OPS_MAP, FEATURE_TYPE_MAP):

        rule_state["matches_count"] += 1
        rule_state["match_count"] = rule_state["matches_count"]  # 🔧 compatibility

        time_val = row.get("http://www.w3.org/ns/odrl/2/dateTime")

        if time_val is not None:
            try:
                time_val = parser.parse(str(time_val))
            except:
                time_val = None

        if rule_state["earliestMatch"] is None:
            rule_state["earliestMatch"] = time_val

        rule_state["latestMatch"] = time_val

        if rule_state.get("required", 0) == 1:
            rule_state["required"] = 0

        return True

    return False

def evaluate_ODRL_on_dataframe(policy, df, FEATURE_TYPE_MAP, evaluation_state=None):

    if isinstance(policy, list):
        policy = policy[0]

    # Ensure time ordering
    DT_COL = "http://www.w3.org/ns/odrl/2/dateTime"

    if DT_COL in df.columns:
        df[DT_COL] = pd.to_datetime(df[DT_COL], errors="coerce", utc=True)
        df = df.sort_values(by=DT_COL, ascending=True)

    if evaluation_state is None:
        evaluation_state = initialise_evaluation_state(policy)

    validity = 1

    for idx, row in df.iterrows():

        matched_permissions = []
        matched_prohibitions = []

        # ----------------------------------------
        # 1) MATCH ALL RULES (INCLUDING DUTIES ETC.)
        # ----------------------------------------

        # Permissions
        for p in evaluation_state["permissions"]:
            if check_match(row, p, OPS_MAP, FEATURE_TYPE_MAP):
                matched_permissions.append(p)

            # Duties ALWAYS evaluated
            for d in p.get("duties", []):
                check_match(row, d, OPS_MAP, FEATURE_TYPE_MAP)

                for c in d.get("consequences", []):
                    check_match(row, c, OPS_MAP, FEATURE_TYPE_MAP)

        # Prohibitions + remedies
        for f in evaluation_state["prohibitions"]:
            if check_match(row, f, OPS_MAP, FEATURE_TYPE_MAP):
                matched_prohibitions.append(f)

            for r in f.get("remedies", []):
                check_match(row, r, OPS_MAP, FEATURE_TYPE_MAP)

        # Obligations
        for o in evaluation_state["obligations"]:
            check_match(row, o, OPS_MAP, FEATURE_TYPE_MAP)

        # ----------------------------------------
        # 2) PERMISSION VIOLATION
        # ----------------------------------------
        if not matched_permissions:
            evaluation_state["rows_violating_permissions"].append(idx)
            validity = 0

        # ----------------------------------------
        # 3) DUTIES / CONSEQUENCES
        # ----------------------------------------
        for p in matched_permissions:
            for d in p.get("duties", []):

                if d["matches_count"] == 0 and d.get("required", 0) == 0:

                    if not d.get("consequences"):
                        evaluation_state["rows_violating_permissions"].append(idx)
                        validity = 0
                    else:
                        d["required"] = 1
                        for c in d["consequences"]:
                            c["required"] = 1

        # ----------------------------------------
        # 4) PROHIBITIONS + REMEDIES
        # ----------------------------------------
        for f in matched_prohibitions:

            remedies = f.get("remedies", [])

            if not remedies:
                evaluation_state["rows_violating_prohibitions"].append(idx)
                validity = 0
            else:
                for r in remedies:
                    r["required"] = 1

    # ----------------------------------------
    # 5) POST PROCESSING
    # ----------------------------------------


    temporary_validity = validity
    if (
            len(evaluation_state["rows_violating_permissions"]) > 0
            or len(evaluation_state["rows_violating_prohibitions"]) > 0
    ):
        temporary_validity = 0

    obligations_not_satisfied = []
    unfulfilled_duties = []
    unfulfilled_consequences = []
    unfulfilled_remedies = []

    # ---- OBLIGATIONS ----
    for o in evaluation_state["obligations"]:
        if o["matches_count"] < 1:
            obligations_not_satisfied.append(o)
            temporary_validity = 0

    # ---- DUTIES + CONSEQUENCES ----
    for p in evaluation_state["permissions"]:
        for d in p.get("duties", []):

            if d.get("required") == 1:
                unfulfilled_duties.append(d)
                temporary_validity = 0

            for c in d.get("consequences", []):
                if c.get("required") == 1:
                    unfulfilled_consequences.append(c)
                    temporary_validity = 0

    # ---- REMEDIES ----
    for f in evaluation_state["prohibitions"]:
        for r in f.get("remedies", []):
            if r.get("required") == 1:
                unfulfilled_remedies.append(r)
                temporary_validity = 0

    # ---- COUNT CONSTRAINTS ----
    for p in evaluation_state["permissions"]:
        for c in p.get("conditions", []):
            if c[0] == "http://www.w3.org/ns/odrl/2/count":
                if not eval_count(p["matches_count"], c, OPS_MAP):
                    temporary_validity = 0

    for f in evaluation_state["prohibitions"]:
        for c in f.get("conditions", []):
            if c[0] == "http://www.w3.org/ns/odrl/2/count":
                if eval_count(f["matches_count"], c, OPS_MAP):
                    temporary_validity = 0

    return (
        evaluation_state,
        temporary_validity,
        evaluation_state["rows_violating_permissions"],
        evaluation_state["rows_violating_prohibitions"],
        obligations_not_satisfied,
        unfulfilled_duties,
        unfulfilled_consequences,
        unfulfilled_remedies
    )

def evaluate_ODRL_from_files(policy_file, SotW_file, evaluation_state=None, normalise=False):
    graph = rdf_utils.load(policy_file)[0]
    if normalise:
        graph = rdf_utils.load_normalise(policy_file)[0]
    policies = SotW_generator.extract_rule_list_from_policy(graph)
    features = SotW_generator.extract_features_list_from_policy(graph)

    FEATURE_TYPE_MAP = {f["iri"]: f["type"] for f in features}
    df = pd.read_csv(SotW_file)

    return evaluate_ODRL_on_dataframe(policies[0], df, FEATURE_TYPE_MAP, evaluation_state)



def evaluate_ODRL_from_files_streaming(policy_file, SotW_file, max_rows_per_SotW=1, normalise=False):

    STREAM_DIR = "stream_simulation"

    # ----------------------------------------
    # 1) PREPARE STREAM DIRECTORY
    # ----------------------------------------
    if os.path.exists(STREAM_DIR):
        shutil.rmtree(STREAM_DIR)
    os.makedirs(STREAM_DIR)

    # ----------------------------------------
    # 2) LOAD POLICY + FEATURES
    # ----------------------------------------
    graph = rdf_utils.load(policy_file)[0]
    if normalise:
        graph = rdf_utils.load_normalise(policy_file)[0]

    policies = SotW_generator.extract_rule_list_from_policy(graph)
    features = SotW_generator.extract_features_list_from_policy(graph)

    FEATURE_TYPE_MAP = {f["iri"]: f["type"] for f in features}

    # ----------------------------------------
    # 3) LOAD + SORT SOTW
    # ----------------------------------------
    df = pd.read_csv(SotW_file)

    DT_COL = "http://www.w3.org/ns/odrl/2/dateTime"

    if DT_COL in df.columns:
        df[DT_COL] = pd.to_datetime(df[DT_COL], errors="coerce", utc=True)
        df = df.sort_values(by=DT_COL, ascending=True)

    # ----------------------------------------
    # 4) SPLIT INTO STREAM FILES
    # ----------------------------------------
    total_rows = len(df)
    num_chunks = math.ceil(total_rows / max_rows_per_SotW)

    stream_files = []

    for i in range(num_chunks):
        start = i * max_rows_per_SotW
        end = start + max_rows_per_SotW

        chunk_df = df.iloc[start:end]

        file_path = os.path.join(STREAM_DIR, f"stream{i}.csv")
        chunk_df.to_csv(file_path, index=False)

        stream_files.append(file_path)

    # ----------------------------------------
    # 5) PROCESS STREAM FILES SEQUENTIALLY
    # ----------------------------------------
    evaluation_state = None
    result = None

    state_file = os.path.join(STREAM_DIR, "evaluation_state.json")

    for i, stream_file in enumerate(stream_files):

        # Load previous state if exists
        if os.path.exists(state_file):
            with open(state_file, "r") as f:
                evaluation_state = json.load(f)

        # Run evaluation
        #result = evaluate_ODRL_on_dataframe(
        #    policies[0],
        #    pd.read_csv(stream_file),
        #    FEATURE_TYPE_MAP,
        #    evaluation_state
        #)
        result = evaluate_ODRL_from_files(
            policy_file,
            stream_file,
            evaluation_state=evaluation_state,
            normalise=normalise
        )

        # Save updated state
        evaluation_state = result[0]

        with open(state_file, "w") as f:
            json.dump(evaluation_state, f, default=str, indent=2)

    # ----------------------------------------
    # 6) RETURN FINAL RESULT
    # ----------------------------------------
    return result