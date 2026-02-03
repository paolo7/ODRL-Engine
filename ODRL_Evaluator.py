import Evaluation.evaluator_functions
import rdf_utils
import SotW_generator
import pandas as pd

def evaluate_ODRL_from_files(policy_file, SotW_file):
    graph = rdf_utils.load(policy_file)[0]
    graph_rules = SotW_generator.extract_rule_list_from_policy(graph)
    df = pd.read_csv(SotW_file)
    return  evaluate_ODRL_on_dataframe(graph_rules, df)

def evaluate_ODRL_on_dataframe(rules, SotW_file):
    return True, {}, "Dummy function returned true. \n\nRules:\n"+str(rules)+"\n\nDataframe:\n"+str(SotW_file)

#print("Evaluation: "+str(evaluate_ODRL_from_files("example_policies/exampleEvaluationPolicy.ttl","example_policies/exampleSotW.csv")))
