from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3
import datetime
import os
import io
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)
app.secret_key = "onlinequiz123"

# Create database table
def init_db():
    conn = sqlite3.connect("quiz.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fullname TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()

init_db()


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("quiz.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM students WHERE email=? AND password=?",
            (email, password)
        )

        user = cursor.fetchone()
        conn.close()

        if user:
            session["email"] = user[2]
            session["name"] = user[1]

            return redirect("/dashboard")
        else:
            return "Invalid Email or Password"

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        fullname = request.form["fullname"]
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("quiz.db")
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO students(fullname,email,password) VALUES(?,?,?)",
                (fullname, email, password)
            )
            conn.commit()
            conn.close()

            return redirect("/")

        except:
            conn.close()
            return "Email already exists!"

    return render_template("register.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/history")
def history():

    conn = sqlite3.connect("quiz.db")
    cur = conn.cursor()

    cur.execute("""
    SELECT
    email,
    subject,
    total,
    score,
    percentage,
    date
    FROM history
    ORDER BY id DESC
    """)

    history = cur.fetchall()

    conn.close()

    return render_template(
        "history.html",
        history=history
    )


@app.route("/select_questions")
def select_questions():
    subject = request.args.get("subject")
    return render_template(
        "select_questions.html",
        subject=subject
    )


@app.route("/subjects")
def subjects():
    return render_template("subjects.html")


@app.route("/quiz")
def quiz():
    subject = request.args.get("subject")
    count = int(request.args.get("count"))

    conn = sqlite3.connect("quiz.db")
    cur = conn.cursor()

    cur.execute("""
    SELECT question, option1, option2, option3, option4, answer
    FROM questions
    WHERE subject=?
    ORDER BY RANDOM()
    LIMIT ?
    """, (subject, count))

    questions = cur.fetchall()
    conn.close()

    return render_template(
        "quiz.html",
        questions=questions,
        subject=subject,
        total=count,
        timer=count * 2
    )


@app.route("/result", methods=["POST"])
def result():

    score = 0
    total = 0

    review = []

    for key in request.form:

        if key.startswith("answer"):

            total += 1

            number = key.replace("answer", "")

            correct = request.form[key]

            selected = request.form.get("q" + number)

            question = request.form.get("question" + number)

            is_correct = (selected == correct)

            if is_correct:
                score += 1

            review.append({
                "question": question,
                "selected": selected if selected else "Not Answered",
                "correct": correct,
                "status": is_correct
            })

    wrong = total - score

    percentage = round((score / total) * 100, 2) if total > 0 else 0

    status = "PASS" if percentage >= 40 else "FAIL"
    
    subject = request.form.get("subject")
    
    # Store the latest result in the session
    session["last_subject"] = subject
    session["last_score"] = score
    session["last_total"] = total
    session["last_percentage"] = percentage

    from datetime import datetime

    conn = sqlite3.connect("quiz.db")
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO history
    (student_email, subject, score, total, percentage, quiz_date)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        session.get("email"),
        subject,
        score,
        total,
        percentage,
        datetime.now().strftime("%d-%m-%Y %H:%M")
    ))

    history_id = cur.lastrowid

    for item in review:
        cur.execute("""
        INSERT INTO history_details
        (history_id, question, selected_answer, correct_answer, status)
        VALUES (?, ?, ?, ?, ?)
        """, (
            history_id,
            item["question"],
            item["selected"],
            item["correct"],
            "Correct" if item["status"] else "Wrong"
        ))

    conn.commit()
    conn.close()

    # Store certificate details before rendering template
    session["certificate_name"] = session.get("name")
    session["certificate_subject"] = request.form.get("subject")
    session["certificate_score"] = score
    session["certificate_total"] = total
    session["certificate_percentage"] = percentage
    session["certificate_date"] = datetime.now().strftime("%d-%m-%Y")

    return render_template(
        "result.html",
        score=score,
        total=total,
        wrong=wrong,
        percentage=percentage,
        status=status,
        review=review
    )


@app.route("/admin_login", methods=["GET","POST"])
def admin_login():

    if request.method=="POST":

        username=request.form["username"]

        password=request.form["password"]

        if username=="Abhijit Sahoo" and password=="Abhijit@2026":

            session["admin"]=True

            return redirect("/admin_dashboard")

        else:

            return "Invalid Admin Login"

    return render_template("admin_login.html")


