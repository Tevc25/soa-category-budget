import logging
import os
from datetime import datetime
from urllib.parse import urlparse
from bson import ObjectId
import requests
from db.database import get_db
from models.category_model import CategoryRequest
from logging_utils import get_correlation_id

class CategoryService:
    def __init__(self):
        self.logger = logging.getLogger("soa-category-budget")
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
                self.logger.info(
                    "Fetching expenses",
                    extra={
                        "correlation_id": get_correlation_id(),
                        "url": target,
                        "method": "GET",
                    },
                )
                resp = requests.get(target, timeout=5)
                resp.raise_for_status()
                payload = resp.json()
                self.logger.info(
                    "Fetched expenses successfully",
                    extra={
                        "correlation_id": get_correlation_id(),
                        "url": target,
                        "method": "GET",
                        "status_code": resp.status_code,
                    },
                )
                return payload
            except requests.RequestException as exc:
                self.logger.warning(
                    "Failed to fetch expenses: %s", exc,
                    extra={
                        "correlation_id": get_correlation_id(),
                        "url": target,
                        "method": "GET",
                    },
                )
                continue
        self.logger.error(
            "All expense fetch attempts failed",
            extra={"correlation_id": get_correlation_id()},
        )
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
        self.logger.info(
            "Fetched expenses for category creation",
            extra={
                "correlation_id": get_correlation_id(),
                "path": f"/{user_id}/categories/create",
                "detail": f"count={len(expenses)}",
            },
        )
        if not expenses:
            self.logger.warning(
                "No expenses found for user, category will store empty items",
                extra={
                    "correlation_id": get_correlation_id(),
                    "path": f"/{user_id}/categories/create",
                    "detail": "empty-expense-list",
                },
            )

        now = datetime.now()

        for exp in expenses:
            desc = exp.get("description", "").strip()
            if desc == "":
                continue

            raw_items = exp.get("items", []) or []
            raw_items = self._ensure_item_dates(raw_items)

            if desc == name:
                items = raw_items
                self.logger.info(
                    "Matched requested category with expenses",
                    extra={
                        "correlation_id": get_correlation_id(),
                        "path": f"/{user_id}/categories/create",
                        "detail": f"name={name}, items={len(items)}",
                    },
                )
            else:
                if desc in seen_extra_names:
                    continue
                seen_extra_names.add(desc)
                exists_extra = self.col.find_one({"user_id": user_id, "name": desc})
                if not exists_extra:
                    self.logger.info(
                        "Auto creating extra category from expense description",
                        extra={
                            "correlation_id": get_correlation_id(),
                            "path": f"/{user_id}/categories/create",
                            "detail": f"name={desc}, items={len(raw_items)}",
                        },
                    )
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
        self.logger.info(
            "Category created",
            extra={
                "correlation_id": get_correlation_id(),
                "path": f"/{user_id}/categories/create",
                "detail": f"category_id={str(res.inserted_id)}",
            },
        )
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
            self.logger.warning(
                "No expenses available when listing categories",
                extra={
                    "correlation_id": get_correlation_id(),
                    "path": f"/{user_id}/categories",
                },
            )

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
        self.logger.info(
            "Category updated",
            extra={
                "correlation_id": get_correlation_id(),
                "path": f"/{user_id}/categories/{category_id}/update",
                "detail": f"name={updated['name']}",
            },
        )
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
        self.logger.info(
            "Category deleted",
            extra={
                "correlation_id": get_correlation_id(),
                "path": f"/{user_id}/categories/{category_id}/delete",
                "detail": f"deleted_id={category_id}",
            },
        )
        return {"message": "Category deleted successfully"}
