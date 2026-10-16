from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, date
import sqlite3, os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-development-secret")
DB_PATH = os.path.join(os.path.dirname(__file__), "findingplayers.db")

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, college TEXT DEFAULT '',
            branch TEXT DEFAULT '', bio TEXT DEFAULT '',
            skills TEXT DEFAULT '', interests TEXT DEFAULT '',
            portfolio TEXT DEFAULT '', created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title TEXT NOT NULL, description TEXT NOT NULL,
            skills TEXT DEFAULT '', team_size INTEGER DEFAULT 4,
            deadline TEXT DEFAULT '', status TEXT DEFAULT 'Open',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            message TEXT DEFAULT '', status TEXT DEFAULT 'Pending',
            created_at TEXT NOT NULL,
            UNIQUE(project_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            assigned_to INTEGER REFERENCES users(id) ON DELETE SET NULL,
            title TEXT NOT NULL, due_date TEXT DEFAULT '',
            status TEXT DEFAULT 'To do', created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            from_user INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            to_user INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            score INTEGER NOT NULL CHECK(score BETWEEN 1 AND 5),
            feedback TEXT DEFAULT '', created_at TEXT NOT NULL,
            UNIQUE(project_id, from_user, to_user)
        );
        """)
        count = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if count == 0:
            # Friendly sample project so the dashboard is useful on first run.
            con.execute("""INSERT INTO users(name,email,password_hash,college,branch,bio,skills,interests,created_at)
                VALUES(?,?,?,?,?,?,?,?,?)""",
                ("Demo Student","demo@findingplayers.test",generate_password_hash("demo1234"),
                 "Graphic Era Hill University","Computer Science","Building useful products with a student team.",
                 "Python, Flask, UI Design","Web Development, AI",datetime.utcnow().isoformat()))
            uid = con.execute("SELECT id FROM users WHERE email=?",("demo@findingplayers.test",)).fetchone()["id"]
            con.execute("""INSERT INTO projects(owner_id,title,description,skills,team_size,deadline,status,created_at)
                VALUES(?,?,?,?,?,?,?,?)""",
                (uid,"Campus Collaboration Hub","A web app that helps students find teammates for meaningful projects.",
                 "Flask, JavaScript, UI/UX",4,"2026-12-15","Open",datetime.utcnow().isoformat()))

def current_user():
    if "user_id" not in session:
        return None
    with db() as con:
        return con.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not current_user():
            flash("Please sign in to continue.", "info")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapped

@app.route("/")
def home():
    user = current_user()
    q = request.args.get("q", "").strip()
    skill = request.args.get("skill", "").strip()
    with db() as con:
        sql = """SELECT p.*, u.name AS owner_name, u.college AS owner_college,
                 (SELECT COUNT(*) FROM applications a WHERE a.project_id=p.id AND a.status='Accepted') AS accepted_count
                 FROM projects p JOIN users u ON u.id=p.owner_id WHERE p.status='Open'"""
        params = []
        if q:
            sql += " AND (p.title LIKE ? OR p.description LIKE ? OR p.skills LIKE ?)"
            params += [f"%{q}%"] * 3
        if skill:
            sql += " AND p.skills LIKE ?"
            params.append(f"%{skill}%")
        sql += " ORDER BY p.created_at DESC"
        projects = con.execute(sql, params).fetchall()
        members = con.execute("""SELECT id,name,college,branch,bio,skills,interests,portfolio
                                 FROM users ORDER BY created_at DESC LIMIT 8""").fetchall()
        counts = {
            "projects": con.execute("SELECT COUNT(*) FROM projects").fetchone()[0],
            "students": con.execute("SELECT COUNT(*) FROM users").fetchone()[0],
            "applications": con.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
        }
    return render_template("index.html", user=user, projects=projects, members=members, counts=counts, q=q, skill=skill)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        college = request.form.get("college", "").strip()
        branch = request.form.get("branch", "").strip()
        if not name or not email or len(password) < 8:
            flash("Enter your name and email, and use a password with at least 8 characters.", "error")
            return render_template("auth.html", mode="register")
        try:
            with db() as con:
                con.execute("""INSERT INTO users(name,email,password_hash,college,branch,created_at)
                    VALUES(?,?,?,?,?,?)""",
                    (name,email,generate_password_hash(password),college,branch,datetime.utcnow().isoformat()))
                uid = con.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()["id"]
            session["user_id"] = uid
            flash("Welcome! Finish your profile to help teammates find you.", "success")
            return redirect(url_for("profile"))
        except sqlite3.IntegrityError:
            flash("That email already has an account. Please sign in.", "error")
    return render_template("auth.html", mode="register")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        with db() as con:
            user = con.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("dashboard"))
        flash("Email or password was incorrect.", "error")
    return render_template("auth.html", mode="login")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("home"))

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = current_user()
    if request.method == "POST":
        fields = {k: request.form.get(k, "").strip() for k in ["college","branch","bio","skills","interests","portfolio"]}
        with db() as con:
            con.execute("""UPDATE users SET college=?,branch=?,bio=?,skills=?,interests=?,portfolio=? WHERE id=?""",
                        (fields["college"],fields["branch"],fields["bio"],fields["skills"],fields["interests"],fields["portfolio"],user["id"]))
        flash("Profile updated.", "success")
        return redirect(url_for("profile"))
    return render_template("profile.html", user=user)

@app.route("/members")
def members():
    user = current_user()
    q = request.args.get("q", "").strip()
    skill = request.args.get("skill", "").strip()
    with db() as con:
        sql = "SELECT * FROM users WHERE 1=1"
        params = []
        if q:
            sql += " AND (name LIKE ? OR college LIKE ? OR interests LIKE ?)"
            params += [f"%{q}%"] * 3
        if skill:
            sql += " AND skills LIKE ?"
            params.append(f"%{skill}%")
        sql += " ORDER BY name"
        people = con.execute(sql, params).fetchall()
    return render_template("members.html", user=user, members=people, q=q, skill=skill)

@app.route("/projects/new", methods=["GET", "POST"])
@login_required
def new_project():
    user = current_user()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        skills = request.form.get("skills", "").strip()
        deadline = request.form.get("deadline", "").strip()
        try:
            team_size = max(2, min(30, int(request.form.get("team_size", "4"))))
        except ValueError:
            team_size = 4
        if not title or not description:
            flash("Project title and description are required.", "error")
        else:
            with db() as con:
                con.execute("""INSERT INTO projects(owner_id,title,description,skills,team_size,deadline,status,created_at)
                    VALUES(?,?,?,?,?,?,?,?)""",
                    (user["id"],title,description,skills,team_size,deadline,"Open",datetime.utcnow().isoformat()))
            flash("Project published. Students can now apply to join.", "success")
            return redirect(url_for("dashboard"))
    return render_template("project_form.html", user=user)

@app.route("/projects/<int:project_id>")
def project_detail(project_id):
    user = current_user()
    with db() as con:
        project = con.execute("""SELECT p.*,u.name owner_name,u.college owner_college
            FROM projects p JOIN users u ON u.id=p.owner_id WHERE p.id=?""",(project_id,)).fetchone()
        if not project:
            flash("Project not found.", "error")
            return redirect(url_for("home"))
        application = None
        if user:
            application = con.execute("SELECT * FROM applications WHERE project_id=? AND user_id=?",
                                       (project_id,user["id"])).fetchone()
        applicants = []
        if user and user["id"] == project["owner_id"]:
            applicants = con.execute("""SELECT a.*,u.name,u.college,u.skills FROM applications a
                JOIN users u ON u.id=a.user_id WHERE a.project_id=? ORDER BY a.created_at DESC""",(project_id,)).fetchall()
        tasks = con.execute("""SELECT t.*,u.name assigned_name FROM tasks t LEFT JOIN users u ON u.id=t.assigned_to
                               WHERE t.project_id=? ORDER BY t.id DESC""",(project_id,)).fetchall()
    return render_template("project_detail.html", user=user, project=project, application=application, applicants=applicants, tasks=tasks)

@app.route("/projects/<int:project_id>/apply", methods=["POST"])
@login_required
def apply_project(project_id):
    user = current_user()
    with db() as con:
        project = con.execute("SELECT * FROM projects WHERE id=?",(project_id,)).fetchone()
        if not project:
            flash("Project not found.", "error")
        elif project["owner_id"] == user["id"]:
            flash("You already own this project.", "info")
        else:
            try:
                con.execute("""INSERT INTO applications(project_id,user_id,message,status,created_at)
                    VALUES(?,?,?,?,?)""",(project_id,user["id"],request.form.get("message","").strip(),"Pending",datetime.utcnow().isoformat()))
                flash("Application sent to the project host.", "success")
            except sqlite3.IntegrityError:
                flash("You've already applied to this project.", "info")
    return redirect(url_for("project_detail", project_id=project_id))

@app.route("/applications/<int:application_id>/<action>", methods=["POST"])
@login_required
def update_application(application_id, action):
    if action not in ("accept", "reject"):
        return redirect(url_for("dashboard"))
    with db() as con:
        row = con.execute("""SELECT a.*,p.owner_id FROM applications a JOIN projects p ON p.id=a.project_id
                             WHERE a.id=?""",(application_id,)).fetchone()
        if not row or row["owner_id"] != session["user_id"]:
            flash("Only the project host can review this application.", "error")
        else:
            status = "Accepted" if action == "accept" else "Rejected"
            con.execute("UPDATE applications SET status=? WHERE id=?", (status, application_id))
            flash(f"Application {status.lower()}.", "success")
            return redirect(url_for("project_detail", project_id=row["project_id"]))
    return redirect(url_for("dashboard"))

@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    with db() as con:
        projects = con.execute("""SELECT p.*, (SELECT COUNT(*) FROM applications a WHERE a.project_id=p.id) application_count
            FROM projects p WHERE p.owner_id=? ORDER BY p.created_at DESC""",(user["id"],)).fetchall()
        applications = con.execute("""SELECT a.*,p.title,p.id project_id,p.status project_status
            FROM applications a JOIN projects p ON p.id=a.project_id WHERE a.user_id=? ORDER BY a.created_at DESC""",(user["id"],)).fetchall()
        accepted = con.execute("""SELECT a.*,p.title,p.id project_id FROM applications a JOIN projects p ON p.id=a.project_id
            WHERE a.user_id=? AND a.status='Accepted'""",(user["id"],)).fetchall()
        task_count = con.execute("""SELECT COUNT(*) FROM tasks t JOIN projects p ON p.id=t.project_id
            WHERE (p.owner_id=? OR t.assigned_to=?) AND t.status!='Done'""",(user["id"],user["id"])).fetchone()[0]
    return render_template("dashboard.html", user=user, projects=projects, applications=applications, accepted=accepted, task_count=task_count)

@app.route("/projects/<int:project_id>/tasks", methods=["POST"])
@login_required
def add_task(project_id):
    user = current_user()
    title = request.form.get("title","").strip()
    due_date = request.form.get("due_date","").strip()
    with db() as con:
        project = con.execute("SELECT * FROM projects WHERE id=?",(project_id,)).fetchone()
        if not project or project["owner_id"] != user["id"]:
            flash("Only the project host can add tasks in this starter version.", "error")
        elif title:
            con.execute("INSERT INTO tasks(project_id,title,due_date,status,created_at) VALUES(?,?,?,?,?)",
                        (project_id,title,due_date,"To do",datetime.utcnow().isoformat()))
            flash("Task added to the workspace.", "success")
    return redirect(url_for("project_detail", project_id=project_id))

@app.route("/tasks/<int:task_id>/toggle", methods=["POST"])
@login_required
def toggle_task(task_id):
    user = current_user()
    with db() as con:
        task = con.execute("""SELECT t.*,p.owner_id FROM tasks t JOIN projects p ON p.id=t.project_id WHERE t.id=?""",(task_id,)).fetchone()
        if task and (task["owner_id"] == user["id"] or task["assigned_to"] == user["id"]):
            new_status = "Done" if task["status"] != "Done" else "To do"
            con.execute("UPDATE tasks SET status=? WHERE id=?", (new_status, task_id))
            flash("Task status updated.", "success")
        elif task:
            flash("You don't have permission to update this task.", "error")
        if task:
            return redirect(url_for("project_detail", project_id=task["project_id"]))
    return redirect(url_for("dashboard"))

@app.route("/projects/<int:project_id>/rate", methods=["POST"])
@login_required
def rate_teammate(project_id):
    user = current_user()
    try:
        target = int(request.form.get("to_user", "0"))
        score = int(request.form.get("score", "5"))
    except ValueError:
        return redirect(url_for("project_detail", project_id=project_id))
    feedback = request.form.get("feedback","").strip()
    with db() as con:
        project = con.execute("SELECT * FROM projects WHERE id=?",(project_id,)).fetchone()
        if not project or project["status"] != "Completed":
            flash("Ratings are available after the host marks a project complete.", "info")
        elif target == user["id"] or score not in range(1,6):
            flash("Choose a valid teammate and rating.", "error")
        else:
            try:
                con.execute("""INSERT INTO ratings(project_id,from_user,to_user,score,feedback,created_at)
                    VALUES(?,?,?,?,?,?)""",(project_id,user["id"],target,score,feedback,datetime.utcnow().isoformat()))
                flash("Thanks for sharing your feedback.", "success")
            except sqlite3.IntegrityError:
                flash("You've already rated this teammate for this project.", "info")
    return redirect(url_for("project_detail", project_id=project_id))

@app.route("/projects/<int:project_id>/complete", methods=["POST"])
@login_required
def complete_project(project_id):
    user = current_user()
    with db() as con:
        project = con.execute("SELECT * FROM projects WHERE id=?",(project_id,)).fetchone()
        if project and project["owner_id"] == user["id"]:
            con.execute("UPDATE projects SET status='Completed' WHERE id=?", (project_id,))
            flash("Project marked as completed.", "success")
        else:
            flash("Only the project host can complete this project.", "error")
    return redirect(url_for("project_detail", project_id=project_id))

@app.route("/api/projects")
def api_projects():
    with db() as con:
        rows = con.execute("""SELECT p.id,p.title,p.description,p.skills,p.status,u.name AS owner
            FROM projects p JOIN users u ON u.id=p.owner_id ORDER BY p.created_at DESC""").fetchall()
    return jsonify([dict(row) for row in rows])

@app.errorhandler(404)
def not_found(_):
    return render_template("404.html", user=current_user()), 404

with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(debug=True)
