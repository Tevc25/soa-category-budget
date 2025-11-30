from datetime import datetime
from typing import List
from pydantic import BaseModel, field_serializer

class CategoryRequest(BaseModel):
    name: str
    
class CategoryItem(BaseModel):
    item_id: str
    item_name: str
    item_price: float
    item_quantity: int
    created_at: str | None = None
class CategoryResponse(BaseModel):
    category_id: str
    name: str
    items: List[CategoryItem]
    created_at: datetime
    updated_at: datetime
    
    @field_serializer("created_at", "updated_at", mode="plain", when_used="json")
    def serialize_datetime(self, value: datetime) -> str:
        return value.strftime("%Y/%m/%d %H:%M:%S")