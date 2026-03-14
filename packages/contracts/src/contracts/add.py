from pydantic import BaseModel


class AddNumbersRequest(BaseModel):
    a: int
    b: int
