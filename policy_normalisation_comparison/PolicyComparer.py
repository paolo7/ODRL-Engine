from ContractParser import ContractParser
from GraphParser import GraphParser
import Utils


class PolicyComparer:

    @staticmethod
    def compare(filepath1, filepath2):
        # Load contracts from local files as RDF graphs.
        parser1 = ContractParser()
        parser1.load(filepath1)
        parser2 = ContractParser()
        parser2.load(filepath2)

        # Create a map between left operands and respective sets of constant values.
        values_per_constraints_1 = parser1.get_values_from_constraints()
        values_per_constraints_2 = parser2.get_values_from_constraints()

        # Merge these maps to use when splitting intervals.
        merged_values = Utils.merge_key_multisets(values_per_constraints_1, values_per_constraints_2)

        # Convert RDF graphs into Python data structures
        graph_parser1 = GraphParser(parser1.contract_graph)
        graph_parser2 = GraphParser(parser2.contract_graph)
        policy1 = graph_parser1.parse()
        policy2 = graph_parser2.parse()

        # Normalise logical constraints to sets of rules, and reformulate simple constraints.
        policy1 = policy1.normalise()
        policy2 = policy2.normalise()

        if len(merged_values) == 0:
            normal_policy1 = policy1
            normal_policy2 = policy2
        else:
            # Split intervals using the merged map.
            normal_policy1 = policy1.split_intervals(merged_values)
            normal_policy2 = policy2.split_intervals(merged_values)

        # Compute the effective policies by removing permissions that match prohibitions.
        effective_policy1 = PolicyComparer.diff(normal_policy1.permission, normal_policy1.prohibition)
        effective_policy2 = PolicyComparer.diff(normal_policy2.permission, normal_policy2.prohibition)

        #TODO: Add a check here that if an effective policy has no permissions, then nothing is contained in it.

        # Compute the overlap between policies, and two-way containment.
        ov = PolicyComparer.overlap(effective_policy1, effective_policy2)
        diff1 = PolicyComparer.diff(effective_policy1, effective_policy2)
        diff2 = PolicyComparer.diff(effective_policy2, effective_policy1)

        return ov, len(diff1) == 0, len(diff2) == 0

    @staticmethod
    def overlap(rule_list1, rule_list2):
        ans = []
        for rule1 in rule_list1:
            for rule2 in rule_list2:
                if rule1.equiv(rule2):
                    ans.append(rule1)
        return ans

    @staticmethod
    def diff(rule_list1, rule_list2):
        ans = []
        for rule1 in rule_list1:
            broken = False
            for rule2 in rule_list2:
                if rule1.equiv(rule2):
                    broken = True
                    break
            if not broken:
                ans.append(rule1)
        return ans