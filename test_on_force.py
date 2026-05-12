import os
import ODRL_Evaluator
import pandas as pd
import time

if __name__ == "__main__":
    folder = "test_cases/evaluation/force"  # Replace with your desired folder path
    files = os.listdir(folder)

    base_names = list(
        os.path.splitext(f)[0]
        for f in files
        if f.endswith(".ttl"))
    
    base_names.sort()
    
    dataframe = pd.read_csv("test_cases/evaluation/force/expected_results.csv")
    i = 0
    results = dataframe["result"].tolist()
    expected_results = [row == "allowed" for row in dataframe["result"].tolist()]
    runtimes = []

    for base in base_names:
        ttl_path = os.path.join(folder, base + ".ttl")
        csv_path = os.path.join(folder, base + ".csv")
        start = time.perf_counter()
        result = ODRL_Evaluator.evaluate_ODRL_from_files(ttl_path, csv_path, normalise=False)
        end =time.perf_counter()
        result_row = result[0]
        ans = result[1] == 1
        total_time = (end - start)*1000
        runtimes.append(total_time)

        print("Ghent: " + str(results[i]) + ", Our system: " + str(ans) + " for " + base)
        i += 1
    print("id,runtime")
    for i, runtime in enumerate(runtimes):
        print(f"{str(i + 1)},{str(runtime)}")

        # print(f"Evaluation result for {base}: {result}")