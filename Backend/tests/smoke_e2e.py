"""Chạy thử toàn bộ luồng API trên server đang chạy (kể cả pipeline OCR/dịch thật).

  python tests/smoke_e2e.py [BASE_URL] [ẢNH_TRANG]
Mặc định: http://localhost:8001 và module xử lí ảnh/mudule xu ly anh/dataset/images/val/trang_001.jpg
Tạo tài khoản test ngẫu nhiên smoke-<random>@example.com.
"""

import secrets
import sys
import time
from pathlib import Path

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8001"
IMG = Path(sys.argv[2]) if len(sys.argv) > 2 else (
    Path(__file__).resolve().parents[2] / "module xử lí ảnh" / "mudule xu ly anh" / "dataset" / "images" / "val"
    / "trang_001.jpg")

c = httpx.Client(base_url=BASE, timeout=120)
ok_count = 0


def check(cond, msg):
    global ok_count
    if not cond:
        raise SystemExit(f"FAIL: {msg}")
    ok_count += 1
    print(f"  ok  {msg}")


def auth(tok):
    return {"Authorization": f"Bearer {tok}"}


print("== auth")
email = f"smoke-{secrets.token_hex(4)}@example.com"
r = c.post("/api/auth/register", json={"email": email, "password": "matkhau123", "display_name": "Smoke"})
check(r.status_code == 201, f"register {r.status_code}")
tok = r.json()
check(c.post("/api/auth/register", json={"email": email, "password": "matkhau123", "display_name": "x"}).status_code == 409,
      "register trùng email -> 409")
check(c.post("/api/auth/login", json={"email": email, "password": "sai"}).status_code == 401, "login sai mật khẩu -> 401")
r = c.post("/api/auth/login", json={"email": email, "password": "matkhau123"})
check(r.status_code == 200, "login")
access, refresh = r.json()["access_token"], r.json()["refresh_token"]
check(c.get("/api/auth/me").status_code == 401, "không token -> 401")
check(c.get("/api/auth/me", headers=auth(access)).json()["email"] == email, "me")
r = c.post("/api/auth/refresh", json={"refresh_token": refresh})
check(r.status_code == 200 and r.json()["refresh_token"] != refresh, "refresh xoay vòng")
new_refresh, access = r.json()["refresh_token"], r.json()["access_token"]
check(c.post("/api/auth/refresh", json={"refresh_token": refresh}).status_code == 401, "dùng lại refresh cũ -> 401")
check(c.post("/api/auth/refresh", json={"refresh_token": new_refresh}).status_code == 401,
      "sau khi phát hiện dùng lại, cả phiên bị thu hồi")
r = c.post("/api/auth/login", json={"email": email, "password": "matkhau123"})
access, refresh = r.json()["access_token"], r.json()["refresh_token"]
H = auth(access)
check(c.put("/api/me/settings", json={"hsk_level": 3, "default_mode": "learn"}, headers=H).json()["hsk_level"] == 3,
      "cập nhật settings")

print("== dictionary")
r = c.get("/api/dict/lookup", params={"term": "修炼"}, headers=H)
check(r.status_code == 200 and "xianxia" in r.json(), "lookup 修炼")
check(len(c.get("/api/dict/search", params={"q": "ai"}, headers=H).json()) > 0, "search pinyin")
h = c.get("/api/dict/hanzi/好", headers=H).json()
check(h["has_strokes"] and h["stroke_data"]["strokes"], "hanzi 好 có nét viết")
check(len(c.post("/api/dict/segment", json={"text": "我们今天修炼功法"}, headers=H).json()) >= 3, "segment")
check(len(c.get("/api/dict/xianxia/search", params={"q": "修", "kind": "phrase"}, headers=H).json()) > 0,
      "xianxia search")

print("== library + pipeline")
s = c.post("/api/series", json={"title_vi": "Truyện test", "public": False}, headers=H).json()
check(c.post("/api/series", json={"title_vi": "x", "public": True}, headers=H).status_code == 403,
      "user thường không tạo truyện public")
ch = c.post(f"/api/series/{s['id']}/chapters", json={"number": 1, "title": "Chương 1"}, headers=H).json()
r = c.post(f"/api/chapters/{ch['id']}/pages", files=[("files", (IMG.name, IMG.read_bytes(), "image/jpeg"))],
           headers=H)
check(r.status_code == 201, f"upload trang {r.status_code} {r.text[:200]}")
page_id = r.json()["pages"][0]["id"]
deadline = time.time() + 900
while True:
    p = c.get(f"/api/pages/{page_id}", headers=H).json()
    st = p["translation"]["status"]
    if st in ("done", "failed") or time.time() > deadline:
        break
    print(f"    ... {st}")
    time.sleep(5)
