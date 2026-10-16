# FindingPlayers — Flask starter project

A full-stack starter implementation of the FindingPlayers student collaboration platform using **Python + Flask**, **SQLite**, and **HTML/CSS/JavaScript**.

## Features included
- Register, sign in, sign out, password hashing
- Student profiles with college, branch, bio, skills, interests, and portfolio
- Search/filter projects and student members
- Create projects with required skills, team size, and deadline
- Apply to projects and track application status
- Project hosts accept/reject applicants
- Dashboard for hosted projects, applications, and accepted projects
- Starter team workspace with tasks and completion toggles
- Mark a project completed
- Basic teammate rating endpoint and database table
- JSON API at `/api/projects`
- Responsive interface

## Run locally
Python 3.10+ recommended.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000

### Demo account
- Email: `demo@findingplayers.test`
- Password: `demo1234`

The demo account is only for local development. Change `SECRET_KEY` and remove demo credentials before deployment.

## Project structure
```
findingplayers_flask/
├── app.py
├── requirements.txt
├── README.md
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── auth.html
│   ├── profile.html
│   ├── members.html
│   ├── project_form.html
│   ├── project_detail.html
│   ├── dashboard.html
│   └── 404.html
└── static/
    ├── css/style.css
    └── js/main.js
```

## Notes before production
This is a functional MVP scaffold, not a production-hardened service. Add CSRF protection, email verification, password reset, rate limiting, stronger authorization/team membership rules, file upload storage, tests, migrations, and deployment configuration before public launch. Never use Flask's development server for production.
