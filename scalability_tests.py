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
import ast
import sys

import ODRL_generator
import SotW_generator
import ODRL_Evaluator


# ==========================================================
# GLOBAL CONFIGURATION PARAMETERS (* values from spec)
# ==========================================================

# ---- plot 1 parameters ----
STATE_SIZE_START = 50
STATE_SIZE_END = 1000
STATE_SIZE_STEP = 50

FIXED_PERMISSION_RULES = 30
FIXED_PROHIBITION_RULES = 30
FIXED_OBLIGATION_RULES = 30


# ---- plot 2 parameters ----
POLICY_SIZE_START = 5
POLICY_SIZE_END = 50
POLICY_SIZE_STEP = 5

FIXED_STATE_SIZE = 100

# ---- general parameters ----
TEST_REPETITIONS = 10

CONSTRAINT_NUMBER_MIN = 0
CONSTRAINT_NUMBER_MAX = 100
CONSTRAINT_NUMBER_STEP = 5
CONSTANTS_PER_FEATURE = 6
FIXED_CONSTRAINT_NUMBER = 1

PERMISSIONS_WITH_DUTIES = 100
DUTIES_PER_PERMISSION = 1
DUTIES_PER_PERMISSION_MIN = 0
DUTIES_PER_PERMISSION_MAX = 10

CONSEQUENCE_PER_PERMISSION = 1
REMEDIES_PER_PROHIBITION = 1
PROHIBITIONS_WITH_REMEDIES = 100

CHANCE_FEATURE_NULL = 0.5
CHANCE_FEATURE_EMPTY = 0.5

ONTOLOGY_PATH = "sample_ontologies/ODRL_DPV.ttl"


# PARAMETER OVERRIDES

def apply_cli_overrides(args):
    """
    Allows overriding global parameters from command line.

    Example:
        python scalability_tests.py POLICY POLICY_SIZE_START=10 POLICY_SIZE_END=100
    """

    global_vars = globals()

    for arg in args:
        if "=" not in arg:
            continue

        key, value = arg.split("=", 1)

        if key == "suffix":
            continue

        if key not in global_vars:
            print(f"[WARNING] Unknown parameter: {key}")
            continue

        try:
            # Automatically parse int, float, bool, etc.
            parsed_value = ast.literal_eval(value)
        except:
            parsed_value = value

        global_vars[key] = parsed_value

        print(f"[CONFIG] {key} = {parsed_value}")

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

    result_list = ODRL_Evaluator.evaluate_ODRL_on_dataframe(
        rules,
        dataframe,
        feature_map
    )
    result = result_list[1] == 1

    end = time.perf_counter()

    return end - start, result



# ==========================================================
# POLICY + SOTW GENERATION
# ==========================================================

def generate_valid_pair(
    permissions,
    prohibitions,
    obligations,
    sotw_size,
    duties_per_p_n = DUTIES_PER_PERMISSION,
    p_with_duties_n = PERMISSIONS_WITH_DUTIES,
    consequence_per_permissionDuty=CONSEQUENCE_PER_PERMISSION,  
    remedies_per_f_n=REMEDIES_PER_PROHIBITION,  
    f_with_remedies_n=PROHIBITIONS_WITH_REMEDIES,
    constants_per_feature = CONSTANTS_PER_FEATURE,
    constraint_number_min = CONSTRAINT_NUMBER_MIN,
    constraint_number_max = CONSTRAINT_NUMBER_MAX,
    chance_feature_null = CHANCE_FEATURE_NULL,
    ontology_path = ONTOLOGY_PATH,
    valid = True,
    chance_feature_empty = CHANCE_FEATURE_EMPTY
    
):

    policy_graph = ODRL_generator.generate_ODRL(
        policy_number=1,
        p_rule_n=permissions,
        f_rule_n=prohibitions,
        o_rule_n=obligations,
        duties_per_p_n=duties_per_p_n,
        p_with_duties_n=p_with_duties_n,
        consequence_per_permissionDuty=consequence_per_permissionDuty,
        remedies_per_f_n=remedies_per_f_n,
        f_with_remedies_n=f_with_remedies_n,
        constants_per_feature=constants_per_feature,
        constraint_number_min=constraint_number_min,
        constraint_number_max=constraint_number_max,
        chance_feature_null=chance_feature_null,
        ontology_path=ontology_path
    )

    dataframe = SotW_generator.generate_pd_state_of_the_world_from_policies(
        policy_graph,
        number_of_records=sotw_size,
        valid=valid,
        chance_feature_empty=chance_feature_empty
    )

    return policy_graph, dataframe



