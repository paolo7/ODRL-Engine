from rdflib.namespace import RDF
import rdflib
import csv
import pandas as pd
import sys

base_features = [
    {"iri": "http://www.w3.org/ns/odrl/2/dateTime",
     "type": "http://www.w3.org/2001/XMLSchema#dateTime"},
    {"iri": "http://www.w3.org/ns/odrl/2/Party",
     "type": "http://www.w3.org/ns/shacl#IRI"},
    {"iri": "http://www.w3.org/ns/odrl/2/Action",
     "type": "http://www.w3.org/ns/shacl#IRI"},
    {"iri": "http://www.w3.org/ns/odrl/2/Asset",
     "type": "http://www.w3.org/ns/shacl#IRI"},
]

ODRL = rdflib.Namespace("http://www.w3.org/ns/odrl/2/")
SOTW = rdflib.Namespace("https://w3id.org/force/sotw#")
EX = rdflib.Namespace("http://example.org/")
REPORT = rdflib.Namespace("https://w3id.org/force/compliance-report#")
DCT = rdflib.Namespace("http://purl.org/dc/terms/")
TEMP = rdflib.Namespace("http://example.com/request/")

def translate_csv_to_solid_syntax(csv_file, destination_file="translated_sotw.ttl"):
    df = pd.read_csv(csv_file)
    rdf_graph = rdflib.Graph()
    sotw_node = rdflib.URIRef("https://example.com/iri/sotw")
    rdf_graph.add((sotw_node, RDF.type, SOTW.SotW))
    for i, row in df.iterrows():
        evaluation_node = rdflib.URIRef(f"https://example.com/iri/sotw#{i}")
        rdf_graph.add((sotw_node, SOTW.context, evaluation_node))
        rdf_graph.add((rdflib.URIRef(evaluation_node), RDF.type, SOTW.EvaluationRequest))
        for col, val in zip(df.columns, row):
            if not pd.isnull(val):
                if col == "http://www.w3.org/ns/odrl/2/dateTime":
                    rdf_graph.add((rdflib.URIRef(evaluation_node), rdflib.URIRef("http://purl.org/dc/terms/issued"), rdflib.Literal(val, datatype=rdflib.XSD.dateTime)))
                elif col == "http://www.w3.org/ns/odrl/2/Party":
                    rdf_graph.add((rdflib.URIRef(evaluation_node), SOTW.evaluatedParty, rdflib.URIRef(val)))
                elif col == "http://www.w3.org/ns/odrl/2/Action": 
                    rdf_graph.add((rdflib.URIRef(evaluation_node), SOTW.evaluatedAction, rdflib.URIRef(val)))
                elif col == "http://www.w3.org/ns/odrl/2/Asset":
                    rdf_graph.add((rdflib.URIRef(evaluation_node), SOTW.evaluatedTarget, rdflib.URIRef(val)))
                else:
                    blank_node = rdflib.BNode()
                    rdf_graph.add((rdflib.URIRef(evaluation_node), SOTW.requestParameter, blank_node))
                    rdf_graph.add((blank_node, RDF.type, SOTW.RequestParameter))
                    if len(col.split()) > 1:
                        prefix, feature_iri = col.split(" ", 1)
                        if prefix in ["http://www.w3.org/ns/odrl/2/Party", "http://www.w3.org/ns/odrl/2/Action", "http://www.w3.org/ns/odrl/2/Asset"]:
                            rdf_graph.add((blank_node, SOTW.describesFeature, rdflib.URIRef(feature_iri)))
                            rdf_graph.add((blank_node, SOTW.value, rdflib.Literal(val)))
                        else:
                            rdf_graph.add((blank_node, SOTW.describesFeature, rdflib.URIRef(feature_iri)))
                            rdf_graph.add((blank_node, SOTW.value, rdflib.Literal(val)))
                    else:
                        rdf_graph.add((blank_node, SOTW.describesFeature, rdflib.URIRef(col)))
                        rdf_graph.add((blank_node, SOTW.value, rdflib.Literal(val)))
    rdf_graph.serialize(destination=destination_file, format="turtle")

