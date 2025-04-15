from pydantic import BaseModel


class DataItem(BaseModel):
    name: str | None = ""
    value: str | None = ""
