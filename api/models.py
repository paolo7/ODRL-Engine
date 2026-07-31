from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class EvaluateRequest(BaseModel):
    policy: str = Field(
        description=(
            "An ODRL policy serialized as a string. "
            "All major RDF serialisations like Turtle (TTL) and JSON-LD are supported. "
        )
    )

    sotw: str = Field(
        description=(
            "A State of the World object (log of events) in CSV format serialised as a string. "
            "It should include, at a minimum, a one column for each feature of the policy, reusing the same IRIs. "
            "Use function /get_policy_features to see the list of required features and their IRIs. "
        )
    )

    evaluation_state: dict | None = Field(
        default=None,
        description=(
            "Optional Evaluation State returned by a previous call to "
            "/evaluate_policy_on_sotw. If provided, evaluation resumes from "
            "this state instead of starting a new evaluation. Use this field "
            "if you want to evaluate incrementally, for example in a streaming "
            "scenario. Omit or set to null to begin a fresh evaluation. "
        )
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "policy": "@prefix odrl: <http://www.w3.org/ns/odrl/2/> .\n@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n\n<http://example.com/policy:6161>\n  a odrl:Offer ;\n  odrl:permission [\n    odrl:action [\n      rdf:value odrl:print ;\n      odrl:refinement [\n        odrl:leftOperand odrl:resolution ;\n        odrl:operator odrl:lteq ;\n        odrl:rightOperand 1200 ;\n        odrl:unit \"http://dbpedia.org/resource/Dots_per_inch\"^^xsd:string\n      ]\n    ] ;\n    odrl:assignee <http://example.com/org:John> ;\n    odrl:target <http://example.com/document:1234> ;\n  ] ;\n  odrl:profile <http://example.com/odrl:profile:10> .",

                "sotw": "http://www.w3.org/ns/odrl/2/dateTime,http://www.w3.org/ns/odrl/2/Party,http://www.w3.org/ns/odrl/2/Action,http://www.w3.org/ns/odrl/2/Asset,http://www.example.com/age,http://www.w3.org/ns/odrl/2/Action http://www.w3.org/ns/odrl/2/resolution,http://www.w3.org/ns/odrl/2/Party http://www.w3.org/ns/odrl/2/adminLevel\n2026-01-11T11:33:10.665638,http://example.com/org:John,http://www.w3.org/ns/odrl/2/print,http://example.com/document:1234,0,1190,\n2026-01-11T11:13:10.665638,http://example.com/org:John,http://www.w3.org/ns/odrl/2/print,http://example.com/document:1234,,1142,12"
            }
        }
    )


class EvaluateResponse(BaseModel):
    evaluation_state: Any = Field(
        description=(
            "The Evaluation State object in JSON format. "
            "It contains information that can be used to restart evaluation on newer States of the World if "
            "the evaluation is done in batches or streaming."
        )
    )
    valid: bool = Field(
        description=(
            "True if the State of the World is compliant (valid), or False if the State of the World is not compliant (invalid). "
        )
    )
    rows_violating_permissions: list[int] = Field(
        description=(
            "The list of row indexes of rows that do not match any permission. "
        )
    )
    rows_violating_prohibitions: list[int] = Field(
        description=(
            "The list of row indexes of rows that match one or more prohibitions. "
        )
    )
    obligations_not_satisfied: list[Any] = Field(
        description=(
            "The list of unmet obligations that have not been satisfied in the State of the World. "
        )
    )
    unfulfilled_duties: list[Any] = Field(
        description=(
            "The list of required duties that have not been satisfied in the State of the World. "
        )
    )
    unfulfilled_consequences: list[Any]  = Field(
        description=(
            "The list of required consequences that have not been satisfied in the State of the World. "
        )
    )
    unfulfilled_remedies: list[Any] = Field(
        description=(
            "The list of required remedies that have not been satisfied in the State of the World. "
        )
    )

