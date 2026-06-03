from pydantic import BaseModel


class EvaluateRequest(BaseModel):
    policy: str
    sotw: str


class EvaluateResponse(BaseModel):
    valid: bool
    violations: list
    message: str