from pydantic import BaseModel


class SearchEntitiesFoundEntity(BaseModel):
    id: str
    type: str