# ==========================================================
# PLOT 1
# Runtime vs SotW Size
# ==========================================================

# ==========================================================
# PLOT 2
# Runtime vs Policy Size
# ==========================================================

def benchmark_policy_size_plot(minimum = POLICY_SIZE_START, maximum = POLICY_SIZE_END, step = POLICY_SIZE_STEP):

    permission_results, avg_permission_results = benchmark_permissions_plot(minimum, maximum, step)
    prohibition_results, avg_prohibition_results = benchmark_permissions_prohibitions_plot(minimum, maximum, step)
    obligation_results, avg_obligation_results = benchmark_permissions_obligations_plot(minimum, maximum, step)

    return permission_results, avg_permission_results, prohibition_results, avg_prohibition_results, obligation_results, avg_obligation_results


def benchmark_permissions_plot(policy_size_min = POLICY_SIZE_START, policy_size_max = POLICY_SIZE_END, policy_step = POLICY_SIZE_STEP):
    results = []
    avg_results = []

    policy_sizes = list(range(
        policy_size_min,
        policy_size_max + 1,
        policy_step
    ))

    for size in policy_sizes:
        # Only Permissions

        times = []
        policy_size = size + (DUTIES_PER_PERMISSION + CONSEQUENCE_PER_PERMISSION) * min(size, PERMISSIONS_WITH_DUTIES)

        for _ in range(TEST_REPETITIONS):

            policy, df = generate_valid_pair(
                permissions=size,
                prohibitions=0,
                obligations=0,
                sotw_size=FIXED_STATE_SIZE,
                constraint_number_max=FIXED_CONSTRAINT_NUMBER,
                constraint_number_min=FIXED_CONSTRAINT_NUMBER
            )

            t, valid = evaluate_once(policy, df)
            stats = [policy_size, 
                    size, 
                    0, 
                    0, 
                    DUTIES_PER_PERMISSION,
                    PERMISSIONS_WITH_DUTIES,
                    CONSEQUENCE_PER_PERMISSION,
                    REMEDIES_PER_PROHIBITION,
                    PROHIBITIONS_WITH_REMEDIES,
                    CONSTANTS_PER_FEATURE,
                    CONSTRAINT_NUMBER_MIN,
                    CONSTRAINT_NUMBER_MAX,
                    FIXED_STATE_SIZE, 
                    t, 
                    CHANCE_FEATURE_NULL, 
                    CHANCE_FEATURE_EMPTY,
                    valid
                    ]

            times.append(t)
            results.append(stats)

        avg_time = sum(times) / len(times)

        avg_results.append([policy_size, 
                    size, 
                    0, 
                    0, 
                    DUTIES_PER_PERMISSION,
                    PERMISSIONS_WITH_DUTIES,
                    CONSEQUENCE_PER_PERMISSION,
                    REMEDIES_PER_PROHIBITION,
                    PROHIBITIONS_WITH_REMEDIES,
                    CONSTANTS_PER_FEATURE,
                    CONSTRAINT_NUMBER_MIN,
                    CONSTRAINT_NUMBER_MAX,
                    FIXED_STATE_SIZE, 
                    avg_time, 
                    CHANCE_FEATURE_NULL, 
                    CHANCE_FEATURE_EMPTY,
                    None
                    ])

        print(f"Number of permissions: {size} -> {avg_time:.4f}s")

    return results, avg_results

