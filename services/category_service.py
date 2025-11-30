import os
from datetime import datetime
from urllib.parse import urlparse
from bson import ObjectId
import requests
from db.database import get_db
from models.category_model import CategoryRequest

class CategoryService:
    def __init__(self):
        self.db = get_db()
        self.col = self.db["category_data"]
        base = os.getenv("EXPENSE_SERVICE_URL", "http://soa-expense:8000").rstrip("/")
        parsed = urlparse(base)
        if parsed.port is None:
            base = f"{base}:8000"
        self.expense_service_url = base
        self.expense_service_url_fallback = "http://localhost:8000"
        self.expense_service_internal = "http://soa-expense:8000"
        
    def _ensure_item_dates(self, raw_items: list[dict]) -> list[dict]:
        now_iso = datetime.now().isoformat()
        out = []
        for it in raw_items or []:
            if isinstance(it, dict) and "created_at" not in it:
                it = {**it, "created_at": now_iso}
            out.append(it)
        return out

    def _fetch_expenses(self, user_id: str) -> list[dict]:
        urls: list[str] = []
        for candidate in [
            self.expense_service_url,
            self.expense_service_internal,
            self.expense_service_url_fallback
        ]:
            if candidate not in urls:
                urls.append(candidate)

        for base in urls:
            try:
                target = f"{base}/{user_id}/expenses"
                print(f"[CategoryService] fetching expenses from {target}")
                resp = requests.get(target, timeout=5)
                resp.raise_for_status()
                payload = resp.json()
                print(f"[CategoryService] success {target} -> {len(payload)} expenses")
                return payload
            except requests.RequestException as exc:
                print(f"[CategoryService] failed fetch {base}: {exc}")
                continue
        print("[CategoryService] all expense fetch attempts failed")
        return []

    def create_category(self, user_id: str, payload: CategoryRequest) -> str:
        name = payload.name.strip()
        if name == "":
            raise ValueError("Category name can not be empty")

        exists = self.col.find_one({"user_id": user_id, "name": name})
        if exists:
            raise ValueError("Category with this name already exists")

        items: list[dict] = []
        extra_categories: list[dict] = []
        seen_extra_names: set[str] = set()
        expenses = self._fetch_expenses(user_id)
        print(f"[CategoryService] fetched expenses for user {user_id}: base_url={self.expense_service_url}, count={len(expenses)}")
        if not expenses:
            print(f"[CategoryService] no expenses found for user {user_id}, category will store empty items")

        now = datetime.now()

        for exp in expenses:
            desc = exp.get("description", "").strip()
            if desc == "":
                continue

            raw_items = exp.get("items", []) or []
            raw_items = self._ensure_item_dates(raw_items)

            if desc == name:
                items = raw_items
                print(f"[CategoryService] matched requested category '{name}' with expense items count={len(items)}")
            else:
                if desc in seen_extra_names:
                    continue
                seen_extra_names.add(desc)
                exists_extra = self.col.find_one({"user_id": user_id, "name": desc})
                if not exists_extra:
                    print(f"[CategoryService] auto-creating category '{desc}' with items count={len(raw_items)}")
                    extra_categories.append({
                        "user_id": user_id,
                        "name": desc,
                        "items": raw_items,
                        "created_at": now,
                        "updated_at": now
                    })

        doc = {
            "user_id": user_id,
            "name": name,
            "items": items,
            "created_at": now,
            "updated_at": now
        }
        res = self.col.insert_one(doc)
        if extra_categories:
            self.col.insert_many(extra_categories)
        return {
            "message": "Category created successfully",
            "category_id": str(res.inserted_id),
            "name": name,
            "items": items
        }

    def get_categories(self, user_id: str):
        expense_items_by_desc: dict[str, list[dict]] = {}
        expenses = self._fetch_expenses(user_id)
        for exp in expenses:
            desc = exp.get("description", "").strip()
            if desc:
                current = expense_items_by_desc.get(desc, [])
                raw_items = exp.get("items", []) or []
                raw_items = self._ensure_item_dates(raw_items)
                expense_items_by_desc[desc] = current + raw_items
        if not expenses:
            print(f"[CategoryService] no expenses available when listing categories for user {user_id}")

        docs = self.col.find({"user_id": user_id}).sort("name", 1)
        out = []
        for d in docs:
            items = d.get("items", [])
            if (not items) and d.get("name") in expense_items_by_desc:
                items = expense_items_by_desc[d["name"]]
                self.col.update_one(
                    {"_id": d["_id"]},
                    {"$set": {"items": items, "updated_at": datetime.now()}}
                )
            out.append({
                "category_id": str(d["_id"]),
                "name": d["name"],
                "items": items,
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

        updated = self.col.find_one({"_id": ObjectId(category_id), "user_id": user_id})
        return {
            "message": "Category updated successfully",
            "category_id": category_id,
            "name": updated["name"],
            "items": updated.get("items", []),
            "updated_at": updated["updated_at"],
        }

    def delete_category(self, user_id: str, category_id: str):
        res = self.col.delete_one({"_id": ObjectId(category_id), "user_id": user_id})
        if res.deleted_count == 0:
            raise ValueError("Category not found")
        return {"message": "Category deleted successfully"}
