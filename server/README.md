# YingHua Server (FastAPI · Clean Architecture)

Kế hoạch: `../docs/ke-hoach-trien-khai.md` · Rules: `../.claude/rules/`

## Cài đặt (chạy trong thư mục `server/`)

```bash
python -m pip install -r requirements-dev.txt
cp .env.example .env                 # điền mật khẩu PostgreSQL, JWT_SECRET (≥ 32 ký tự)
python scripts/create_databases.py   # tạo yinghua_db và yinghua_test nếu chưa có
python -m alembic upgrade head
ALEMBIC_TARGET=test python -m alembic upgrade head
```

Trên Windows, đặt `PYTHONIOENCODING=utf-8` nếu console báo lỗi mã hóa khi in tiếng Việt.

## Chạy

```bash
python -m uvicorn app.main:create_app --factory --reload --port 8000
```

- Health: http://localhost:8000/api/v1/health
- Swagger: http://localhost:8000/api/v1/docs

## Kiểm tra trước khi báo xong

```bash
python -m ruff check . && python -m ruff format --check .
python -m mypy app
python -m pytest
```

## Migration

```bash
python -m alembic revision --autogenerate --rev-id 0002 -m "mo_ta_ngan"
```