def benchmark_permissions_prohibitions_plot(policy_size_min = POLICY_SIZE_START, policy_size_max = POLICY_SIZE_END, policy_step = POLICY_SIZE_STEP):
    results = []
    avg_results = []

    policy_sizes = list(range(
        policy_size_min,
        policy_size_max + 1,
        policy_step
    ))

    for size in policy_sizes:
        # Permissions and Prohibitions

        times = []
        half_size = int(size/2.0)
        policy_size = 2*half_size + (DUTIES_PER_PERMISSION + CONSEQUENCE_PER_PERMISSION) * min(half_size, PERMISSIONS_WITH_DUTIES) + REMEDIES_PER_PROHIBITION * min(half_size, PROHIBITIONS_WITH_REMEDIES)

        for _ in range(TEST_REPETITIONS):

            policy, df = generate_valid_pair(
                permissions=half_size,
                prohibitions=half_size,
                obligations=0,
                sotw_size=FIXED_STATE_SIZE,
                constraint_number_max=FIXED_CONSTRAINT_NUMBER,
                constraint_number_min=FIXED_CONSTRAINT_NUMBER
            )

            t, valid = evaluate_once(policy, df)
            stats = [policy_size, 
                    half_size, 
                    half_size, 
                    0, 
                    DUTIES_PER_PERMISSION,
                    PERMISSIONS_WITH_DUTIES,
                    CONSEQUENCE_PER_PERMISSION,
                    REMEDIES_PER_PROHIBITION,
                    PROHIBITIONS_WITH_REMEDIES,
                    CONSTANTS_PER_FEATURE,
                    CONSTRAINT_NUMBER_MIN,
                    CONSTRAINT_NUMBER_MAX,
                    FIXED_STATE_SIZE,
                    t, 
                    CHANCE_FEATURE_NULL, 
                    CHANCE_FEATURE_EMPTY,
                    valid
                    ]

            times.append(t)
            results.append(stats)

        avg_time = sum(times) / len(times)

        avg_results.append([policy_size, 
                    half_size, 
                    half_size, 
                    0, 
                    DUTIES_PER_PERMISSION,
                    PERMISSIONS_WITH_DUTIES,
                    CONSEQUENCE_PER_PERMISSION,
                    REMEDIES_PER_PROHIBITION,
                    PROHIBITIONS_WITH_REMEDIES,
                    CONSTANTS_PER_FEATURE,
                    CONSTRAINT_NUMBER_MIN,
                    CONSTRAINT_NUMBER_MAX,
                    FIXED_STATE_SIZE,
                    avg_time, 
                    CHANCE_FEATURE_NULL, 
                    CHANCE_FEATURE_EMPTY,
                    None
                    ])

        print(f"Number of permissions and prohibitions: {half_size} each -> {avg_time:.4f}s")

    return results, avg_results

