import os
import json
from fastapi import FastAPI, HTTPException


import rdf_utils
import ODRL_Evaluator as Evaluator
import validate as Validator

from api.models import (
    EvaluateRequest,
    EvaluateResponse,
    PolicyFeaturesRequest,
    PolicyFeaturesResponse,
    ValidateODRLRequest,
    ValidateODRLResponse,
    EvaluateAccessResponse,
    EvaluateAccessRequest
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
        request.sotw,
        request.evaluation_state
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
def get_policy_features(request: PolicyFeaturesRequest):
    try:
        features = rdf_utils.extract_features_list_from_string(
            request.policy
        )
        return PolicyFeaturesResponse(features=features)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post(
    "/validate_ODRL",
    response_model=ValidateODRLResponse
)
def validate_odrl(request: ValidateODRLRequest):
    try:
        result = Validator.validate_ODRL_from_string(request.odrl)
        return ValidateODRLResponse(result=result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post(
    "/evaluate_access_request",
    response_model=EvaluateAccessResponse
)
def evaluate_access_request(request: EvaluateAccessRequest):
    try:
        result = Evaluator.evaluate_ODRL_access_request_from_string(
            access_request_string=json.dumps(request.access_request),
            policy_string=request.policy,
            state_of_the_world_string=request.state_of_the_world,
            evaluation_state_string=(
                json.dumps(request.evaluation_state)
                if request.evaluation_state is not None
                else None
            ),
            semantics_for_duties=request.semantics_for_duties,
            semantics_by_default=request.semantics_by_default,
            reasoning=request.reasoning,
        )

        return EvaluateAccessResponse(
            permissions_matched=result["permissions_matched"],
            prohibitions_matched=result["prohibitions_matched"],
            accept_decision=result["accept_decision"],
            accept_explanation=result["accept_explanation"],
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))