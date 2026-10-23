# Cấu trúc dự án (Clean Architecture, chia theo module)

Code mới phải theo cấu trúc dưới đây. Thêm/bớt thư mục cấp cao hoặc đổi cách tổ chức → hỏi trước.

> Code mới nằm ở **`server/`**. Không dùng tên `backend/`: Windows không phân biệt hoa/thường nên `backend/` chính là thư mục `Backend/` cũ.

```
server/
├── app/
│   ├── main.py                 # tạo FastAPI app, gắn router, middleware
│   ├── container.py            # lắp ghép dependency (DI)
│   ├── core/                   # dùng chung, KHÔNG chứa nghiệp vụ
│   │   ├── config.py           # Settings (pydantic-settings)
│   │   ├── errors.py           # lớp lỗi gốc + mã lỗi
│   │   ├── security.py         # băm mật khẩu, JWT
│   │   ├── db.py               # engine, session, Unit of Work
│   │   └── logging.py
│   └── modules/
│       ├── auth/               # M01
│       ├── settings/           # M02
│       ├── library/            # M03
│       ├── imaging/            # M04 (phía API: tạo job, đọc kết quả)
│       ├── reader/             # M05
│       ├── dictionary/         # M06
│       ├── vocab/              # M07
│       ├── review/             # M08
│       ├── quiz/               # M09
│       ├── suggestions/        # M10
│       ├── tts/                # M11
│       ├── stats/              # M12
│       ├── admin/              # M13
│       ├── notifications/      # M14
│       └── jobs/               # M15
│           (mỗi module có cùng cấu trúc:)
│           ├── domain/         # entities.py, value_objects.py, services.py, errors.py
│           ├── application/    # use_cases/<ten_use_case>.py, ports.py, dto.py, public.py
│           ├── infrastructure/ # orm_models.py, repositories.py, adapters (tts, llm, storage...)
│           └── api/            # router.py, schemas.py, dependencies.py
├── worker/                     # process riêng: pipeline ảnh + scheduler
├── migrations/                 # Alembic
├── tests/
│   ├── unit/                   # domain + use case (dùng fake repository)
│   ├── integration/            # repository với PostgreSQL thật
│   └── api/                    # gọi API bằng httpx
├── pyproject.toml / requirements.txt
└── .env.example
frontend/                       # HTML/CSS/JS
module xử lí ảnh/               # mã pipeline hiện có — worker gọi qua adapter, không sửa trực tiếp khi chưa hỏi
docs/                           # user story, module–chức năng, thiết kế
```

## Quy tắc
- Mỗi use case = 1 file trong `application/use_cases/`, tên theo động từ (`save_word.py`, `grade_card.py`), docstring ghi mã chức năng (`F07.01`) và user story.
- `orm_models.py` chỉ ở infrastructure; domain entity **không** phải ORM model. Repository chuyển đổi qua lại.
- `schemas.py` (Pydantic) chỉ ở tầng api; không trả ORM model hoặc entity trực tiếp ra API.
- Không tạo thư mục `utils/` hay `helpers/` chung chung; đặt code vào module sở hữu nó, phần thật sự dùng chung thì vào `core/`.
- Thư mục `Backend/` cũ (routers/services) **không** theo cấu trúc này: chỉ dùng để tham khảo, **không sửa, không mở rộng**. Khi tạo file mới, kiểm tra đường dẫn không trùng (kể cả khác hoa/thường) với file sẵn có.