def benchmark_permissions_obligations_plot(policy_size_min = POLICY_SIZE_START, policy_size_max = POLICY_SIZE_END, policy_step = POLICY_SIZE_STEP):
    results = []
    avg_results = []

    policy_sizes = list(range(
        policy_size_min,
        policy_size_max + 1,
        policy_step
    ))

    for size in policy_sizes:
        # Permissions and Obligations

        times = []
        half_size = int(size/2.0)
        policy_size = 2*half_size + (DUTIES_PER_PERMISSION + CONSEQUENCE_PER_PERMISSION) * min(half_size, PERMISSIONS_WITH_DUTIES)

        for _ in range(TEST_REPETITIONS):

            policy, df = generate_valid_pair(
                permissions=half_size,
                prohibitions=0,
                obligations=half_size,
                sotw_size=FIXED_STATE_SIZE,
                constraint_number_max=FIXED_CONSTRAINT_NUMBER,
                constraint_number_min=FIXED_CONSTRAINT_NUMBER
            )

            t, valid = evaluate_once(policy, df)
            stats = [policy_size, 
                    half_size, 
                    0, 
                    half_size, 
                    DUTIES_PER_PERMISSION,
                    PERMISSIONS_WITH_DUTIES,
                    CONSEQUENCE_PER_PERMISSION,
                    REMEDIES_PER_PROHIBITION,
                    PROHIBITIONS_WITH_REMEDIES,
                    CONSTANTS_PER_FEATURE,
                    CONSTRAINT_NUMBER_MIN,
                    CONSTRAINT_NUMBER_MAX,
                    FIXED_STATE_SIZE,
                    t, 
                    CHANCE_FEATURE_NULL, 
                    CHANCE_FEATURE_EMPTY,
                    valid
                    ]

            times.append(t)
            results.append(stats)

        avg_time = sum(times) / len(times)

        avg_results.append([policy_size, 
                    half_size, 
                    0, 
                    half_size, 
                    DUTIES_PER_PERMISSION,
                    PERMISSIONS_WITH_DUTIES,
                    CONSEQUENCE_PER_PERMISSION,
                    REMEDIES_PER_PROHIBITION,
                    PROHIBITIONS_WITH_REMEDIES,
                    CONSTANTS_PER_FEATURE,
                    CONSTRAINT_NUMBER_MIN,
                    CONSTRAINT_NUMBER_MAX,
                    FIXED_STATE_SIZE, 
                    avg_time, 
                    CHANCE_FEATURE_NULL, 
                    CHANCE_FEATURE_EMPTY,
                    None
                    ])

        print(f"Number of permissions and obligations: {half_size} each -> {avg_time:.4f}s")

    return results, avg_results

def benchmark_all_plot(policy_size_min = POLICY_SIZE_START, policy_size_max = POLICY_SIZE_END, policy_step = POLICY_SIZE_STEP):
    results = []
    avg_results = []

    policy_sizes = list(range(
        policy_size_min,
        policy_size_max + 1,
        policy_step
    ))

    for size in policy_sizes:
        # Permissions and Obligations

        times = []
        third_size = int(size/3.0)
        policy_size = 3*third_size + (DUTIES_PER_PERMISSION + CONSEQUENCE_PER_PERMISSION) * min(third_size, PERMISSIONS_WITH_DUTIES) + REMEDIES_PER_PROHIBITION * min(third_size, PROHIBITIONS_WITH_REMEDIES)

        for _ in range(TEST_REPETITIONS):

            policy, df = generate_valid_pair(
                permissions=third_size,
                prohibitions=third_size,
                obligations=third_size,
                sotw_size=FIXED_STATE_SIZE,
                constraint_number_max=FIXED_CONSTRAINT_NUMBER,
                constraint_number_min=FIXED_CONSTRAINT_NUMBER
            )

            t, valid = evaluate_once(policy, df)
            stats = [policy_size, 
                    third_size, 
                    third_size, 
                    third_size, 
                    DUTIES_PER_PERMISSION,
                    PERMISSIONS_WITH_DUTIES,
                    CONSEQUENCE_PER_PERMISSION,
                    REMEDIES_PER_PROHIBITION,
                    PROHIBITIONS_WITH_REMEDIES,
                    CONSTANTS_PER_FEATURE,
                    CONSTRAINT_NUMBER_MIN,
                    CONSTRAINT_NUMBER_MAX,
                    FIXED_STATE_SIZE,
                    t, 
                    CHANCE_FEATURE_NULL, 
                    CHANCE_FEATURE_EMPTY,
                    valid
                    ]

            times.append(t)
            results.append(stats)

        avg_time = sum(times) / len(times)
        avg_results.append([policy_size, 
                    third_size, 
                    third_size, 
                    third_size, 
                    DUTIES_PER_PERMISSION,
                    PERMISSIONS_WITH_DUTIES,
                    CONSEQUENCE_PER_PERMISSION,
                    REMEDIES_PER_PROHIBITION,
                    PROHIBITIONS_WITH_REMEDIES,
                    CONSTANTS_PER_FEATURE,
                    CONSTRAINT_NUMBER_MIN,
                    CONSTRAINT_NUMBER_MAX,
                    FIXED_STATE_SIZE, 
                    avg_time, 
                    CHANCE_FEATURE_NULL, 
                    CHANCE_FEATURE_EMPTY,
                    None
                    ])

        print(f"Number of permissions, prohibitions and obligations: {third_size} each -> {avg_time:.4f}s")

    return results, avg_results

