"""
ODRL Runtime Benchmark Script

Generates:
1) Runtime vs State-of-the-World size
2) Runtime vs Policy size

Outputs:
- plot1_runtime_vs_sotw.png
- plot2_runtime_vs_policy.png
- plot1_data.csv
- plot2_data.csv

Requires:
- ODRL_generator
- SotW_generator
- ODRL_Evaluator
"""

import time
import csv
import matplotlib.pyplot as plt

import ODRL_generator
import SotW_generator
import ODRL_Evaluator


# ==========================================================
# GLOBAL CONFIGURATION PARAMETERS (* values from spec)
# ==========================================================

# ---- plot 1 parameters ----
STATE_SIZE_START = 25
STATE_SIZE_END = 200
STATE_SIZE_STEP = 25

FIXED_PERMISSION_RULES = 10
FIXED_PROHIBITION_RULES = 10
FIXED_OBLIGATION_RULES = 10


# ---- plot 2 parameters ----
POLICY_SIZE_START = 10
POLICY_SIZE_END = 50
POLICY_SIZE_STEP = 10

FIXED_STATE_SIZE = 200


# ---- general parameters ----
TEST_REPETITIONS = 10

CONSTRAINT_NUMBER_MIN = 0
CONSTRAINT_NUMBER_MAX = 6
CONSTANTS_PER_FEATURE = 6

CHANCE_FEATURE_NULL = 0.5
CHANCE_FEATURE_EMPTY = 0.5

ONTOLOGY_PATH = "sample_ontologies/ODRL_DPV.ttl"



# ==========================================================
# CORE EVALUATION FUNCTION
# ==========================================================

def evaluate_once(policy_graph, dataframe):
    """
    Run one ODRL evaluation and return runtime.
    """

    feature_map = {
        f["iri"]: f["type"]
        for f in SotW_generator.extract_features_list_from_policy(policy_graph)
    }

    rules = SotW_generator.extract_rule_list_from_policy(policy_graph)

    start = time.perf_counter()

    ODRL_Evaluator.evaluate_ODRL_on_dataframe(
        rules,
        dataframe,
        feature_map
    )

    end = time.perf_counter()

    return end - start



# ==========================================================
# POLICY + SOTW GENERATION
# ==========================================================

def generate_valid_pair(
    permissions,
    prohibitions,
    obligations,
    sotw_size
):

    policy_graph = ODRL_generator.generate_ODRL(
        policy_number=1,
        p_rule_n=permissions,
        f_rule_n=prohibitions,
        o_rule_n=obligations,
        constants_per_feature=CONSTANTS_PER_FEATURE,
        constraint_number_min=CONSTRAINT_NUMBER_MIN,
        constraint_number_max=CONSTRAINT_NUMBER_MAX,
        chance_feature_null=CHANCE_FEATURE_NULL,
        ontology_path=ONTOLOGY_PATH
    )

    dataframe = SotW_generator.generate_pd_state_of_the_world_from_policies(
        policy_graph,
        number_of_records=sotw_size,
        valid=True,
        chance_feature_empty=CHANCE_FEATURE_EMPTY
    )

    return policy_graph, dataframe



# ==========================================================
# PLOT 1
# Runtime vs SotW Size
# ==========================================================

def benchmark_plot_1():

    results = []

    sizes = list(range(
        STATE_SIZE_START,
        STATE_SIZE_END + 1,
        STATE_SIZE_STEP
    ))

    print("\nRunning Plot 1 Benchmark")

    for size in sizes:

        times = []

        for _ in range(TEST_REPETITIONS):

            policy, df = generate_valid_pair(
                FIXED_PERMISSION_RULES,
                FIXED_PROHIBITION_RULES,
                FIXED_OBLIGATION_RULES,
                size
            )

            t = evaluate_once(policy, df)

            times.append(t)

        avg_time = sum(times) / len(times)

        results.append((size, avg_time))

        print(f"SotW size {size} -> {avg_time:.4f}s")

    return results



# ==========================================================
# PLOT 2
# Runtime vs Policy Size
# ==========================================================

def benchmark_plot_2():

    results = []

    policy_sizes = list(range(
        POLICY_SIZE_START,
        POLICY_SIZE_END + 1,
        POLICY_SIZE_STEP
    ))

    print("\nRunning Plot 2 Benchmark")

    for size in policy_sizes:

        # ---- Permissions + Prohibitions ----
        times_pp = []

        for _ in range(TEST_REPETITIONS):

            policy, df = generate_valid_pair(
                permissions=size,
                prohibitions=size,
                obligations=0,
                sotw_size=FIXED_STATE_SIZE
            )

            t = evaluate_once(policy, df)

            times_pp.append(t)

        avg_pp = sum(times_pp) / len(times_pp)


        # ---- Permissions + Obligations ----
        times_po = []

        for _ in range(TEST_REPETITIONS):

            policy, df = generate_valid_pair(
                permissions=size,
                prohibitions=0,
                obligations=size,
                sotw_size=FIXED_STATE_SIZE
            )

            t = evaluate_once(policy, df)

            times_po.append(t)

        avg_po = sum(times_po) / len(times_po)


        results.append((size, avg_pp, avg_po))

        print(
            f"Policy size {size} -> "
            f"PP={avg_pp:.4f}s | PO={avg_po:.4f}s"
        )

    return results



# ==========================================================
# CSV WRITING
# ==========================================================

def save_plot1_csv(results):

    with open("plot1_data.csv", "w", newline="") as f:

        writer = csv.writer(f)

        writer.writerow([
            "sotw_size",
            "avg_runtime_seconds"
        ])

        for row in results:
            writer.writerow(row)



def save_plot2_csv(results):

    with open("plot2_data.csv", "w", newline="") as f:

        writer = csv.writer(f)

        writer.writerow([
            "policy_size",
            "permissions_prohibitions_runtime",
            "permissions_obligations_runtime"
        ])

        for row in results:
            writer.writerow(row)



# ==========================================================
# PLOTTING
# ==========================================================

def plot_results_plot1(results):

    x = [r[0] for r in results]
    y = [r[1] for r in results]

    plt.figure()

    plt.plot(x, y)

    plt.xlabel("State of the World Size")
    plt.ylabel("Runtime (seconds)")
    plt.title("Runtime vs SotW Size")

    plt.savefig("plot1_runtime_vs_sotw.png")

    plt.close()



def plot_results_plot2(results):

    x = [r[0] for r in results]
    y_pp = [r[1] for r in results]
    y_po = [r[2] for r in results]

    plt.figure()

    plt.plot(x, y_pp, label="Permissions + Prohibitions")
    plt.plot(x, y_po, label="Permissions + Obligations")

    plt.xlabel("Policy Size")
    plt.ylabel("Runtime (seconds)")
    plt.title("Runtime vs Policy Size")

    plt.legend()

    plt.savefig("plot2_runtime_vs_policy.png")

    plt.close()



# ==========================================================
# MAIN EXECUTION
# ==========================================================

def main():

    # ---- Plot 1 ----
    results1 = benchmark_plot_1()

    save_plot1_csv(results1)

    plot_results_plot1(results1)


    # ---- Plot 2 ----
    results2 = benchmark_plot_2()

    save_plot2_csv(results2)

    plot_results_plot2(results2)


    print("\nBenchmark complete.")



if __name__ == "__main__":
    main()