@app.route("/admin_dashboard")
def admin_dashboard():

    if not session.get("admin"):
        return redirect("/admin_login")

    conn=sqlite3.connect("quiz.db")
    cur=conn.cursor()

    cur.execute("SELECT COUNT(*) FROM students")
    students=cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM questions")
    questions=cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM history")
    quizzes=cur.fetchone()[0]

    conn.close()

    return render_template(
        "admin_dashboard.html",
        students=students,
        questions=questions,
        quizzes=quizzes
    )


def create_question_table():
    conn = sqlite3.connect("quiz.db")
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS questions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject TEXT,
        question TEXT,
        option1 TEXT,
        option2 TEXT,
        option3 TEXT,
        option4 TEXT,
        answer TEXT
    )
    """)

    conn.commit()
    conn.close()


def create_history_table():
    conn = sqlite3.connect("quiz.db")
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_email TEXT,
        subject TEXT,
        score INTEGER,
        total INTEGER,
        percentage REAL,
        quiz_date TEXT
    )
    """)

    conn.commit()
    conn.close()


def create_history_details_table():
    conn = sqlite3.connect("quiz.db")
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS history_details(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        history_id INTEGER,
        question TEXT,
        selected_answer TEXT,
        correct_answer TEXT,
        status TEXT
    )
    """)

    conn.commit()
    conn.close()


@app.route("/add_question", methods=["GET", "POST"])
def add_question():

    if request.method == "POST":

        subject = request.form["subject"]
        question = request.form["question"]
        option1 = request.form["option1"]
        option2 = request.form["option2"]
        option3 = request.form["option3"]
        option4 = request.form["option4"]
        answer = request.form["answer"]

        conn = sqlite3.connect("quiz.db")
        cur = conn.cursor()

        cur.execute("""
        INSERT INTO questions
        (subject, question, option1, option2, option3, option4, answer)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            subject,
            question,
            option1,
            option2,
            option3,
            option4,
            answer
        ))

        conn.commit()
        conn.close()

        return redirect("/admin_dashboard")

    return render_template("add_question.html")


@app.route("/view_students")
def view_students():

    conn = sqlite3.connect("quiz.db")
    cur = conn.cursor()

    cur.execute("SELECT fullname, email FROM students")

    students = cur.fetchall()

    conn.close()

    return render_template(
        "view_students.html",
        students=students
    )


# --- REPLACED EDIT QUESTION ROUTE WITH SEARCH & PAGINATION ---
@app.route("/edit_question")
def edit_question():
    
    search = request.args.get("search", "")
    page = int(request.args.get("page", 1))
    per_page = 10
    offset = (page - 1) * per_page

    conn = sqlite3.connect("quiz.db")
    cur = conn.cursor()

    if search == "":
        cur.execute("""
        SELECT id,subject,question,option1,option2,option3,option4,answer
        FROM questions
        ORDER BY id
        LIMIT ? OFFSET ?
        """,(per_page, offset))
    else:
        cur.execute("""
        SELECT id,subject,question,option1,option2,option3,option4,answer
        FROM questions
        WHERE subject LIKE ?
        OR question LIKE ?
        ORDER BY id
        LIMIT ? OFFSET ?
        """,(
            "%" + search + "%",
            "%" + search + "%",
            per_page,
            offset
        ))

    questions = cur.fetchall()
    conn.close()

    return render_template(
        "edit_question.html",
        questions=questions,
        search=search,
        page=page
    )


@app.route("/delete_question")
def delete_question():

    conn = sqlite3.connect("quiz.db")
    cur = conn.cursor()

    cur.execute("""
    SELECT
        id,
        subject,
        question
    FROM questions
    ORDER BY id
    """)

    questions = cur.fetchall()

    conn.close()

    return render_template(
        "delete_question.html",
        questions=questions
    )


@app.route("/statistics")
def statistics():

    conn = sqlite3.connect("quiz.db")
    cur = conn.cursor()

    # Total Students
    cur.execute("SELECT COUNT(*) FROM students")
    students = cur.fetchone()[0]

    # Total Questions
    cur.execute("SELECT COUNT(*) FROM questions")
    questions = cur.fetchone()[0]

    # Total Quiz Attempts
    cur.execute("SELECT COUNT(*) FROM history")
    quizzes = cur.fetchone()[0]

    # Highest Percentage
    cur.execute("SELECT MAX(percentage) FROM history")
    highest = cur.fetchone()[0]

    if highest is None:
        highest = 0

    # Average Percentage
    cur.execute("SELECT AVG(percentage) FROM history")
    average = cur.fetchone()[0]

    if average is None:
        average = 0

    conn.close()

    return render_template(
        "statistics.html",
        students=students,
        questions=questions,
        quizzes=quizzes,
        highest=round(highest,2),
        average=round(average,2)
    )


