import subprocess
import sys
import time
import os
import pandas as pd
import matplotlib.pyplot as plt

PYTHON = sys.executable


def run_experiment(name, command):

    print("\n" + "=" * 70)
    print(f"STARTING EXPERIMENT: {name}")
    print("=" * 70)

    start = time.time()

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    # Stream output live
    for line in process.stdout:
        print(f"[{name}] {line}", end="")

    process.wait()

    end = time.time()

    if process.returncode != 0:
        print(f"\n[ERROR] Experiment failed: {name}")
        sys.exit(process.returncode)

    print(f"\nCOMPLETED: {name} ({end - start:.2f}s)")
    print("=" * 70)


# ==========================================================
# GRAPH A - RED
# ==========================================================

run_experiment(
    "GRAPH_A_RED_POLICY",
    [
        PYTHON,
        "scalability_tests.py",
        "POLICY",

        "POLICY_SIZE_START=10",
        "POLICY_SIZE_END=100",
        "POLICY_SIZE_STEP=10",

        "FIXED_STATE_SIZE=100",

        "PERMISSIONS_WITH_DUTIES=0",

        'suffix="_graph_a_red"'
    ]
)


# ==========================================================
# GRAPH A - BLUE
# ==========================================================

run_experiment(
    "GRAPH_A_BLUE_COMPLEX",
    [
        PYTHON,
        "scalability_tests.py",
        "COMPLEX",

        "POLICY_SIZE_START=5",
        "POLICY_SIZE_END=50",
        "POLICY_SIZE_STEP=5",

        "FIXED_STATE_SIZE=100",

        "PERMISSIONS_WITH_DUTIES=100",
        "PROHIBITIONS_WITH_REMEDIES=100",

        'suffix="_graph_a_blue"'
    ]
)


# ==========================================================
# GRAPH B
# ==========================================================

graph_b_configs = [
    ("red", 10),
    ("blue", 20),
    ("black", 30),
]

for colour, fixed_rules in graph_b_configs:

    run_experiment(
        f"GRAPH_B_{colour.upper()}",
        [
            PYTHON,
            "scalability_tests.py",
            "SOTW",

            "STATE_SIZE_START=100",
            "STATE_SIZE_END=1000",
            "STATE_SIZE_STEP=50",

            "DUTIES_PER_PERMISSION=0",
            "REMEDIES_PER_PROHIBITION=0",

            f"FIXED_PERMISSION_RULES={fixed_rules}",
            f"FIXED_PROHIBITION_RULES={fixed_rules}",
            f"FIXED_OBLIGATION_RULES={fixed_rules}",

            f'suffix="_graph_b_{colour}"'
        ]
    )


# ==========================================================
# GRAPH C
# ==========================================================

graph_c_configs = [
    ("red", 100),
    ("blue", 300),
    ("black", 500),
]

for colour, state_size in graph_c_configs:

    run_experiment(
        f"GRAPH_C_{colour.upper()}",
        [
            PYTHON,
            "scalability_tests.py",
            "DUTIES",

            "DUTIES_PER_PERMISSION_MIN=0",
            "DUTIES_PER_PERMISSION_MAX=10",

            "PERMISSIONS_WITH_DUTIES=10",

            f"FIXED_STATE_SIZE={state_size}",

            f'suffix="_graph_c_{colour}"'
        ]
    )


# ==========================================================
# GRAPH D
# ==========================================================

graph_d_configs = [
    ("red", 100),
    ("blue", 300),
    ("black", 500),
]

for colour, state_size in graph_d_configs:

    run_experiment(
        f"GRAPH_D_{colour.upper()}",
        [
            PYTHON,
            "scalability_tests.py",
            "CONSTRAINTS",

            "CONSTRAINT_NUMBER_MIN=0",
            "CONSTRAINT_NUMBER_MAX=100",
            "CONSTRAINT_NUMBER_STEP=5",

            f"FIXED_STATE_SIZE={state_size}",

            f'suffix="_graph_d_{colour}"'
        ]
    )

