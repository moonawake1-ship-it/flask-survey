from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
import sqlite3, os

app = Flask(__name__)
app.secret_key = "secret123"
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# 建立資料庫
def init_db():
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            q1 INTEGER,
            q2 TEXT,
            q3 TEXT,
            q4 TEXT,
            image TEXT
        )
    """)
    conn.commit()
    conn.close()
init_db()

# 前台表單
@app.route("/", methods=["GET", "POST"])
def form():
    if request.method == "POST":
        q1 = int(request.form["q1"])
        q2 = request.form["q2"]
        q3 = request.form["q3"]
        q4 = request.form["q4"]
        img = None

        # 驗證：q1 只能是 4 或 5
        if q1 not in [4, 5]:
            flash("只能選 4 或 5！")
            return redirect(url_for("form"))

        # 圖片上傳
        if "image" in request.files:
            file = request.files["image"]
            if file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                img = filename

        conn = sqlite3.connect("data.db")
        c = conn.cursor()
        c.execute("INSERT INTO responses (q1, q2, q3, q4, image) VALUES (?,?,?,?,?)",
                  (q1, q2, q3, q4, img))
        conn.commit()
        conn.close()
        return redirect(url_for("success"))
    return render_template("form.html")

@app.route("/success")
def success():
    return render_template("success.html")

# 後台登入
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == "admin" and request.form["password"] == "1234":
            session["admin"] = True
            return redirect(url_for("admin"))
        else:
            flash("帳號或密碼錯誤")
    return render_template("login.html")

# 後台管理
@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect(url_for("login"))
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("SELECT * FROM responses")
    rows = c.fetchall()
    conn.close()
    return render_template("admin.html", rows=rows)

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)