# BENCHMARK PLOT WRITTEN BY A HUMAN
def benchmark_duties_plot(minimum = 0, maximum = DUTIES_PER_PERMISSION, step = 1):

    results = []
    avg_results = []

    duties_per_permission = list(range(
        minimum,
        maximum + 1,
        step
    ))

    for size in duties_per_permission:

        times = []

        for _ in range(TEST_REPETITIONS):

            policy, df = generate_valid_pair(
                FIXED_PERMISSION_RULES,
                FIXED_PROHIBITION_RULES,
                FIXED_OBLIGATION_RULES,
                FIXED_STATE_SIZE,
                duties_per_p_n=size,
                constraint_number_max=FIXED_CONSTRAINT_NUMBER,
                constraint_number_min=FIXED_CONSTRAINT_NUMBER
            )

            t, valid = evaluate_once(policy, df)
            stats = [len(policy), 
                    FIXED_PERMISSION_RULES, 
                    FIXED_PROHIBITION_RULES, 
                    FIXED_OBLIGATION_RULES, 
                    size,
                    PERMISSIONS_WITH_DUTIES,
                    CONSEQUENCE_PER_PERMISSION,
                    REMEDIES_PER_PROHIBITION,
                    PROHIBITIONS_WITH_REMEDIES,
                    CONSTANTS_PER_FEATURE,
                    CONSTRAINT_NUMBER_MIN,
                    CONSTRAINT_NUMBER_MAX,
                    FIXED_STATE_SIZE,
                    t, 
                    CHANCE_FEATURE_NULL, 
                    CHANCE_FEATURE_EMPTY,
                    valid
                    ]

            times.append(t)
            results.append(stats)

        avg_time = sum(times) / len(times)

        avg_results.append([len(policy), 
                    FIXED_PERMISSION_RULES, 
                    FIXED_PROHIBITION_RULES, 
                    FIXED_OBLIGATION_RULES,
                    size,
                    PERMISSIONS_WITH_DUTIES,
                    CONSEQUENCE_PER_PERMISSION,
                    REMEDIES_PER_PROHIBITION,
                    PROHIBITIONS_WITH_REMEDIES,
                    CONSTANTS_PER_FEATURE,
                    CONSTRAINT_NUMBER_MIN,
                    CONSTRAINT_NUMBER_MAX,
                    FIXED_STATE_SIZE, 
                    avg_time, 
                    CHANCE_FEATURE_NULL, 
                    CHANCE_FEATURE_EMPTY,
                    None
                    ])
        print(f"Duties per permission {size} -> {avg_time:.4f}s")

    return results, avg_results

