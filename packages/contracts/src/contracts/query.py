from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str
    model: str | None = None