class PolicyFeaturesRequest(BaseModel):
    policy: str = Field(
        description=(
            "An ODRL policy serialized as a string. "
            "All major RDF serialisations like Turtle (TTL) and JSON-LD are supported. "
        )
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "policy": "@prefix odrl: <http://www.w3.org/ns/odrl/2/> .\n@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n\n<http://example.com/policy:6161>\n  a odrl:Offer ;\n  odrl:permission [\n    odrl:action [\n      rdf:value odrl:print ;\n      odrl:refinement [\n        odrl:leftOperand odrl:resolution ;\n        odrl:operator odrl:lteq ;\n        odrl:rightOperand 1200 ;\n        odrl:unit \"http://dbpedia.org/resource/Dots_per_inch\"^^xsd:string\n      ]\n    ] ;\n    odrl:assignee <http://example.com/org:John> ;\n    odrl:target <http://example.com/document:1234> ;\n  ] ;\n  odrl:profile <http://example.com/odrl:profile:10> ."
                },
                {
                    "policy": "{\n  \"permission\": [\n    {\n      \"action\": {\n        \"source\": \"https://w3id.org/dpv/owl#Access\",\n        \"refinement\": [\n          {\n            \"leftOperand\": \"hasStartTime\",\n            \"operator\": \"http://www.w3.org/ns/odrl/2/gteq\",\n            \"rightOperand\": \"2026-07-01\"\n          },\n          {\n            \"leftOperand\": \"hasFinishTime\",\n            \"operator\": \"http://www.w3.org/ns/odrl/2/lteq\",\n            \"rightOperand\": \"2026-07-31\"\n          }\n        ]\n      },\n      \"assignee\": {\n        \"@type\": \"PartyCollection\",\n        \"source\": \"https://w3id.org/dpv/owl#LegalEntity\",\n        \"refinement\": [\n          {\n            \"leftOperand\": \"hasName\",\n            \"operator\": \"http://www.w3.org/ns/odrl/2/eq\",\n            \"rightOperand\": \"GATE\"\n          },\n          {\n            \"leftOperand\": \"hasAddress\",\n            \"operator\": \"http://www.w3.org/ns/odrl/2/eq\",\n            \"rightOperand\": \"Gate Street 123\"\n          }\n        ]\n      },\n      \"target\": \"http://example.org/datasets/economicIndicators\",\n      \"constraint\": [\n        {\n          \"and\": [\n            {\n              \"leftOperand\": \"purpose\",\n              \"operator\": \"http://www.w3.org/ns/odrl/2/eq\",\n              \"rightOperand\": \"https://w3id.org/dpv/owl#AcademicResearch\"\n            },\n            {\n              \"leftOperand\": \"isMonitoredBy\",\n              \"operator\": \"http://www.w3.org/ns/odrl/2/eq\",\n              \"rightOperand\": \"Sofia University\"\n            },\n            {\n              \"leftOperand\": \"Location\",\n              \"operator\": \"http://www.w3.org/ns/odrl/2/eq\",\n              \"rightOperand\": \"Sofia\"\n            },\n            {\n              \"leftOperand\": \"http://www.w3.org/ns/odrl/2/dateTime\",\n              \"operator\": \"http://www.w3.org/ns/odrl/2/lteq\",\n              \"rightOperand\": \"2026-12-31\"\n            }\n          ]\n        }\n      ]\n    }\n  ],\n  \"uid\": \"http://example.org/policy-f79c55f9-f95b-43c6-ab88-c0d32fe2980b\",\n  \"@context\": [\n    \"http://www.w3.org/ns/odrl.jsonld\",\n    {\n      \"dcat\": \"http://www.w3.org/ns/dcat#\",\n      \"dpv\": \"https://w3id.org/dpv/dpv-owl#\"\n    }\n  ],\n  \"@type\": \"Policy\"\n}"
                }
            ]
        }
    )

class PolicyFeaturesRequest(BaseModel):
    policy: str = Field(
        description=(
            "An ODRL policy serialized as a string. "
            "All major RDF serialisations like Turtle (TTL) and JSON-LD are supported. "
        )
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "policy": "@prefix odrl: <http://www.w3.org/ns/odrl/2/> .\n@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n\n<http://example.com/policy:6161>\n  a odrl:Offer ;\n  odrl:permission [\n    odrl:action [\n      rdf:value odrl:print ;\n      odrl:refinement [\n        odrl:leftOperand odrl:resolution ;\n        odrl:operator odrl:lteq ;\n        odrl:rightOperand 1200 ;\n        odrl:unit \"http://dbpedia.org/resource/Dots_per_inch\"^^xsd:string\n      ]\n    ] ;\n    odrl:assignee <http://example.com/org:John> ;\n    odrl:target <http://example.com/document:1234> ;\n  ] ;\n  odrl:profile <http://example.com/odrl:profile:10> ."
            }
        }
    )

class PolicyFeaturesResponse(BaseModel):
    features: list[dict] = Field(
        description=(
            "The list of unique policy features extracted from the policy. "
            "Each feature is defined by its IRI and provides an indication of its expected datatype."
        )
    )