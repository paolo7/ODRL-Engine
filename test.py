import rdflib
import pyshacl
import test_utils
import ODRL_Evaluator
import SotW_generator
import validate
import os
import uuid
import time

total_eval_time = 0.0
total_eval_calls = 0

tests_passed = 0
tests_failed = 0
test_log = []

def timed_evaluation(func, *args, **kwargs):
    global total_eval_time, total_eval_calls

    start = time.perf_counter()
    result = func(*args, **kwargs)
    end = time.perf_counter()

    total_eval_time += (end - start)
    total_eval_calls += 1

    return result

def run_SotW_tests(test_repetitions, test_cases, test_name ):
    global tests_passed
    global tests_failed
    global test_log

    os.makedirs("error_log_files", exist_ok=True)

    def log_failure(pair, expected):
        uid = uuid.uuid4().hex[:8]

        policy_path = f"error_log_files/{uid}_policy.ttl"
        sotw_path = f"error_log_files/{uid}_sotw.csv"
        log_path = f"error_log_files/{uid}_log.txt"

        # Save ODRL graph
        pair[0].serialize(destination=policy_path, format="turtle")

        # Save SotW dataframe
        pair[1].to_csv(sotw_path, index=False)

        # Re-run evaluation once and capture diagnostics
        FEATURE_TYPE_MAP = {f["iri"]: f["type"] for f in SotW_generator.extract_features_list_from_policy(pair[0])}
        result = ODRL_Evaluator.evaluate_ODRL_on_dataframe(
            SotW_generator.extract_rule_list_from_policy(pair[0]),
            pair[1],
            FEATURE_TYPE_MAP
        )

        with open(log_path, "w", encoding="utf-8") as f:
            f.write("=== ODRL State of the World Evaluation Messages ===\n\n")
            if expected:
                f.write("=== Expected Valid, found Invalid ===\n\n")
            else:
                f.write("=== Expected Invalid, found Valid ===\n\n")
            f.write("Result[1]:\n")
            f.write(str(result[1]))
            f.write("\n\nResult[2]:\n")
            f.write(str(result[2]))
            f.write("\n")

        return uid

    for pair in test_cases["valid_pairs"]:
        FEATURE_TYPE_MAP = {f["iri"]: f["type"] for f in SotW_generator.extract_features_list_from_policy(pair[0])}
        if ODRL_Evaluator.evaluate_ODRL_on_dataframe(SotW_generator.extract_rule_list_from_policy(pair[0]), pair[1], FEATURE_TYPE_MAP)[1]:
            tests_passed += 1
        else:
            tests_failed += 1
            uid = log_failure(pair, True)
            test_log.append(
                f"Failed {test_name} (should be valid, got invalid) | logged as {uid}"
            )

    for pair in test_cases["invalid_pairs"]:
        FEATURE_TYPE_MAP = {f["iri"]: f["type"] for f in SotW_generator.extract_features_list_from_policy(pair[0])}
        if not ODRL_Evaluator.evaluate_ODRL_on_dataframe(SotW_generator.extract_rule_list_from_policy(pair[0]), pair[1],FEATURE_TYPE_MAP)[1]:
            tests_passed += 1
        else:
            tests_failed += 1
            uid = log_failure(pair, False)
            test_log.append(
                f"Failed {test_name} (should be invalid, got valid) | logged as {uid}"
            )



