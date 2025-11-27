import SotW_generator
from rdflib import Graph
import ODRL_generator
import random

def generate_permission_test_cases(
    test_n,
    # ---- parameters forwarded to generate_ODRL ----
    policy_number=3,
    p_rule_n=6,
    f_rule_n=0,
    o_rule_n=0,
    constants_per_feature=6,
    constraint_number_min=0,
    constraint_number_max=6,
    chance_feature_null=0.5,
    constraint_right_operand_min=0,
    constraint_right_operand_max=100,
    ontology_path="sample_ontologies/ODRL_DPV.ttl",
    # ---- parameters forwarded to SotW_generator.generate_pd_state_of_the_world_from_policies ----
    number_of_records=100,
    chance_feature_empty=0.5,
    use_random_configuration=False
):
    """
    Generate paired ODRL policy graphs and corresponding State-of-the-World (SotW)
    datasets for permission testing. For each test case to generate, one valid and one invalid
    SotW dataset are produced based on the same generated policy.

    The function can optionally randomize key configuration parameters.

    Parameters
    ----------
    test_n : int
        Number of test cases to generate. Each test case yields one valid pair
        (policy_graph, dataframe) and one invalid pair.

    policy_number : int
        Base number of ODRL policies to generate. If `use_random_configuration`
        is True, an integer in [1, policy_number] is sampled for each iteration.

    p_rule_n : int
        Number of permission rules. If randomization is enabled, a value in
        [0, p_rule_n] is sampled. If all rule categories become zero, p_rule_n
        is forced to 1.

    f_rule_n : int
        Number of prohibition rules. Randomized into [0, f_rule_n] if enabled.

    o_rule_n : int
        Number of obligation rules. Randomized into [0, o_rule_n] if enabled.

    constants_per_feature : int
        Maximum number of constants per ontology feature. Randomized into
        [1, constants_per_feature] if enabled.

    constraint_number_min : int
        Minimum number of constraints per rule.

    constraint_number_max : int
        Maximum number of constraints per rule.

    chance_feature_null : float
        Probability that a feature appears with no assigned condition in a rule.

    constraint_right_operand_min : int
        Minimum numeric value for constraint right operands.

    constraint_right_operand_max : int
        Maximum numeric value for constraint right operands.

    ontology_path : str
        Path to the ontology file used when generating ODRL policies.

    number_of_records : int
        Number of rows to generate in each SotW dataset (the number of
        events in the event log) If randomization is
        enabled, this becomes a random integer in [number_of_records/2,
        number_of_records].

    chance_feature_empty : float
        Probability that a feature is omitted from a record in the generated
        SotW dataset.

    use_random_configuration : bool
        If True, randomizes selected parameters for each test case iteration
        (policy_number, rule counts, constants_per_feature, and number_of_records).

    Returns
    -------
    dict
        A dictionary with two keys:
            "valid_pairs"   : list of (policy_graph, dataframe) state of the world that
                               satisfies the generated policy.
            "invalid_pairs" : list of (policy_graph, dataframe) state of the world that
                               intentionally violates the generated policy.
    """
    valid = []
    invalid = []

    for _ in range(test_n):

        # -----------------------
        # RANDOMIZATION LOGIC
        # -----------------------
        if use_random_configuration:

            # random 1..value
            constants_pf = random.randint(1, constants_per_feature)
            policy_num = random.randint(1, policy_number)

            # random 0..value
            p_n = random.randint(0, p_rule_n)
            f_n = random.randint(0, f_rule_n)
            o_n = random.randint(0, o_rule_n)

            # ensure not all zero
            if p_n + f_n + o_n == 0:
                p_n = 1

            # number_of_records random between half and full
            recs = random.randint(max(1, number_of_records // 2), number_of_records)

        else:
            constants_pf = constants_per_feature
            policy_num = policy_number
            p_n = p_rule_n
            f_n = f_rule_n
            o_n = o_rule_n
            recs = number_of_records

        # ---- 1. Generate ODRL policy ----
        policy_graph = ODRL_generator.generate_ODRL(
            policy_number=policy_num,
            p_rule_n=p_n,
            f_rule_n=f_n,
            o_rule_n=o_n,
            constants_per_feature=constants_pf,
            constraint_number_min=constraint_number_min,
            constraint_number_max=constraint_number_max,
            chance_feature_null=chance_feature_null,
            constraint_right_operand_min=constraint_right_operand_min,
            constraint_right_operand_max=constraint_right_operand_max,
            ontology_path=ontology_path
        )

        # ---- 2. Generate valid SotW ----
        valid_df = SotW_generator.generate_pd_state_of_the_world_from_policies(
            policy_graph,
            number_of_records=recs,
            valid=True,
            chance_feature_empty=chance_feature_empty
        )
        valid.append((policy_graph, valid_df))

        # ---- 3. Generate invalid SotW ----
        invalid_df = SotW_generator.generate_pd_state_of_the_world_from_policies(
            policy_graph,
            number_of_records=recs,
            valid=False,
            chance_feature_empty=chance_feature_empty
        )
        invalid.append((policy_graph, invalid_df))

    return {
        "valid_pairs": valid,
        "invalid_pairs": invalid
    }



def print_test(test_n =3):
    results = generate_permission_test_cases(
        test_n=test_n,
        number_of_records=5,
        chance_feature_empty=0.3
    )

    print("\n========== VALID PAIRS ==========\n")
    for i, (graph, df) in enumerate(results["valid_pairs"], start=1):
        print(f"\n--- VALID POLICY #{i} ---")
        print(graph.serialize(format="turtle"))
        print("\n--- VALID DATAFRAME ---")
        print(df)

    print("\n========== INVALID PAIRS ==========\n")
    for i, (graph, df) in enumerate(results["invalid_pairs"], start=1):
        print(f"\n--- INVALID POLICY #{i} ---")
        print(graph.serialize(format="turtle"))
        print("\n--- INVALID DATAFRAME ---")
        print(df)

#print_test()