def benchmark_sotw_plot(minimum = STATE_SIZE_START, maximum = STATE_SIZE_END, step = STATE_SIZE_STEP):

    results = []
    avg_results = []

    sotw_size = list(range(
        minimum,
        maximum,
        step
    ))

    for size in sotw_size:

        times = []

        for _ in range(TEST_REPETITIONS):

            policy, df = generate_valid_pair(
                FIXED_PERMISSION_RULES,
                FIXED_PROHIBITION_RULES,
                FIXED_OBLIGATION_RULES,
                size,
                constraint_number_min=FIXED_CONSTRAINT_NUMBER,
                constraint_number_max=FIXED_CONSTRAINT_NUMBER
            )

            t, valid = evaluate_once(policy, df)
            stats = [len(policy), 
                    FIXED_PERMISSION_RULES,
                    FIXED_PROHIBITION_RULES,
                    FIXED_OBLIGATION_RULES,
                    DUTIES_PER_PERMISSION,
                    PERMISSIONS_WITH_DUTIES,
                    CONSEQUENCE_PER_PERMISSION,
                    REMEDIES_PER_PROHIBITION,
                    PROHIBITIONS_WITH_REMEDIES,
                    CONSTANTS_PER_FEATURE,
                    CONSTRAINT_NUMBER_MIN,
                    CONSTRAINT_NUMBER_MAX, 
                    size, 
                    t, 
                    CHANCE_FEATURE_NULL, 
                    CHANCE_FEATURE_EMPTY,
                    valid
                    ]

            times.append(t)
            results.append(stats)

        avg_time = sum(times) / len(times)

        avg_results.append([len(policy), 
                    FIXED_PERMISSION_RULES,
                    FIXED_PROHIBITION_RULES,
                    FIXED_OBLIGATION_RULES,
                    DUTIES_PER_PERMISSION,
                    PERMISSIONS_WITH_DUTIES,
                    CONSEQUENCE_PER_PERMISSION,
                    REMEDIES_PER_PROHIBITION,
                    PROHIBITIONS_WITH_REMEDIES,
                    CONSTANTS_PER_FEATURE,
                    CONSTRAINT_NUMBER_MIN,
                    CONSTRAINT_NUMBER_MAX, 
                    size, 
                    avg_time, 
                    CHANCE_FEATURE_NULL, 
                    CHANCE_FEATURE_EMPTY,
                    None
                    ])
        print(f"State of the world size {size} -> {avg_time:.4f}s")

    return results, avg_results

def benchmark_constraints_plot(minimum = CONSTRAINT_NUMBER_MIN, maximum = CONSTRAINT_NUMBER_MAX, step = CONSTRAINT_NUMBER_STEP):
    results = []
    avg_results = []

    n_constraints = list(range(
        minimum,
        maximum,
        step
    ))

    for size in n_constraints:

        times = []

        for _ in range(TEST_REPETITIONS):

            policy, df = generate_valid_pair(
                FIXED_PERMISSION_RULES,
                FIXED_PROHIBITION_RULES,
                FIXED_OBLIGATION_RULES,
                FIXED_STATE_SIZE,
                constraint_number_min=size,
                constraint_number_max=size
            )

            t, valid = evaluate_once(policy, df)
            stats = [
                len(policy), 
                FIXED_PERMISSION_RULES,
                FIXED_PROHIBITION_RULES,
                FIXED_OBLIGATION_RULES,
                DUTIES_PER_PERMISSION,
                PERMISSIONS_WITH_DUTIES,
                CONSEQUENCE_PER_PERMISSION,
                REMEDIES_PER_PROHIBITION,
                PROHIBITIONS_WITH_REMEDIES,
                CONSTANTS_PER_FEATURE,
                size, 
                size,
                FIXED_STATE_SIZE, 
                t, 
                CHANCE_FEATURE_NULL, 
                CHANCE_FEATURE_EMPTY,
                valid
            ]

            times.append(t)
            results.append(stats)

        avg_time = sum(times) / len(times)

        avg_results.append([len(policy),
                            FIXED_PERMISSION_RULES,
                            FIXED_PROHIBITION_RULES,
                            FIXED_OBLIGATION_RULES,
                            DUTIES_PER_PERMISSION,
                            PERMISSIONS_WITH_DUTIES,
                            CONSEQUENCE_PER_PERMISSION,
                            REMEDIES_PER_PROHIBITION,
                            PROHIBITIONS_WITH_REMEDIES,
                            CONSTANTS_PER_FEATURE,
                            size,
                            size,
                            FIXED_STATE_SIZE,
                            avg_time,
                            CHANCE_FEATURE_NULL,
                            CHANCE_FEATURE_EMPTY,
                            None])

        print(f"Number of constraints per rule: {size} -> {avg_time:.4f}s")

    return results, avg_results

