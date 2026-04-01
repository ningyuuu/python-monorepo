from pydantic import BaseModel, ConfigDict, EmailStr


class QueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str
    email: EmailStr


class SummariseDocRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_link: str
    blob_link: str
    blob_type: str
    email: EmailStr


class ExtractQuoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_link: str
    blob_link: str
    blob_type: str
    email: EmailStr


class ExtractPoItemsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_link: str
    blob_link: str
    blob_type: str
    email: EmailStr
