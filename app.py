import sqlite3
import datetime
from flask import Flask, render_template, request, redirect, session

app = Flask(__name__)
app.secret_key = "manitej_exam_secure"

DATABASE = "database.db"


# ======================================
# DATABASE CONNECTION HELPER
# ======================================
def get_db():
    return sqlite3.connect(DATABASE)


# ======================================
# DATABASE INITIALIZATION
# ======================================
def init_db():
    conn = get_db()
    c = conn.cursor()

    # Admin Table
    c.execute("""
    CREATE TABLE IF NOT EXISTS admin(
        username TEXT PRIMARY KEY,
        password TEXT
    )
    """)

    # Questions Table
    c.execute("""
    CREATE TABLE IF NOT EXISTS questions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT,
        option1 TEXT,
        option2 TEXT,
        option3 TEXT,
        option4 TEXT,
        correct_option INTEGER,
        marks INTEGER
    )
    """)

    # Results Table
    c.execute("""
    CREATE TABLE IF NOT EXISTS results(
        student TEXT,
        score INTEGER,
        total INTEGER,
        date TEXT
    )
    """)

    # Attempt Log Table
    c.execute("""
    CREATE TABLE IF NOT EXISTS attempts(
        student TEXT,
        action TEXT,
        time TEXT
    )
    """)

    # Default Admin
    c.execute("INSERT OR IGNORE INTO admin VALUES ('admin','admin123')")

    conn.commit()
    conn.close()


init_db()


# ======================================
# HOME LOGIN
# ======================================
@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        student = request.form.get("student")

        if not student:
            return redirect("/")

        session["student"] = student

        log_attempt(student, "Started Exam")

        return redirect("/exam")

    return render_template("login.html")


# ======================================
# EXAM PAGE
# ======================================
@app.route("/exam")
def exam():

    if "student" not in session:
        return redirect("/")

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT * FROM questions")
    questions = c.fetchall()

    conn.close()

    return render_template("exam.html", questions=questions)


# ======================================
# SUBMIT RESULT
# ======================================
@app.route("/result", methods=["POST"])
def result():

    if "student" not in session:
        return redirect("/")

    student = session["student"]

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT id, correct_option, marks FROM questions")
    questions = c.fetchall()

    score = 0
    total = 0

    for q in questions:
        qid, correct, marks = q
        total += marks

        answer = request.form.get(f"q{qid}")

        if answer and int(answer) == correct:
            score += marks

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    c.execute("INSERT INTO results VALUES (?,?,?,?)",
              (student, score, total, now))

    conn.commit()
    conn.close()

    log_attempt(student, "Submitted Exam")

    return render_template("result.html", score=score, total=total)


# ======================================
# ADMIN LOGIN
# ======================================
@app.route("/admin", methods=["GET", "POST"])
def admin():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        conn = get_db()
        c = conn.cursor()

        c.execute("SELECT * FROM admin WHERE username=? AND password=?",
                  (username, password))

        admin_user = c.fetchone()
        conn.close()

        if admin_user:
            session["admin"] = username
            return redirect("/admin-dashboard")

        return "Invalid Login"

    return render_template("admin_login.html")


# ======================================
# ADMIN DASHBOARD
# ======================================
@app.route("/admin-dashboard")
def dashboard():

    if "admin" not in session:
        return redirect("/admin")

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT * FROM questions")
    questions = c.fetchall()

    c.execute("SELECT * FROM results")
    results = c.fetchall()

    # Analytics
    c.execute("SELECT COUNT(*) FROM results")
    total_students = c.fetchone()[0] or 0

    c.execute("SELECT MAX(score) FROM results")
    highest = c.fetchone()[0] or 0

    c.execute("SELECT AVG(score) FROM results")
    average = c.fetchone()[0]
    average = round(average, 2) if average else 0

    conn.close()

    return render_template("admin_dashboard.html",
                           questions=questions,
                           results=results,
                           total_students=total_students,
                           highest=highest,
                           average=average)


# ======================================
# ADD QUESTION
# ======================================
@app.route("/add-question", methods=["GET", "POST"])
def add_question():

    if "admin" not in session:
        return redirect("/admin")

    if request.method == "POST":

        data = (
            request.form["question"],
            request.form["o1"],
            request.form["o2"],
            request.form["o3"],
            request.form["o4"],
            int(request.form["correct"]),
            int(request.form["marks"])
        )

        conn = get_db()
        c = conn.cursor()

        c.execute("""
        INSERT INTO questions
        (question,option1,option2,option3,option4,correct_option,marks)
        VALUES (?,?,?,?,?,?,?)
        """, data)

        conn.commit()
        conn.close()

        return redirect("/admin-dashboard")

    return render_template("add_question.html")


# ======================================
# DELETE QUESTION
# ======================================
@app.route("/delete-question/<int:id>")
def delete_question(id):

    if "admin" not in session:
        return redirect("/admin")

    conn = get_db()
    c = conn.cursor()

    c.execute("DELETE FROM questions WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect("/admin-dashboard")


# ======================================
# LEADERBOARD
# ======================================
@app.route("/leaderboard")
def leaderboard():

    conn = get_db()
    c = conn.cursor()

    c.execute("""
    SELECT student, score, total
    FROM results
    ORDER BY score DESC
    """)

    leaders = c.fetchall()
    conn.close()

    return render_template("leaderboard.html", leaders=leaders)


# ======================================
# STUDENT HISTORY
# ======================================
@app.route("/history")
def history():

    if "student" not in session:
        return redirect("/")

    student = session["student"]

    conn = get_db()
    c = conn.cursor()

    c.execute("""
    SELECT score,total,date
    FROM results
    WHERE student=?
    """, (student,))

    history_data = c.fetchall()
    conn.close()

    return render_template("history.html", history=history_data)


# ======================================
# ATTEMPT LOG FUNCTION
# ======================================
def log_attempt(student, action):

    conn = get_db()
    c = conn.cursor()

    time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    c.execute("INSERT INTO attempts VALUES (?,?,?)",
              (student, action, time))

    conn.commit()
    conn.close()


# ======================================
# LOGOUT
# ======================================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ======================================
# RUN SERVER
# ======================================
if __name__ == "__main__":
    app.run(debug=True)
