import rdflib
import pyshacl
import test_utils
import ODRL_Evaluator
import SotW_generator
import validate
import os
import uuid

tests_passed = 0
tests_failed = 0
test_log = []

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
        result = ODRL_Evaluator.evaluate_ODRL_on_dataframe(
            SotW_generator.extract_rule_list_from_policy(pair[0]),
            pair[1]
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
        if ODRL_Evaluator.evaluate_ODRL_on_dataframe(SotW_generator.extract_rule_list_from_policy(pair[0]), pair[1])[0]:
            tests_passed += 1
        else:
            tests_failed += 1
            uid = log_failure(pair, True)
            test_log.append(
                f"Failed {test_name} (should be valid, got invalid) | logged as {uid}"
            )

    for pair in test_cases["invalid_pairs"]:
        if not ODRL_Evaluator.evaluate_ODRL_on_dataframe(SotW_generator.extract_rule_list_from_policy(pair[0]), pair[1])[0]:
            tests_passed += 1
        else:
            tests_failed += 1
            uid = log_failure(pair, False)
            test_log.append(
                f"Failed {test_name} (should be invalid, got valid) | logged as {uid}"
            )




def runTests(test_repetitions = 30):
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

    run_SotW_tests(test_repetitions,
                   test_utils.generate_permission_test_cases(test_n = test_repetitions,
                                                             p_rule_n = 4,
                                                             f_rule_n = 0,),
                   "Test of SotW Evaluation for Permissions Only"
                   )

    # PRINT SUMMARY

    print(f"TESTS PASSED {tests_passed}/{tests_passed + tests_failed}")

    for log in test_log:
        print(log)


runTests()