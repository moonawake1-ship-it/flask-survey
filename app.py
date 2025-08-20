# app.py
from flask import Flask, render_template, request, redirect, url_for, abort
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Date, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from pathlib import Path
import os

# === Flask 基本設定（指定模板資料夾） ===
app = Flask(__name__, template_folder="templates")

# 允許的表單模板檔名（會依序嘗試，找到第一個就用）
TEMPLATE_CANDIDATES = ["form.html", "from.html", "4.html", "表單.html", "index.html"]

def pick_template():
    """回傳第一個存在的模板檔名，並列印偵錯資訊；若找不到就拋錯。"""
    tpl_dir = Path(app.template_folder).resolve()
    # 列印偵錯資訊（在終端機看得到）
    print("=== DEBUG ===")
    print("CWD:               ", os.getcwd())
    print("Template folder:   ", tpl_dir)
    if tpl_dir.exists():
        print("Folder listing:    ", [p.name for p in tpl_dir.iterdir() if p.is_file()])
    else:
        print("Folder listing:    <templates 資料夾不存在>")
    for name in TEMPLATE_CANDIDATES:
        if (tpl_dir / name).exists():
            print("Using template --->", name)
            return name
    existing = []
    if tpl_dir.exists():
        existing = [p.name for p in tpl_dir.glob("*") if p.is_file()]
    abort(500, f"找不到可用模板。請在 templates/ 放入以下任一檔案：{TEMPLATE_CANDIDATES}\n目前檔案：{existing}")

# === SQLite + SQLAlchemy ===
engine = create_engine("sqlite:///survey.db", echo=False, future=True)
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

class Submission(Base):
    __tablename__ = "submissions"
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    email = Column(String(200))
    tel = Column(String(50))
    birth = Column(Date)
    gender = Column(String(20))
    hobbies = Column(String(300))   # 多選以逗號儲存
    city = Column(String(50))
    english_score = Column(String(10))
    source = Column(String(50))
    feedback = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(engine)

# 後台密鑰（可用 .env 設定 ADMIN_KEY 覆蓋）
ADMIN_KEY = os.getenv("ADMIN_KEY", "changeme")

# === 路由 ===
@app.get("/")
def index():
    tpl = pick_template()
    return render_template(tpl)

@app.post("/submit")
def submit():
    # 拿取表單欄位（可缺省）
    name = request.form.get("name") or ""
    email = request.form.get("email") or ""
    tel = request.form.get("tel") or ""
    birth_raw = request.form.get("birth") or ""
    gender = request.form.get("gender") or ""
    hobbies = ",".join(request.form.getlist("hobby"))  # 複選
    city = request.form.get("city") or ""
    english_score = request.form.get("english_score") or ""
    source = request.form.get("source") or ""
    feedback = request.form.get("feedback") or ""

    # 轉日期
    birth = None
    if birth_raw:
        try:
            birth = datetime.strptime(birth_raw, "%Y-%m-%d").date()
        except ValueError:
            birth = None

    # 寫入 DB
    db = SessionLocal()
    db.add(Submission(
        name=name, email=email, tel=tel, birth=birth, gender=gender,
        hobbies=hobbies, city=city, english_score=english_score,
        source=source, feedback=feedback
    ))
    db.commit()
    db.close()

    return redirect(url_for("thanks"))

@app.get("/thanks")
def thanks():
    # 不依賴模板，直接回傳簡單頁面
    return (
        "<!doctype html><meta charset='utf-8'>"
        "<h2>送出成功！</h2>"
        "<p><a href='/'>回到表單</a>｜"
        "<a href='/admin?key=changeme'>到後台（示範密鑰）</a></p>"
    )

@app.get("/admin")
def admin():
    # 後台簡單保護：?key=你的密鑰
    key = request.args.get("key", "")
    if key != ADMIN_KEY:
        return abort(403, "Forbidden: wrong key")

    # 讀取資料
    db = SessionLocal()
    rows = db.query(Submission).order_by(Submission.created_at.desc()).all()
    db.close()

    # 如果你自己提供了 templates/admin.html，我們就用模板渲染
    admin_template_path = Path(app.template_folder or "templates") / "admin.html"
    if admin_template_path.exists():
        return render_template("admin.html", rows=rows)

    # 否則回傳一個內建的簡易表格（免模板也能看）
    def safe(v):
        return "" if v is None else str(v)
    html_rows = "".join(
        f"<tr>"
        f"<td>{r.id}</td>"
        f"<td>{safe(r.created_at)}</td>"
        f"<td>{safe(r.name)}</td>"
        f"<td>{safe(r.email)}</td>"
        f"<td>{safe(r.tel)}</td>"
        f"<td>{safe(r.birth)}</td>"
        f"<td>{safe(r.gender)}</td>"
        f"<td>{safe(r.hobbies)}</td>"
        f"<td>{safe(r.city)}</td>"
        f"<td>{safe(r.english_score)}</td>"
        f"<td>{safe(r.source)}</td>"
        f"<td>{safe(r.feedback)}</td>"
        f"</tr>"
        for r in rows
    )
    return (
        "<!doctype html><meta charset='utf-8'>"
        "<title>後台列表</title>"
        "<style>"
        "body{font-family:system-ui,'Microsoft JhengHei',Arial;padding:20px}"
        "table{border-collapse:collapse;width:100%}"
        "th,td{border:1px solid #ddd;padding:8px;vertical-align:top}"
        "th{background:#f3f4f6;text-align:left}"
        "small{color:#6b7280}"
        "</style>"
        "<h1>問卷回覆（最新在上）</h1>"
        f"<p><small>🔒 以密鑰進入：?key={ADMIN_KEY}</small></p>"
        "<table>"
        "<thead><tr>"
        "<th>ID</th><th>時間</th><th>姓名</th><th>Email</th><th>電話</th>"
        "<th>生日</th><th>性別</th><th>興趣</th><th>城市</th>"
        "<th>英文分數</th><th>來源</th><th>意見</th>"
        "</tr></thead>"
        f"<tbody>{html_rows or '<tr><td colspan=12>尚無資料</td></tr>'}</tbody>"
        "</table>"
    )

if __name__ == "__main__":
    # debug=True 存檔自動重啟；需要改埠口可加 port=5001
    app.run(debug=True)