@app.route("/quiz_history")
def quiz_history():

    conn = sqlite3.connect("quiz.db")
    cur = conn.cursor()

    cur.execute("""
    SELECT student_email,
           subject,
           score,
           total,
           percentage,
           quiz_date
    FROM history
    ORDER BY id DESC
    """)

    records = cur.fetchall()

    conn.close()

    return render_template(
        "history.html",
        records=records
    )


@app.route("/remove_question/<int:id>")
def remove_question(id):

    conn = sqlite3.connect("quiz.db")
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM questions WHERE id=?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect("/delete_question")


@app.route("/update_question/<int:id>", methods=["GET", "POST"])
def update_question(id):

    conn = sqlite3.connect("quiz.db")
    cur = conn.cursor()

    if request.method == "POST":

        subject = request.form["subject"]
        question = request.form["question"]
        option1 = request.form["option1"]
        option2 = request.form["option2"]
        option3 = request.form["option3"]
        option4 = request.form["option4"]
        answer = request.form["answer"]

        cur.execute("""
        UPDATE questions
        SET
            subject=?,
            question=?,
            option1=?,
            option2=?,
            option3=?,
            option4=?,
            answer=?
        WHERE id=?
        """,
        (
            subject,
            question,
            option1,
            option2,
            option3,
            option4,
            answer,
            id
        ))

        conn.commit()
        conn.close()

        return redirect("/edit_question")

    cur.execute("""
    SELECT
        id,
        subject,
        question,
        option1,
        option2,
        option3,
        option4,
        answer
    FROM questions
    WHERE id=?
    """,(id,))

    question = cur.fetchone()

    conn.close()

    return render_template(
        "update_question.html",
        question=question
    )


@app.route("/leaderboard")
def leaderboard():

    conn = sqlite3.connect("quiz.db")
    cur = conn.cursor()

    cur.execute("""
    SELECT
        students.fullname,
        students.email,
        MAX(history.percentage)
    FROM history
    JOIN students
        ON history.student_email = students.email
    GROUP BY students.email
    ORDER BY MAX(history.percentage) DESC
    """)

    leaders = cur.fetchall()

    conn.close()

    return render_template(
        "leaderboard.html",
        leaders=leaders
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/profile")
def profile():

    return render_template(
        "profile.html",
        name=session.get("name"),
        email=session.get("email")
    )


# --- CERTIFICATE ROUTE (in-memory PDF, no disk file) ---
@app.route("/certificate")
def certificate():

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(buffer)

    styles = getSampleStyleSheet()

    story = []

    story.append(Paragraph("<b><font size=24>CERTIFICATE OF ACHIEVEMENT</font></b>", styles["Title"]))

    story.append(Paragraph("<br/><br/>", styles["Normal"]))

    story.append(Paragraph("This is to certify that", styles["Heading2"]))

    story.append(Paragraph(
        f"<b><font size=20>{session.get('certificate_name')}</font></b>",
        styles["Title"]
    ))

    story.append(Paragraph("<br/>has successfully completed the", styles["Heading2"]))

    story.append(Paragraph(
        f"<b>{session.get('certificate_subject')} Quiz</b>",
        styles["Title"]
    ))

    story.append(Paragraph("<br/><br/>", styles["Normal"]))

    story.append(Paragraph(
        f"<b>Score :</b> {session.get('certificate_score')} / {session.get('certificate_total')}",
        styles["Heading2"]
    ))

    story.append(Paragraph(
        f"<b>Percentage :</b> {session.get('certificate_percentage')}%",
        styles["Heading2"]
    ))

    story.append(Paragraph(
        f"<b>Date :</b> {session.get('certificate_date')}",
        styles["Heading2"]
    ))

    story.append(Paragraph("<br/><br/><br/>", styles["Normal"]))

    story.append(Paragraph(
        "<b>ONLINE QUIZ SYSTEM</b>",
        styles["Title"]
    ))

    doc.build(story)

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="certificate.pdf",
        mimetype="application/pdf"
    )


if __name__ == "__main__":
    init_db()
    create_question_table()
    create_history_table()
    create_history_details_table()

    app.run(debug=True)