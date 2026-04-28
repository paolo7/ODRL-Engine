import os
import ODRL_Evaluator
import pandas as pd

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

    for base in base_names:
        ttl_path = os.path.join(folder, base + ".ttl")
        csv_path = os.path.join(folder, base + ".csv")
        result = ODRL_Evaluator.evaluate_files(ttl_path, csv_path)
        result_row = result[0]

        ans = all(row["decision"] == "ALLOW" for row in result_row["row_permission_prohibitions"])

        if ans != expected_results[i]:
            print("Ghent: " + str(results[i]) + ", Our system: " + str(ans) + " for " + base)
        i += 1

        # print(f"Evaluation result for {base}: {result}")