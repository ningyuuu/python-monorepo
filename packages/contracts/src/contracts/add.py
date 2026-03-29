from pydantic import BaseModel, ConfigDict, EmailStr


class AddNumbersRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    a: int
    b: int
    email: EmailStr
