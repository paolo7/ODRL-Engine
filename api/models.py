from typing import Any
from pydantic import BaseModel, ConfigDict


class EvaluateRequest(BaseModel):
    policy: str
    sotw: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "policy": "@prefix odrl: <http://www.w3.org/ns/odrl/2/> .\n@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n\n<http://example.com/policy:6161>\n  a odrl:Offer ;\n  odrl:permission [\n    odrl:action [\n      rdf:value odrl:print ;\n      odrl:refinement [\n        odrl:leftOperand odrl:resolution ;\n        odrl:operator odrl:lteq ;\n        odrl:rightOperand 1200 ;\n        odrl:unit \"http://dbpedia.org/resource/Dots_per_inch\"^^xsd:string\n      ]\n    ] ;\n    odrl:assignee <http://example.com/org:John> ;\n    odrl:target <http://example.com/document:1234> ;\n  ] ;\n  odrl:profile <http://example.com/odrl:profile:10> .",

                "sotw": "http://www.w3.org/ns/odrl/2/dateTime,http://www.w3.org/ns/odrl/2/Party,http://www.w3.org/ns/odrl/2/Action,http://www.w3.org/ns/odrl/2/Asset,http://www.example.com/age,http://www.w3.org/ns/odrl/2/Action http://www.w3.org/ns/odrl/2/resolution,http://www.w3.org/ns/odrl/2/Party http://www.w3.org/ns/odrl/2/adminLevel\n2026-01-11T11:33:10.665638,http://example.com/org:John,http://www.w3.org/ns/odrl/2/print,http://example.com/document:1234,0,1190,\n2026-01-11T11:13:10.665638,http://example.com/org:John,http://www.w3.org/ns/odrl/2/print,http://example.com/document:1234,,1142,12"
            }
        }
    )


class EvaluateResponse(BaseModel):
    evaluation_state: Any
    valid: bool
    rows_violating_permissions: list[int]
    rows_violating_prohibitions: list[int]
    obligations_not_satisfied: list[Any]
    unfulfilled_duties: list[Any]
    unfulfilled_consequences: list[Any]
    unfulfilled_remedies: list[Any]