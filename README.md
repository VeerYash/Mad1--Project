# PlacementHub — Placement Portal Application

> MAD-1 Project | IIT Madras BS Degree Program
>
> **Student:** Yash Bhagwat Veer | **Roll No:** 23f3003957 | **Email:** 23f3003957@ds.study.iitm.ac.in

---

## About the Project

PlacementHub is a **role-based web application** that allows an institute's placement cell (Admin), companies, and students to manage campus recruitment activities efficiently. It replaces manual spreadsheet and email-based processes with a centralized portal supporting three distinct user roles.

---

## Tech Stack

| Technology | Purpose |
|---|---|
| **Flask** | Backend web framework, routing, sessions, request handling |
| **SQLAlchemy** | ORM for database models and relationships |
| **SQLite** | Local relational database (created programmatically) |
| **Jinja2** | Server-side HTML template rendering |
| **Bootstrap 5** | Responsive UI, styling, and layout |
| **Werkzeug** | Password hashing and secure file uploads |
| **Chart.js** | Analytics charts on admin dashboard |
| **Bootstrap Icons** | Icon library used throughout the UI |

---

## Roles and Features

### Admin
- Dashboard with live stats (students, companies, drives, applications)
- Approve or reject company registrations
- Approve or reject placement drives
- Blacklist companies (auto-cancels all their active drives)
- Search students by name, ID, email, or contact
- Search companies by name
- Activate, deactivate, or permanently delete student accounts
- View all applications across all drives
- Analytics page with 6 Chart.js charts (placement rate, department breakdown, monthly trends, and more)

### Company
- Register and await admin approval
- Create, edit, and delete placement drives
- View student applications per drive
- Update application status (Applied / Shortlisted / Selected / Rejected)
- View resume of applicants

### Student
- Self-register and log in
- Browse all admin-approved placement drives
- Apply for drives (duplicate application prevention enforced)
- Track application status in real time
- View complete placement history
- Edit profile (CGPA, department, skills, contact)
- Upload PDF resume

---

## Project Structure

```
project/
├── app.py                       # Flask app entry point, DB config, secret key
├── models.py                    # SQLAlchemy models, db.create_all(), admin seeding
├── routes.py                    # All route handlers (auth, admin, company, student)
├── README.md                    # This file
├── Project Report.pdf           # Project report
│
├── templates/
│   ├── base.html                # Shared base layout with navbar
│   ├── login.html               # Login page with role selector
│   ├── register.html            # Registration page (student / company)
│   │
│   ├── admin/
│   │   ├── dashboard.html       # Admin dashboard with stats and pending approvals
│   │   ├── companies.html       # Manage and search companies
│   │   ├── students.html        # Manage and search students
│   │   ├── drives.html          # View and approve/reject drives
│   │   ├── applications.html    # View all applications
│   │   └── analytics.html       # Placement analytics with Chart.js
│   │
│   ├── company/
│   │   ├── dashboard.html       # Company dashboard with drive stats
│   │   ├── drives.html          # Manage placement drives
│   │   ├── drive_form.html      # Create / edit a drive
│   │   └── drive_applications.html  # View and update applicant statuses
│   │
│   └── student/
│       ├── dashboard.html       # Student dashboard with open drives
│       ├── drives.html          # Browse approved placement drives
│       ├── applications.html    # View application statuses
│       ├── history.html         # Complete placement history
│       └── edit_profile.html    # Edit profile and upload resume
│
└── uploads/
    └── resumes/                 # Student PDF resumes stored here
```

---

## How to Run

### 1. Install required packages

```bash
pip install flask flask-sqlalchemy werkzeug
```

### 2. Navigate to the project folder

```bash
cd path/to/project
```

### 3. Run the application

```bash
python app.py
```

### 4. Open in browser

```
http://127.0.0.1:5000
```

> The database and all tables are created **automatically** on first run. The admin account is also seeded automatically. No manual setup needed.

---

## Login Credentials

| Role | Email | Password |
|---|---|---|
| Admin | admin@placement.com | admin123 |
| Company | Register via `/register` | Your chosen password |
| Student | Register via `/register` | Your chosen password |

> **Note:** Companies must be approved by the Admin before they can log in.

---

## Database Schema

| Table | Description |
|---|---|
| `users` | Stores credentials and role for all user types |
| `students` | Student profile details linked to users |
| `companies` | Company profile details linked to users |
| `placement_drives` | Job drives created by companies |
| `applications` | Student applications for drives (unique per student + drive) |

---

## Analytics (Admin Only)

The admin analytics page includes 6 interactive Chart.js charts:

1. **Doughnut** — Application status breakdown (Applied / Shortlisted / Selected / Rejected)
2. **Grouped Bar** — Top companies by total applicants vs selected
3. **Pie** — Drive status distribution (Pending / Approved / Rejected / Closed)
4. **Horizontal Bar** — Applications by student department
5. **Line Chart** — Application activity over last 6 months
6. **Horizontal Bar** — Selection rate percentage per company

---

## Notes

- No manual database creation required — `db.create_all()` handles everything on startup
- JS is only used for UI interactions (role selector, mobile navbar) — all core logic is server-side as required by the project spec
- Resume uploads are PDF only, stored in `uploads/resumes/` with secure filenames
- Role-based access is enforced on every route via `login_required(role)` guard
- Duplicate application prevention enforced at both DB level (UniqueConstraint) and route level