check(st == "done", f"pipeline xong (status={st}, error={(p['translation'] or {}).get('error')})")
check(len(p["bubbles"]) > 0, f"có {len(p['bubbles'])} bong bóng")
b = p["bubbles"][0]
check(b["lines"] and b["tokens"], "bubble có lines + tokens")
for v in ("original", "rendered", "inpainted"):
    r = c.get(f"/api/pages/{page_id}/image/{v}", headers=H)
    check(r.status_code == 200 and r.headers["content-type"].startswith("image/"), f"ảnh {v}")
r = c.get(f"/api/pages/{page_id}/image/rendered", params={"download": True}, headers=H)
check("attachment" in r.headers.get("content-disposition", ""), "tải xuống ảnh đã dịch")

# Upload lại đúng ảnh đó -> dùng chung bản dịch
r = c.post("/api/uploads/quick", files=[("files", (IMG.name, IMG.read_bytes(), "image/jpeg"))], headers=H).json()
check(r["reused"] == 1 and r["queued"] == 0, "ảnh trùng dùng lại bản dịch (không chạy pipeline)")

r = c.put(f"/api/bubbles/{b['id']}/edit", json={"text_vi": "Bản dịch của tôi"}, headers=H)
check(r.json()["edited"], "sửa bản dịch riêng")
check(c.get(f"/api/pages/{page_id}", headers=H).json()["bubbles"][0]["text_vi"] == "Bản dịch của tôi",
      "trang trả về bản đã sửa")
c.put(f"/api/chapters/{ch['id']}/progress", json={"last_page_no": 1, "mode": "learn"}, headers=H)
check(c.get("/api/me/progress", headers=H).json()[0]["chapter_id"] == ch["id"], "tiến độ đọc")

print("== vocab + review")
term = next((t["w"] for bb in p["bubbles"] for t in bb["tokens"] if len(t["w"]) >= 2), b["tokens"][0]["w"])
bid = next(bb["id"] for bb in p["bubbles"] if term in bb["text_zh"])
c.get("/api/dict/lookup", params={"term": term, "bubble_id": bid}, headers=H)
r = c.post("/api/vocab", json={"term": term, "bubble_id": bid}, headers=H)
check(r.status_code == 201 and r.json()["contexts"], f"lưu từ '{term}' kèm ngữ cảnh")
vocab = r.json()
check(vocab["contexts"][0]["snippet_url"], "có ảnh cắt bong bóng")
check(c.get(vocab["contexts"][0]["snippet_url"], headers=H).headers["content-type"] == "image/webp", "ảnh cắt webp")
check(len(vocab["flashcards"]) == 2, "tạo 2 flashcard")
due = c.get("/api/review/due", headers=H).json()
check(len(due["cards"]) == 2, "2 thẻ mới cần học")
card = due["cards"][0]
r = c.post(f"/api/review/{card['id']}", json={"rating": 3, "duration_ms": 3000}, headers=H).json()
check(r["state"] == "review" and r["interval_days"] == 1, "SM-2 Good lần đầu -> 1 ngày")
r = c.post(f"/api/review/{due['cards'][1]['id']}", json={"rating": 1}, headers=H).json()
check(r["state"] == "learning", "Again -> learning, 10 phút")
check(c.get("/api/me/stats", headers=H).json()["reviews"]["today"] == 2, "thống kê")
check(c.patch(f"/api/vocab/{vocab['id']}", json={"status": "known"}, headers=H).json()["flashcards"][0]["suspended"],
      "đánh dấu đã thuộc -> tạm ngưng thẻ")

print("== suggestions + tts")
sug = c.get(f"/api/chapters/{ch['id']}/suggestions", headers=H).json()
check(isinstance(sug, list), f"{len(sug)} gợi ý")
check(all(x["term"] != term for x in sug), "không gợi ý từ đã có trong sổ tay")
if sug:
    check(c.post(f"/api/suggestions/{sug[0]['id']}/accept", headers=H).status_code == 200, "nhận gợi ý")
r = c.get("/api/tts", params={"text": "你好"}, headers=H)
check(r.status_code in (200, 503), f"tts ({r.status_code})")
if r.status_code == 200:
    check(r.headers["content-type"] == "audio/mpeg" and len(r.content) > 1000, "mp3 hợp lệ")

print("== cleanup quyền")
check(c.get("/api/admin/stats", headers=H).status_code == 403, "user thường không vào admin")
check(c.post("/api/auth/logout", json={"refresh_token": refresh}, headers=H).status_code == 204, "logout")
check(c.post("/api/auth/refresh", json={"refresh_token": refresh}).status_code == 401, "refresh sau logout -> 401")
print(f"\nPASS {ok_count} kiểm tra")
