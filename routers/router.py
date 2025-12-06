from fastapi import APIRouter, Path, status, HTTPException, Query, Body, Depends
from models.category_model import CategoryRequest
from models.budget_model import BudgetRequest
from services.category_service import CategoryService
from services.budget_service import BudgetService
from routers.auth_dependency import verify_jwt_token

router = APIRouter(prefix="/{user_id}", tags=["category-budget"])

category_service = CategoryService()
budget_service = BudgetService()

@router.post("/categories/create", status_code=status.HTTP_201_CREATED)
async def create_category(
    user_id: str = Path(...), 
    payload: CategoryRequest = Body(...),
    current_user: dict = Depends(verify_jwt_token)
):
    if current_user["user_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    try:
        category_id = category_service.create_category(user_id, payload)
        return {"message": "Category created successfully", "category_id": category_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/categories", status_code=status.HTTP_200_OK)
async def get_categories(
    user_id: str = Path(...),
    current_user: dict = Depends(verify_jwt_token)
):
    if current_user["user_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return category_service.get_categories(user_id)

@router.put("/categories/{category_id}/update", status_code=status.HTTP_200_OK)
async def update_category(
    user_id: str = Path(...), 
    category_id: str = Path(...), 
    payload: CategoryRequest = Body(...),
    current_user: dict = Depends(verify_jwt_token)
):
    if current_user["user_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    try:
        return category_service.update_category(user_id, category_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/categories/{category_id}/delete", status_code=status.HTTP_200_OK)
async def delete_category(
    user_id: str = Path(...), 
    category_id: str = Path(...),
    current_user: dict = Depends(verify_jwt_token)
):
    if current_user["user_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    try:
        return category_service.delete_category(user_id, category_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/budgets/upsert", status_code=status.HTTP_200_OK)
async def upsert_budget(
    user_id: str = Path(...), 
    payload: BudgetRequest = Body(...),
    current_user: dict = Depends(verify_jwt_token)
):
    if current_user["user_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    try:
        return budget_service.upsert_budget(user_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/budgets", status_code=status.HTTP_200_OK)
async def get_budgets(
    user_id: str = Path(...), 
    month: str | None = Query(None),
    current_user: dict = Depends(verify_jwt_token)
):
    if current_user["user_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    try:
        return budget_service.get_budgets(user_id, month)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/budgets/{budget_id}/delete", status_code=status.HTTP_200_OK)
async def delete_budget(
    user_id: str = Path(...), 
    budget_id: str = Path(...),
    current_user: dict = Depends(verify_jwt_token)
):
    if current_user["user_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    try:
        return budget_service.delete_budget(user_id, budget_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.put("/budgets/{budget_id}/update", status_code=status.HTTP_200_OK)
async def update_budget(
    user_id: str = Path(...),
    budget_id: str = Path(...),
    payload: BudgetRequest = Body(...),
    current_user: dict = Depends(verify_jwt_token)
):
    if current_user["user_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    try:
        return budget_service.update_budget(user_id, budget_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))