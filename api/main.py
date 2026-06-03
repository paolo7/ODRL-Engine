from io import StringIO

import pandas as pd
from fastapi import FastAPI, HTTPException

import rdf_utils
import SotW_generator
import ODRL_Evaluator as Evaluator

from api.models import (
    EvaluateRequest,
    EvaluateResponse
)

app = FastAPI(
    title="ODRL Evaluator API",
    version="1.0.0"
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/evaluate_policy_on_sotw")
def evaluate_policy_on_sotw(
    request: EvaluateRequest
):

    result = Evaluator.evaluate_ODRL_from_strings(
        request.policy,
        request.sotw
    )

    return convert_result_to_response(result)