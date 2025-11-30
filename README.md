# soa-category-budget

Storitev za kategorije in budgete, ki bere MongoDB in se povezuje na `soa-expense` za sinhronizacijo itemov iz expense zapisov.

## Namestitev in zagon

### Docker
```bash
# v mapi soa-expenseTracker
docker compose build soa-category-budget
docker compose up -d soa-category-budget
# lokalni port: 8002 -> container port: 8001
```

### Okoljske spremenljivke (`.env`)
- `MONGODB_URI` – povezava na MongoDB.
- `MONGODB_DB` – ime baze (npr. `category_db`).
- `EXPENSE_SERVICE_URL` – URL do expense servisa; v docker mreži naj bo `http://soa-expense:8000`, lokalno lahko `http://localhost:8000`.

## Struktura podatkov

### Category (Mongo dokument)
```json
{
  "_id": "<ObjectId>",
  "user_id": "<user-id>",
  "name": "Nakup hrane",
  "items": [
    {
      "item_id": "uuid",
      "item_name": "Kruh",
      "item_price": 2.5,
      "item_quantity": 1
    }
  ],
  "created_at": "2025-11-30T15:53:16.137000",
  "updated_at": "2025-11-30T15:53:16.137000"
}
```

### Budget (Mongo dokument)
```json
{
  "_id": "<ObjectId>",
  "user_id": "<user-id>",
  "month": "2024-05",
  "category_id": "<category ObjectId>",
  "limit": 100.0,
  "created_at": "2025-11-30T15:53:16.137000",
  "updated_at": "2025-11-30T15:53:16.137000"
}
```

## API (base: `http://localhost:8002`)

### Kategorije
- **POST** `/{user_id}/categories/create`  
  Body: `{ "name": "Nakup hrane" }`  
  Če obstaja expense z enakim `description`, se itemi pripnejo. Auto-ustvari tudi manjkajoče kategorije za druge expense opise.

- **GET** `/{user_id}/categories`  
  Vrne seznam kategorij z `items`.

- **PUT** `/{user_id}/categories/{category_id}/update`  
  Body: `{ "name": "Novo ime" }`  
  Preimenuje kategorijo.

- **DELETE** `/{user_id}/categories/{category_id}/delete`  
  Izbriše kategorijo.

### Budgeti
- **POST** `/{user_id}/budgets/upsert`  
  Body: `{ "month": "YYYY-MM", "category_id": "<id>", "limit": 100 }`  
  Ustvari ali posodobi budget za mesec/kategorijo.

- **GET** `/{user_id}/budgets?month=YYYY-MM`  
  Seznam budgetov, opcijsko filtriran po mesecu.

- **PUT** `/{user_id}/budgets/{budget_id}/update`  
  Body: `{ "month": "YYYY-MM", "category_id": "<id>", "limit": 100 }`  
  Posodobitev obstoječega budgeta.

- **DELETE** `/{user_id}/budgets/{budget_id}/delete`  
  Izbriše budget.

## Opombe
- Datumi se vračajo v obliki ISO stringov ali formatiranih datumov (glej Pydantic serializerje).
- Servis pričakuje, da expense servis deluje in je dostopen na `EXPENSE_SERVICE_URL`; v nasprotnem primeru se kategorija ustvari brez itemov.
