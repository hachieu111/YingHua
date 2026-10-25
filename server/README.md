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

## Tạo Quản trị viên đầu tiên

Đăng ký công khai luôn tạo Người học (F01.01). Quản trị viên đầu tiên do người vận hành tạo:

```bash
python scripts/create_admin.py admin@example.com   # nhập mật khẩu khi được hỏi, hoặc đặt ADMIN_PASSWORD
```

Sau đó Quản trị viên này nâng quyền cho người khác trong giao diện quản trị.

## Chạy

```bash
python -m uvicorn app.main:create_app --factory --reload --port 8000
```

Trên Windows, `--reload` không đáng tin: reloader thấy thay đổi nhưng tiến trình cũ không tắt nên code mới không lên, và có thể để lại tiến trình con mồ côi giữ cổng 8000. Khi phát triển trên Windows, chạy không reload và khởi động lại sau mỗi đợt sửa:

```bash
python -m uvicorn app.main:create_app --factory --port 8000
```

Worker xử lý ảnh (process riêng; cài thêm `requirements-worker.txt`):

```bash
PIPELINE_ENABLED=true python -m worker.main
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