def extract_sotw_from_solid_syntax(policy, request, sotw, destination_csv="extracted_sotw.csv"):
    request_graph = rdflib.Graph().parse(data=request, format="turtle")
    sotw_graph = rdflib.Graph().parse(data=sotw, format="turtle")
    policy_graph = rdflib.Graph().parse(data=policy, format="turtle")
    sotw_graph += policy_graph
    sotw_data = []
    fieldnames = [str(ODRL.dateTime), str(ODRL.Party), str(ODRL.Action), str(ODRL.Asset)]
    current_time = None
    if (None, RDF.type, EX.Sotw) in sotw_graph:
        sotw = sotw_graph.value(None, RDF.type, EX.Sotw)
        for context in sotw_graph.objects(sotw, EX.includes):
            if context == TEMP.currentTime:
                current_time = sotw_graph.value(context, DCT.issued)
            else:
                if sotw_graph.value(context, RDF.type) == REPORT.PolicyReport:
                    sotw_data.append(parse_policy_report(sotw_graph, context))
    else:
        current_time = sotw_graph.value(TEMP.currentTime, DCT.issued)
        for context in sotw_graph.subjects(RDF.type, REPORT.PolicyReport):
             event = parse_policy_report(sotw_graph, context)
             if event is not None:
                 sotw_data.append(event)
    for request in request_graph.subjects(RDF.type, ODRL.Request):
        record = {}
        record[str(ODRL.dateTime)] = current_time
        for permission in request_graph.objects(request, ODRL.permission):
            if (permission, ODRL.action, None) in request_graph:
                record[str(ODRL.Action)] = str(request_graph.value(permission, ODRL.action))
            if (permission, ODRL.target, None) in request_graph:
                record[str(ODRL.Asset)] = str(request_graph.value(permission, ODRL.target))
            if (permission, ODRL.assignee, None) in request_graph:
                record[str(ODRL.Party)] = str(request_graph.value(permission, ODRL.assignee))

        sotw_data.append(record)
    csv_filename = destination_csv
    destination = destination_csv.replace(".csv", ".ttl")
    policy_node = policy_graph.value(None, RDF.type, ODRL.Set) # We assume that the policy graph contains a policy set because that's how the test cases are structured.
    for duty in sotw_graph.subjects(RDF.type, ODRL.Duty):
        permission_node = rdflib.BNode()
        policy_graph.add((permission_node, RDF.type, ODRL.Permission))
        if (duty, ODRL.action, None) in policy_graph:
            policy_graph.add((permission_node, ODRL.action, sotw_graph.value(duty, ODRL.action)))
        if (duty, ODRL.target, None) in policy_graph:
            policy_graph.add((permission_node, ODRL.target, sotw_graph.value(duty, ODRL.target)))
        if (duty, ODRL.assignee, None) in policy_graph:
            policy_graph.add((permission_node, ODRL.assignee, sotw_graph.value(duty, ODRL.assignee)))
        policy_graph.add((policy_node, ODRL.permission, permission_node))
    policy_graph.serialize(destination=destination, format="turtle")
    with open(csv_filename, mode='w', newline='') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sotw_data)
    return sotw_data

def parse_policy_report(sotw_graph, policy_report_node):
    report_data = {}
    report_data[str(ODRL.dateTime)] = sotw_graph.value(policy_report_node, DCT.created)
    for rule in sotw_graph.objects(policy_report_node, REPORT.ruleReport):
        if (rule, RDF.type, REPORT.PermissionReport) in sotw_graph:
            permission_report = rule
            for permission in sotw_graph.objects(permission_report, REPORT.permission):
                result = sotw_graph.value(permission_report, REPORT.result)
                report_data[str(permission)] = str(result)
        if (rule, RDF.type, REPORT.ProhibitionReport) in sotw_graph:
            prohibition_report = rule
            for prohibition in sotw_graph.objects(prohibition_report, REPORT.prohibition):
                result = sotw_graph.value(prohibition_report, REPORT.result)
                report_data[str(prohibition)] = str(result)
        if (rule, RDF.type, REPORT.DutyReport) in sotw_graph:
            if sotw_graph.value(rule, REPORT.attemptState) == REPORT.Attempted:
                if sotw_graph.value(rule, REPORT.deonticState) == REPORT.Fulfilled:
                    duty = sotw_graph.value(rule, REPORT.rule)
                    report_data[str(ODRL.Action)] = sotw_graph.value(duty, ODRL.action)
                    report_data[str(ODRL.Asset)] = sotw_graph.value(duty, ODRL.target)
                    report_data[str(ODRL.Party)] = sotw_graph.value(duty, ODRL.assignee)
                    #TODO: handle constraints
                else:
                    return None
    return report_data

def parse_test_cases_from_md(md_file_path):
    with open(md_file_path, 'r') as file:
        content = file.read()
    filename = md_file_path.split("/")[-1].split(".")[0]
    components = []
    for section in content.split("```")[1:]:
        if section.startswith("ttl"):
            components.append(section[4:].strip())
    extract_sotw_from_solid_syntax(components[0], components[1], components[2], destination_csv=f"test_cases/evaluation/force/extracted_{filename}.csv")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("Please provide the path to a markdown file containing the test case.")
    else:
        parse_test_cases_from_md(args[0])