def run_folder_evaluation_tests():
    global tests_passed
    global tests_failed
    global test_log

    base_dirs = {
        "valid": "test_cases/evaluation/valid",
        "invalid": "test_cases/evaluation/invalid"
    }

    # Category statistics
    category_stats = {}
    # Format:
    # {
    #   "category_name": {"passed": int, "total": int}
    # }

    def get_category(txt_path):
        """Return category from second line of txt file."""
        if not os.path.exists(txt_path):
            return "other"

        try:
            with open(txt_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            if len(lines) >= 2:
                category = lines[1].strip()
                if category:
                    return category

        except Exception:
            pass

        return "other"

    def get_first_line(txt_path):
        """Return first line if exists."""
        if not os.path.exists(txt_path):
            return None

        try:
            with open(txt_path, "r", encoding="utf-8") as f:
                line = f.readline().strip()

            if line:
                return line

        except Exception:
            pass

        return None

    for expected_type, folder in base_dirs.items():

        if not os.path.exists(folder):
            continue

        files = os.listdir(folder)

        base_names = set(
            os.path.splitext(f)[0]
            for f in files
            if f.endswith(".ttl")
        )

        for base in base_names:

            ttl_path = os.path.join(folder, base + ".ttl")
            csv_path = os.path.join(folder, base + ".csv")
            txt_path = os.path.join(folder, base + ".txt")

            display_name = os.path.join(folder, base)

            if not os.path.exists(csv_path):
                print(f"Skipping {display_name}: missing CSV file")
                continue

            # Determine category
            category = get_category(txt_path)

            if category not in category_stats:
                category_stats[category] = {"passed": 0, "total": 0}

            category_stats[category]["total"] += 1

            try:
                #result_list = ODRL_Evaluator.evaluate_ODRL_from_files_streaming(ttl_path, csv_path)
                result_list = timed_evaluation(
                    ODRL_Evaluator.evaluate_ODRL_from_files_streaming,
                    ttl_path,
                    csv_path
                )
                result = result_list[1] #all(r.get("decision") == "ALLOW" for r in result_list)

            except Exception as e:

                tests_failed += 1

                print(f"\nEvaluation test of {display_name} failed due to exception:")
                print(str(e))

                continue

            expected_valid = (expected_type == "valid")

            test_ok = (
                (result and expected_valid)
                or
                ((not result) and (not expected_valid))
            )

            if test_ok:

                tests_passed += 1
                category_stats[category]["passed"] += 1

            else:

                tests_failed += 1

                expectation_str = (
                    "valid"
                    if expected_valid
                    else "invalid"
                )

                print(
                    f"Evaluation test of {base} failed "
                    f"(was expected to be {expectation_str})"
                )

                # Print first line if exists
                first_line = get_first_line(txt_path)

                if first_line:
                    print(first_line)

                test_log.append(
                    f"Failed evaluation test {base} "
                    f"(expected {expectation_str})"
                )

    # ---- CATEGORY SUMMARY ----

    print("\nFolder tests category summary:")

    for category in sorted(category_stats.keys()):

        passed = category_stats[category]["passed"]
        total = category_stats[category]["total"]

        print(f"- Tests: {category} {passed}/{total}")


def runTests(test_repetitions = 0):
    global tests_passed
    global tests_failed
    global test_log

    tests_passed = 0
    tests_failed = 0
    test_log = []

    # VALIDATION TESTS

    # validate.generate_ODRL_diagnostic_report("example_policies/example_valid.json")
    # validate.generate_ODRL_diagnostic_report("example_policies/example_invalid.json")
    if validate.diagnose_ODRL("example_policies/example_valid.json")[3]:
        tests_passed += 1
    else:
        tests_failed += 1
        test_log.append("Failed to validate example_policies/example_valid.json as valid")

    if not validate.diagnose_ODRL("example_policies/example_invalid.json")[3]:
        tests_passed += 1
    else:
        tests_failed += 1
        test_log.append("Failed to validate example_policies/example_invalid.json as invalid")

    # EVALUATION TESTS

    # evaluation with datetime
    result_list = ODRL_Evaluator.evaluate_ODRL_from_files("example_policies/example_valid3.ttl", "example_policies/sotw_ex3_valid.csv")
    result = result_list[1] #all(r.get("decision") == "ALLOW" for r in result_list)
    if result:
        tests_passed += 1
    else:
        tests_failed += 1
        test_log.append("Failed to evaluate datetime example example_policies/example_valid3.ttl as valid on SotW example_policies/sotw_ex3_valid.csv")

    result_list = ODRL_Evaluator.evaluate_ODRL_from_files("example_policies/example_valid3.ttl", "example_policies/sotw_ex3_invalid.csv")
    result = result_list[1] # all(r.get("decision") == "ALLOW" for r in result_list)
    if not result:
        tests_passed += 1
    else:
        tests_failed += 1
        test_log.append("Failed to evaluate datetime example example_policies/example_valid3.ttl as invalid on SotW example_policies/sotw_ex3_invalid.csv")

    run_SotW_tests(test_repetitions,
                   test_utils.generate_permission_test_cases(test_n = test_repetitions,
                                                             p_rule_n = 4,
                                                             f_rule_n = 0,),
                   "Test of SotW Evaluation for Permissions Only"
                   )

    # Folder-based evaluation tests
    run_folder_evaluation_tests()

    # PRINT SUMMARY

    print(f"\nTOTAL TESTS PASSED {tests_passed}/{tests_passed + tests_failed}")

    for log in test_log:
        print(log)

    if total_eval_calls > 0:
        avg_time = total_eval_time / total_eval_calls
        print(f"\nAverage evaluation time: {avg_time:.6f} seconds over {total_eval_calls} runs")

    if tests_failed > 0:
        exit(1)
    else:
        exit(0)


runTests()