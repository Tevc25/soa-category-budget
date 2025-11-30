from datetime import datetime
from bson import ObjectId
from db.database import get_db
from models.category_model import CategoryRequest

class CategoryService:
    def __init__(self):
        self.db = get_db()
        self.col = self.db["category_data"]

    def create_category(self, user_id: str, payload: CategoryRequest) -> str:
        name = payload.name.strip()
        if name == "":
            raise ValueError("Category name can not be empty")

        exists = self.col.find_one({"user_id": user_id, "name": name})
        if exists:
            raise ValueError("Category with this name already exists")

        now = datetime.now()
        doc = {"user_id": user_id, "name": name, "created_at": now, "updated_at": now}
        res = self.col.insert_one(doc)
        return str(res.inserted_id)

    def get_categories(self, user_id: str):
        docs = self.col.find({"user_id": user_id}).sort("name", 1)
        out = []
        for d in docs:
            out.append({
                "category_id": str(d["_id"]),
                "name": d["name"],
                "created_at": d["created_at"],
                "updated_at": d["updated_at"],
            })
        return out

    def update_category(self, user_id: str, category_id: str, payload: CategoryRequest):
        name = payload.name.strip()
        if name == "":
            raise ValueError("Category name can not be empty")

        dup = self.col.find_one({"user_id": user_id, "name": name})
        if dup and str(dup["_id"]) != category_id:
            raise ValueError("Category with this name already exists")

        res = self.col.update_one(
            {"_id": ObjectId(category_id), "user_id": user_id},
            {"$set": {"name": name, "updated_at": datetime.now()}}
        )
        if res.matched_count == 0:
            raise ValueError("Category not found")

        return {"message": "Category updated successfully"}

    def delete_category(self, user_id: str, category_id: str):
        res = self.col.delete_one({"_id": ObjectId(category_id), "user_id": user_id})
        if res.deleted_count == 0:
            raise ValueError("Category not found")
        return {"message": "Category deleted successfully"}