def generate_combined_plot():

    output_dir = "test_results"
    os.makedirs(output_dir, exist_ok=True)

    fig, axs = plt.subplots(2, 2, figsize=(12, 10))
    axs = axs.flatten()

    # ==========================================================
    # GRAPH A
    # ==========================================================

    ax = axs[0]

    red_raw = pd.read_csv(
        "test_results/permissions_graph_a_red.csv"
    )
    red_avg = pd.read_csv(
        "test_results/avg_permissions_graph_a_red.csv"
    )

    blue_raw = pd.read_csv(
        "test_results/all_graph_a_blue.csv"
    )
    blue_avg = pd.read_csv(
        "test_results/avg_all_graph_a_blue.csv"
    )

    ax.scatter(
        red_raw["policy_size"],
        red_raw["runtime_seconds"],
        marker="x",
        color="red",
        alpha=0.6
    )

    ax.plot(
        red_avg["policy_size"],
        red_avg["runtime_seconds"],
        marker="x",
        color="red",
        label="Permissions only"
    )

    ax.scatter(
        blue_raw["policy_size"],
        blue_raw["runtime_seconds"],
        marker="o",
        color="blue",
        alpha=0.6
    )

    ax.plot(
        blue_avg["policy_size"],
        blue_avg["runtime_seconds"],
        marker="o",
        color="blue",
        label="Complex"
    )

    ax.set_xlabel("Policy Size")
    ax.set_ylabel("Runtime (seconds)")
    ax.set_title("a)")
    ax.set_ylim(0, 0.2)
    ax.grid(True)
    ax.legend()

    # ==========================================================
    # GRAPH B
    # ==========================================================

    ax = axs[1]

    graph_b = [
        ("red", "x", "10 rules"),
        ("blue", "o", "20 rules"),
        ("black", "s", "30 rules"),
    ]

    for colour, marker, label in graph_b:

        raw = pd.read_csv(
            f"test_results/sotw_graph_b_{colour}.csv"
        )

        avg = pd.read_csv(
            f"test_results/avg_sotw_graph_b_{colour}.csv"
        )

        ax.scatter(
            raw["sotw_size"],
            raw["runtime_seconds"],
            marker=marker,
            color=colour,
            alpha=0.5
        )

        ax.plot(
            avg["sotw_size"],
            avg["runtime_seconds"],
            marker=marker,
            color=colour,
            label=label
        )

    ax.set_xlabel("Number of events")
    ax.set_title("b)")
    ax.set_xlim(0, 1000)
    ax.set_ylim(0, 1)
    ax.grid(True)
    ax.legend()

    # ==========================================================
    # GRAPH C
    # ==========================================================

    ax = axs[2]

    graph_c = [
        ("red", "x", "100 events"),
        ("blue", "o", "300 events"),
        ("black", "s", "500 events"),
    ]

    for colour, marker, label in graph_c:

        raw = pd.read_csv(
            f"test_results/duties_graph_c_{colour}.csv"
        )

        avg = pd.read_csv(
            f"test_results/avg_duties_graph_c_{colour}.csv"
        )

        ax.scatter(
            raw["duties_per_permission"],
            raw["runtime_seconds"],
            marker=marker,
            color=colour,
            alpha=0.5
        )

        ax.plot(
            avg["duties_per_permission"],
            avg["runtime_seconds"],
            marker=marker,
            color=colour,
            label=label
        )

    ax.set_xlabel("Duties per Permission")
    ax.set_ylabel("Runtime (seconds)")
    ax.set_title("c)")
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 1.7)
    ax.grid(True)
    ax.legend()

    # ==========================================================
    # GRAPH D
    # ==========================================================

    ax = axs[3]

    graph_d = [
        ("red", "x", "100 events"),
        ("blue", "o", "300 events"),
        ("black", "s", "500 events"),
    ]

    for colour, marker, label in graph_d:

        raw = pd.read_csv(
            f"test_results/constraints_graph_d_{colour}.csv"
        )

        avg = pd.read_csv(
            f"test_results/avg_constraints_graph_d_{colour}.csv"
        )

        ax.scatter(
            raw["constraints_number_min"],
            raw["runtime_seconds"],
            marker=marker,
            color=colour,
            alpha=0.5
        )

        ax.plot(
            avg["constraints_number_min"],
            avg["runtime_seconds"],
            marker=marker,
            color=colour,
            label=label
        )

    ax.set_xlabel("Constraints per Rule")
    ax.set_title("d)")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 0.5)
    ax.grid(True)
    ax.legend()

    plt.tight_layout()

    output_path = "test_results/scalability_summary.png"

    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"\n[PLOT] Saved combined plot to: {output_path}")

generate_combined_plot()

print("\nALL EXPERIMENTS COMPLETED.")