def save_plot(results, filename="plot.csv"):
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)

        writer.writerow([
            "policy_size",
            "permissions",
            "prohibitions",
            "obligations",
            "duties_per_permission",
            "permissions_with_duties",
            "consequences_per_duty",
            "remedies_per_prohibition",
            "prohibitions_with_remedies",
            "constants_per_feature",
            "constraints_number_min",
            "constraints_number_max",
            "sotw_size",
            "runtime_seconds",
            "null_chance",
            "empty_chance",
            "valid"
        ])

        for row in results:
            writer.writerow(row)




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

def plot_results(filename):
    with open(file=filename) as results:
        csv.reader



# ==========================================================
# MAIN EXECUTION
# ==========================================================

def main():

    # ---- Plot 1 ----
    results1 = benchmark_policy_size_plot()

    save_plot1_csv(results1)

    plot_results_plot1(results1)


    # ---- Plot 2 ----
    results2 = benchmark_policy_size_plot()

    save_plot2_csv(results2)

    plot_results_plot2(results2)


    print("\nBenchmark complete.")



if __name__ == "__main__":
    args = sys.argv[1:]
    apply_cli_overrides(args[1:])
    if not args:
        main()
        print("Please provide the path to a markdown file containing the test case.")
    else:
        suffix = ""
        for arg in args[1:]:
            if arg.startswith("suffix="):
                suffix = arg.split("=", 1)[1].strip('"').strip("'")
        if args[0] == "DUTIES":
            results, avg_results = benchmark_duties_plot(DUTIES_PER_PERMISSION_MIN, DUTIES_PER_PERMISSION_MAX)
            save_plot(results=results, filename=f"test_results/duties{suffix}.csv")
            save_plot(results=avg_results, filename=f"test_results/avg_duties{suffix}.csv")
        elif args[0] == "SOTW":
            results, avg_results = benchmark_sotw_plot(STATE_SIZE_START, STATE_SIZE_END, STATE_SIZE_STEP)
            save_plot(results=results, filename=f"test_results/sotw{suffix}.csv")
            save_plot(results=avg_results, filename=f"test_results/avg_sotw{suffix}.csv")
        elif args[0] == "CONSTRAINTS":
            results, avg_results = benchmark_constraints_plot(CONSTRAINT_NUMBER_MIN, CONSTRAINT_NUMBER_MAX)
            save_plot(results=results, filename=f"test_results/constraints{suffix}.csv")
            save_plot(results=avg_results, filename=f"test_results/avg_constraints{suffix}.csv")
        elif args[0] == "POLICY":
            p_results, avg_p_results, f_results, avg_f_results, o_results, avg_o_results = benchmark_policy_size_plot(POLICY_SIZE_START, POLICY_SIZE_END, POLICY_SIZE_STEP)
            save_plot(results=p_results, filename=f"test_results/permissions{suffix}.csv")
            save_plot(results=avg_p_results, filename=f"test_results/avg_permissions{suffix}.csv")
            save_plot(results=f_results, filename=f"test_results/prohibitions{suffix}.csv")
            save_plot(results=avg_f_results, filename=f"test_results/avg_prohibitions{suffix}.csv")
            save_plot(results=o_results, filename=f"test_results/obligations{suffix}.csv")
            save_plot(results=avg_o_results, filename=f"test_results/avg_obligations{suffix}.csv")
        elif args[0] == "COMPLEX":
            results, avg_results = benchmark_all_plot(POLICY_SIZE_START, POLICY_SIZE_END, POLICY_SIZE_STEP)
            save_plot(results=results, filename=f"test_results/all{suffix}.csv")
            save_plot(results=avg_results, filename=f"test_results/avg_all{suffix}.csv")
