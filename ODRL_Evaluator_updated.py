import operator
from dateutil import parser
import pandas as pd


DEFAULT_OPS_MAP = {
    "=": operator.eq,
    "!=": operator.ne,
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
}


class ODRLEvaluator:
    """
    Reusable ODRL evaluator.
    Instantiate once and use everywhere.
    """

    def __init__(self, policies, feature_type_map, ops_map=None):
        self.policies = policies
        self.feature_type_map = feature_type_map
        self.ops_map = ops_map or DEFAULT_OPS_MAP

    # -------------------------------------------------
    # Public API
    # -------------------------------------------------

    def evaluate_dataframe(self, df):
        return [
            self._evaluate_row_policy(row, policy, idx)
            for policy in self.policies
            for idx, row in df.iterrows()
        ]

    def evaluate_files(self, policy_loader, policy_file, csv_file):
        graph = policy_loader(policy_file)
        df = pd.read_csv(csv_file)
        return self.evaluate_dataframe(df)

    def compute_statistics(self, df):
        results = []

        for policy_idx, policy in enumerate(self.policies):
            policy_iri = policy.get("policy_iri", f"policy_{policy_idx}")
            permissions = policy.get("permissions", [])
            prohibitions = policy.get("prohibitions", [])

            for idx, row in df.iterrows():
                satisfied_perm = [
                    i for i, rule in enumerate(permissions)
                    if self._eval_rule(row, rule)
                ]

                violated_prohib = [
                    i for i, rule in enumerate(prohibitions)
                    if self._eval_rule(row, rule)
                ]

                results.append({
                    "row_index": idx,
                    "policy_iri": policy_iri,
                    "permission_satisfied_percentage":
                        round(len(satisfied_perm) / len(permissions) * 100, 2)
                        if permissions else 0.0,
                    "prohibition_violated_percentage":
                        round(len(violated_prohib) / len(prohibitions) * 100, 2)
                        if prohibitions else 0.0,
                    "permissions_satisfied_indices": satisfied_perm,
                    "prohibitions_violated_indices": violated_prohib,
                })

        return results

    def overall_compliance(self, df):
        results = self.evaluate_dataframe(df)
        return all(r["decision"] != "DENY" for r in results)

    # -------------------------------------------------
    # Core Evaluation Logic
    # -------------------------------------------------

    def _evaluate_row_policy(self, row, policy, row_index):
        permissions = policy.get("permissions", [])
        prohibitions = policy.get("prohibitions", [])

        satisfied_permissions = [
            rule for rule in permissions if self._eval_rule(row, rule)
        ]

        violated_prohibitions = [
            rule for rule in prohibitions if self._eval_rule(row, rule)
        ]

        if violated_prohibitions:
            decision = "DENY"
            reason = "Prohibition violated"
        elif satisfied_permissions:
            decision = "ALLOW"
            reason = "Permission satisfied"
        else:
            decision = "DENY"
            reason = "No permission satisfied"

        return {
            "row_index": row_index,
            "policy_iri": policy.get("policy_iri", "unknown_policy"),
            "decision": decision,
            "reason": reason,
            "permissions_satisfied_rules": satisfied_permissions,
            "prohibitions_violated_rules": violated_prohibitions,
            "row_data": row.to_dict(),
        }

    def _eval_rule(self, row, rule):
        return all(self._eval_constraint(row, c) for c in rule)

    def _eval_constraint(self, row, constraint):
        left, op_symbol, right = constraint

        if left not in row or op_symbol not in self.ops_map:
            return False

        value = row[left]
        if value in (None, ""):
            return False

        column_type = self.feature_type_map.get(left)

        # --- DateTime handling ---
        if column_type == "http://www.w3.org/2001/XMLSchema#dateTime":
            try:
                left_date = parser.parse(str(value)).date()
                right_date = parser.parse(str(right)).date()
                return self.ops_map[op_symbol](left_date, right_date)
            except Exception:
                return False

        # --- String equality ---
        if op_symbol in ("=", "!="):
            return self.ops_map[op_symbol](str(value), str(right))

        # --- Numeric comparison ---
        try:
            return self.ops_map[op_symbol](float(value), float(right))
        except Exception:
            return False
