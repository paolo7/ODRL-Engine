from io import StringIO
import os
import pandas as pd
from fastapi import FastAPI, HTTPException, Body

import rdf_utils
import SotW_generator
import ODRL_Evaluator as Evaluator

from api.models import (
    EvaluateRequest,
    EvaluateResponse,
    PolicyFeaturesRequest,
    PolicyFeaturesResponse,
)

EXTERNAL_PREFIX = os.environ.get("ODRL_EXTERNAL_PREFIX", "").strip("/")
ROOT_PATH = f"/{EXTERNAL_PREFIX}/api" if EXTERNAL_PREFIX else "/api"

app = FastAPI(
    title="ODRL Evaluator API",
    version="1.0.0",
    root_path=ROOT_PATH,
)

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post(
    "/evaluate_policy_on_sotw",
    response_model=EvaluateResponse
)
def evaluate_policy_on_sotw(request: EvaluateRequest):

    result = Evaluator.evaluate_ODRL_from_strings(
        request.policy,
        request.sotw
    )

    (
        evaluation_state,
        validity,
        permission_rows,
        prohibition_rows,
        obligations,
        duties,
        consequences,
        remedies
    ) = result

    return EvaluateResponse(
        evaluation_state=evaluation_state,
        valid=bool(validity),
        rows_violating_permissions=permission_rows,
        rows_violating_prohibitions=prohibition_rows,
        obligations_not_satisfied=obligations,
        unfulfilled_duties=duties,
        unfulfilled_consequences=consequences,
        unfulfilled_remedies=remedies
    )

@app.post(
    "/get_policy_features",
    response_model=PolicyFeaturesResponse
)
def get_policy_features(
    request: PolicyFeaturesRequest = Body(
        examples={
            "ttl": {
                "summary": "ODRL policy in Turtle",
                "value": {
                    "policy": "@prefix odrl: <http://www.w3.org/ns/odrl/2/> .\n@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n\n<http://example.com/policy:6161>\n  a odrl:Offer ;\n  odrl:permission [\n    odrl:action [\n      rdf:value odrl:print ;\n      odrl:refinement [\n        odrl:leftOperand odrl:resolution ;\n        odrl:operator odrl:lteq ;\n        odrl:rightOperand 1200 ;\n        odrl:unit \"http://dbpedia.org/resource/Dots_per_inch\"^^xsd:string\n      ]\n    ] ;\n    odrl:assignee <http://example.com/org:John> ;\n    odrl:target <http://example.com/document:1234> ;\n  ] ;\n  odrl:profile <http://example.com/odrl:profile:10> ."
                }
            },
            "jsonld": {
                "summary": "ODRL policy in JSON-LD",
                "value": {
                    "policy": "{\n  \"permission\": [\n    {\n      \"action\": {\n        \"source\": \"https://w3id.org/dpv/owl#Access\",\n        \"refinement\": [\n          {\n            \"leftOperand\": \"hasStartTime\",\n            \"operator\": \"http://www.w3.org/ns/odrl/2/gteq\",\n            \"rightOperand\": \"2026-07-01\"\n          },\n          {\n            \"leftOperand\": \"hasFinishTime\",\n            \"operator\": \"http://www.w3.org/ns/odrl/2/lteq\",\n            \"rightOperand\": \"2026-07-31\"\n          }\n        ]\n      },\n      \"assignee\": {\n        \"@type\": \"PartyCollection\",\n        \"source\": \"https://w3id.org/dpv/owl#LegalEntity\",\n        \"refinement\": [\n          {\n            \"leftOperand\": \"hasName\",\n            \"operator\": \"http://www.w3.org/ns/odrl/2/eq\",\n            \"rightOperand\": \"GATE\"\n          },\n          {\n            \"leftOperand\": \"hasAddress\",\n            \"operator\": \"http://www.w3.org/ns/odrl/2/eq\",\n            \"rightOperand\": \"Gate Street 123\"\n          }\n        ]\n      },\n      \"target\": \"http://example.org/datasets/economicIndicators\",\n      \"constraint\": [\n        {\n          \"and\": [\n            {\n              \"leftOperand\": \"purpose\",\n              \"operator\": \"http://www.w3.org/ns/odrl/2/eq\",\n              \"rightOperand\": \"https://w3id.org/dpv/owl#AcademicResearch\"\n            },\n            {\n              \"leftOperand\": \"isMonitoredBy\",\n              \"operator\": \"http://www.w3.org/ns/odrl/2/eq\",\n              \"rightOperand\": \"Sofia University\"\n            },\n            {\n              \"leftOperand\": \"Location\",\n              \"operator\": \"http://www.w3.org/ns/odrl/2/eq\",\n              \"rightOperand\": \"Sofia\"\n            },\n            {\n              \"leftOperand\": \"http://www.w3.org/ns/odrl/2/dateTime\",\n              \"operator\": \"http://www.w3.org/ns/odrl/2/lteq\",\n              \"rightOperand\": \"2026-12-31\"\n            }\n          ]\n        }\n      ]\n    }\n  ],\n  \"uid\": \"http://example.org/policy-f79c55f9-f95b-43c6-ab88-c0d32fe2980b\",\n  \"@context\": [\n    \"http://www.w3.org/ns/odrl.jsonld\",\n    {\n      \"dcat\": \"http://www.w3.org/ns/dcat#\",\n      \"dpv\": \"https://w3id.org/dpv/dpv-owl#\"\n    }\n  ],\n  \"@type\": \"Policy\"\n}"
                }
            }
        }
    )
):
    try:
        features = SotW_generator.extract_features_list_from_string(
            request.policy
        )
        return PolicyFeaturesResponse(features=features)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))