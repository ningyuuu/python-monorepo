from pydantic import BaseModel, ConfigDict


class QueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str


class SummariseDocRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_link: str
    blob_link: str
    blob_type: str


class ExtractDataRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_link: str
    blob_link: str
    blob_type: str
