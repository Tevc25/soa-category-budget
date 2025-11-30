import re
from datetime import datetime
from bson import ObjectId
from db.database import get_db
from models.budget_model import BudgetRequest

MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

class BudgetService:
    def __init__(self):
        self.db = get_db()
        self.budgets = self.db["budget_data"]
        self.categories = self.db["category_data"]

    def upsert_budget(self, user_id: str, payload: BudgetRequest):
        if not MONTH_RE.match(payload.month):
            raise ValueError("month must be in YYYY-MM format")
        if payload.limit <= 0:
            raise ValueError("limit must be greater than 0")

        cat = self.categories.find_one({"_id": ObjectId(payload.category_id), "user_id": user_id})
        if not cat:
            raise ValueError("Category not found")

        query = {
            "user_id": user_id,
            "month": payload.month,
            "category_id": payload.category_id
        }

        now = datetime.now()
        existing = self.budgets.find_one(query)

        if existing:
            self.budgets.update_one(
                {"_id": existing["_id"]},
                {"$set": {"limit": float(payload.limit), "updated_at": now}}
            )
            return {"message": "Budget updated successfully", "budget_id": str(existing["_id"])}

        doc = {
            **query,
            "limit": float(payload.limit),
            "created_at": now,
            "updated_at": now
        }
        res = self.budgets.insert_one(doc)
        return {"message": "Budget created successfully", "budget_id": str(res.inserted_id)}

    def get_budgets(self, user_id: str, month: str | None):
        q = {"user_id": user_id}
        if month:
            if not MONTH_RE.match(month):
                raise ValueError("month must be in YYYY-MM format")
            q["month"] = month

        docs = self.budgets.find(q)
        out = []
        for d in docs:
            out.append({
                "budget_id": str(d["_id"]),
                "month": d["month"],
                "category_id": d["category_id"],
                "limit": d["limit"],
                "created_at": d["created_at"],
                "updated_at": d["updated_at"]
            })
        return out

    def delete_budget(self, user_id: str, budget_id: str):
        res = self.budgets.delete_one({"_id": ObjectId(budget_id), "user_id": user_id})
        if res.deleted_count == 0:
            raise ValueError("Budget not found")
        return {"message": "Budget deleted successfully"}
    
    def update_budget(self, user_id: str, budget_id: str, payload: BudgetRequest):
        if not MONTH_RE.match(payload.month):
            raise ValueError("month must be in YYYY-MM format")
        if payload.limit <= 0:
            raise ValueError("limit must be greater than 0")

        cat = self.categories.find_one({"_id": ObjectId(payload.category_id), "user_id": user_id})
        if not cat:
            raise ValueError("Category not found")

        res = self.budgets.update_one(
            {"_id": ObjectId(budget_id), "user_id": user_id},
            {"$set": {
                "month": payload.month,
                "category_id": payload.category_id,
                "limit": float(payload.limit),
                "updated_at": datetime.now()
            }}
        )

        if res.matched_count == 0:
            raise ValueError("Budget not found")

        return {"message": "Budget updated successfully"}