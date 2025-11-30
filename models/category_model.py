from datetime import datetime
from pydantic import BaseModel, field_serializer

class CategoryRequest(BaseModel):
    name: str
    
class CategoryResponse(BaseModel):
    category_id: str
    name: str
    created_at: datetime
    updated_at: datetime
    
    @field_serializer("created_at", "updated_at", mode="plain", when_used="json")
    def serialize_datetime(self, value: datetime) -> str:
        return value.strftime("%Y/%m/%d %H:%M:%S")