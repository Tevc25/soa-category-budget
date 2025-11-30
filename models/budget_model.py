from datetime import datetime
from pydantic import BaseModel, field_serializer

class BudgetRequest(BaseModel):
    month : str
    category_id: str
    limit: float
    
class BudgetResponse(BaseModel):
    budget_id: str
    month: str
    category_id: str
    limit: str
    created_at: datetime
    updated_at: datetime
    
    @field_serializer("created_at", "updated_at", mode="plain", when_used="json")
    def serialize_datetime(self, value: datetime) -> str:
        return value.strftime("%Y%m%d %H:%M:%S")