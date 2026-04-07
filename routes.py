import os
from datetime import date, datetime, timedelta
from collections import defaultdict
from flask import render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.utils import secure_filename
from app import app, db
from models import User, Student, Company, PlacementDrive, Application

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads', 'resumes')
ALLOWED_EXTENSIONS = {'pdf'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def login_required(role=None):
    """Returns None if checks pass, otherwise a redirect response."""
    if 'user_id' not in session:
        flash('Please log in to continue.', 'warning')
        return redirect(url_for('login'))
    if role and session.get('role') != role:
        flash('Access denied.', 'danger')
        return redirect(url_for('login'))
    return None


@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    role = session.get('role')
    if role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif role == 'company':
        return redirect(url_for('company_dashboard'))
    else:
        return redirect(url_for('student_dashboard'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email      = request.form.get('email', '').strip()
        password   = request.form.get('password', '')
        login_role = request.form.get('login_role', '').strip()

        # Must select a role before submitting
        if not login_role:
            flash('Please select a role (Student, Company, or Admin) before signing in.', 'warning')
            return render_template('login.html')

        user = User.query.filter_by(email=email).first()

        # Wrong credentials
        if not user or not user.check_password(password):
            flash('Invalid email or password.', 'danger')
            return render_template('login.html')

        # Role mismatch
        if login_role and user.role != login_role:
            flash(
                f'This account is registered as "{user.role.capitalize()}", '
                f'not "{login_role.capitalize()}". Please select the correct role.',
                'danger'
            )
            return render_template('login.html')

        # Deactivated / blacklisted account
        if not user.is_active:
            flash('Your account has been deactivated. Please contact the admin.', 'danger')
            return render_template('login.html')

        # Company pending approval
        if user.role == 'company':
            company = Company.query.filter_by(user_id=user.id).first()
            if company and company.approval_status != 'approved':
                status_msg = {
                    'pending':     'Your company registration is pending admin approval.',
                    'rejected':    'Your company registration has been rejected. Contact admin.',
                    'blacklisted': 'Your company has been blacklisted. Contact admin.',
                }.get(company.approval_status, 'Your company is not approved yet.')
                flash(status_msg, 'warning')
                return render_template('login.html')

        session['user_id'] = user.id
        session['role']    = user.role
        session['name']    = user.name
        flash(f'Welcome back, {user.name}!', 'success')
        return redirect(url_for('index'))

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        role     = request.form.get('role', '').strip()
        name     = request.form.get('name', '').strip()
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm_password', '')

        if role not in ('student', 'company'):
            flash('Please select a valid role.', 'danger')
            return render_template('register.html')
        if not name or not email or not password:
            flash('All fields are required.', 'danger')
            return render_template('register.html')
        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')
        if User.query.filter_by(email=email).first():
            flash('An account with this email already exists.', 'danger')
            return render_template('register.html')

        user = User(name=name, email=email, role=role, is_active=True)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        if role == 'student':
            student = Student(
                user_id      = user.id,
                age          = request.form.get('age', type=int),
                department   = request.form.get('department', '').strip(),
                cgpa         = request.form.get('cgpa', type=float) or 0.0,
                contact_info = request.form.get('contact_info', '').strip(),
            )
            db.session.add(student)
            db.session.commit()
            flash('Registration successful! You can now log in.', 'success')

        elif role == 'company':
            company = Company(
                user_id      = user.id,
                company_name = request.form.get('company_name', '').strip(),
                hr_contact   = request.form.get('hr_contact', '').strip(),
                website      = request.form.get('website', '').strip(),
            )
            db.session.add(company)
            db.session.commit()
            flash('Registration submitted! You can log in once the admin approves your company.', 'info')

        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/admin/dashboard')
def admin_dashboard():
    guard = login_required('admin')
    if guard: return guard

    pending_companies   = Company.query.filter_by(approval_status='pending').all()
    pending_drives      = PlacementDrive.query.filter_by(status='pending').all()
    recent_applications = Application.query.order_by(Application.applied_at.desc()).limit(10).all()

    stats = {
        'students':     Student.query.count(),
        'companies':    Company.query.count(),
        'drives':       PlacementDrive.query.count(),
        'applications': Application.query.count(),
    }
    return render_template(
        'admin/dashboard.html',
        stats=stats,
        pending_companies=pending_companies,
        pending_drives=pending_drives,
        recent_applications=recent_applications,
    )


@app.route('/admin/companies')
def admin_companies():
    guard = login_required('admin')
    if guard: return guard

    q     = request.args.get('q', '').strip()
    query = Company.query
    if q:
        query = query.join(User).filter(
            Company.company_name.ilike(f'%{q}%') | User.email.ilike(f'%{q}%')
        )
    companies = query.order_by(Company.registered_at.desc()).all()
    return render_template('admin/companies.html', companies=companies, q=q)


@app.route('/admin/companies/<int:company_id>/action', methods=['POST'])
def admin_company_action(company_id):
    guard = login_required('admin')
    if guard: return guard

    company = Company.query.get_or_404(company_id)
    action  = request.form.get('action')

    if action == 'approve':
        company.approval_status = 'approved'
        company.user.is_active  = True
        flash(f'{company.company_name} has been approved.', 'success')
    elif action == 'reject':
        company.approval_status = 'rejected'
        company.user.is_active  = False
        flash(f'{company.company_name} has been rejected.', 'warning')
    elif action == 'blacklist':
        company.approval_status = 'blacklisted'
        company.user.is_active  = False
        PlacementDrive.query.filter(
            PlacementDrive.company_id == company.id,
            PlacementDrive.status.in_(['pending', 'approved'])
        ).update({'status': 'rejected'}, synchronize_session=False)
        flash(f'{company.company_name} has been blacklisted and all drives cancelled.', 'danger')

    db.session.commit()
    return redirect(url_for('admin_companies'))


@app.route('/admin/students')
def admin_students():
    guard = login_required('admin')
    if guard: return guard

    q     = request.args.get('q', '').strip()
    query = Student.query.join(User)
    if q:
        query = query.filter(
            User.name.ilike(f'%{q}%') |
            Student.contact_info.ilike(f'%{q}%') |
            User.email.ilike(f'%{q}%')
        )
    students = query.order_by(User.name).all()
    return render_template('admin/students.html', students=students, q=q)


@app.route('/admin/students/<int:student_id>/action', methods=['POST'])
def admin_student_action(student_id):
    guard = login_required('admin')
    if guard: return guard

    student = Student.query.get_or_404(student_id)
    action  = request.form.get('action')

    if action == 'deactivate':
        student.user.is_active = False
        flash(f'{student.user.name} has been deactivated.', 'warning')
    elif action == 'activate':
        student.user.is_active = True
        flash(f'{student.user.name} has been restored.', 'success')
    elif action == 'delete':
        db.session.delete(student.user)
        db.session.commit()
        flash('Student deleted permanently.', 'danger')
        return redirect(url_for('admin_students'))

    db.session.commit()
    return redirect(url_for('admin_students'))


@app.route('/admin/drives')
def admin_drives():
    guard = login_required('admin')
    if guard: return guard

    drives = PlacementDrive.query.order_by(PlacementDrive.created_at.desc()).all()
    return render_template('admin/drives.html', drives=drives)


@app.route('/admin/drives/<int:drive_id>/action', methods=['POST'])
def admin_drive_action(drive_id):
    guard = login_required('admin')
    if guard: return guard

    drive  = PlacementDrive.query.get_or_404(drive_id)
    action = request.form.get('action')

    if action == 'approve':
        drive.status = 'approved'
        flash(f'Drive "{drive.job_title}" approved.', 'success')
    elif action == 'reject':
        drive.status = 'rejected'
        flash(f'Drive "{drive.job_title}" rejected.', 'warning')

    db.session.commit()
    return redirect(request.referrer or url_for('admin_drives'))


@app.route('/admin/applications')
def admin_applications():
    guard = login_required('admin')
    if guard: return guard

    applications = Application.query.order_by(Application.applied_at.desc()).all()
    return render_template('admin/applications.html', applications=applications)


@app.route('/admin/analytics')
def admin_analytics():
    guard = login_required('admin')
    if guard: return guard

    #Basic counts 
    total_students     = Student.query.count()
    total_companies    = Company.query.count()
    total_drives       = PlacementDrive.query.count()
    total_applications = Application.query.count()
    approved_companies = Company.query.filter_by(approval_status='approved').count()
    approved_drives    = PlacementDrive.query.filter_by(status='approved').count()

    #Placement rate
    selected_students = Application.query.filter_by(status='selected')\
                                         .distinct(Application.student_id).count()
    placement_rate = round((selected_students / total_students * 100), 1) if total_students else 0

    #Companies that hired at least one student
    hired_company_ids = db.session.query(Application.drive_id)\
                                  .filter_by(status='selected').subquery()
    companies_hired = db.session.query(PlacementDrive.company_id)\
                                .filter(PlacementDrive.id.in_(hired_company_ids))\
                                .distinct().count()
    companies_hired_pct = round((companies_hired / approved_companies * 100), 1) if approved_companies else 0

    #Drive approval rate
    drive_approval_rate = round((approved_drives / total_drives * 100), 1) if total_drives else 0

    #Avg applications per approved drive
    if approved_drives:
        avg_apps_per_drive = round(
            Application.query.join(PlacementDrive)
                             .filter(PlacementDrive.status == 'approved').count()
            / approved_drives, 1
        )
    else:
        avg_apps_per_drive = 0

    #Application status counts
    status_counts = {
        'applied':     Application.query.filter_by(status='applied').count(),
        'shortlisted': Application.query.filter_by(status='shortlisted').count(),
        'selected':    Application.query.filter_by(status='selected').count(),
        'rejected':    Application.query.filter_by(status='rejected').count(),
    }

    #Shortlist & rejection rates
    shortlist_rate = round((status_counts['shortlisted'] / total_applications * 100), 1) if total_applications else 0
    rejection_rate = round((status_counts['rejected']    / total_applications * 100), 1) if total_applications else 0

    #Drive status counts
    drive_status = {
        'pending':  PlacementDrive.query.filter_by(status='pending').count(),
        'approved': approved_drives,
        'rejected': PlacementDrive.query.filter_by(status='rejected').count(),
        'closed':   PlacementDrive.query.filter_by(status='closed').count(),
    }

    #Top companies by applicants
    companies_all = Company.query.filter_by(approval_status='approved').all()
    company_data  = []
    for c in companies_all:
        total_apps = sum(d.applications.count() for d in c.drives)
        selected   = sum(d.applications.filter_by(status='selected').count() for d in c.drives)
        if total_apps > 0:
            company_data.append({
                'name':     c.company_name,
                'total':    total_apps,
                'selected': selected,
                'rate':     round(selected / total_apps * 100, 1)
            })
    company_data.sort(key=lambda x: x['total'], reverse=True)
    company_data = company_data[:6]  # top 6

    company_names           = [c['name'] for c in company_data]
    company_applicants      = [c['total'] for c in company_data]
    company_selected        = [c['selected'] for c in company_data]
    company_selection_rates = [c['rate'] for c in company_data]
    top_company             = company_names[0] if company_names else '—'

    #Applications by department
    dept_counter = defaultdict(int)
    for app in Application.query.all():
        dept = app.student.department or 'Unknown'
        dept_counter[dept] += 1
    dept_sorted = sorted(dept_counter.items(), key=lambda x: x[1], reverse=True)[:7]
    dept_labels = [d[0] for d in dept_sorted]
    dept_counts = [d[1] for d in dept_sorted]
    top_dept    = dept_labels[0] if dept_labels else '—'

    #Monthly applications (last 6 months)
    monthly_data = {}
    now = datetime.utcnow()
    for i in range(5, -1, -1):
        month = now.replace(day=1) - timedelta(days=i * 30)
        key   = month.strftime('%b %Y')
        monthly_data[key] = 0
    for app in Application.query.all():
        key = app.applied_at.strftime('%b %Y')
        if key in monthly_data:
            monthly_data[key] += 1
    monthly_labels = list(monthly_data.keys())
    monthly_counts = list(monthly_data.values())

    #Resume count
    resume_count = Student.query.filter(Student.resume_path.isnot(None)).count()

    stats = dict(
        total_students=total_students,
        total_companies=total_companies,
        total_drives=total_drives,
        total_applications=total_applications,
        approved_drives=approved_drives,
        approved_companies=approved_companies,
        selected_students=selected_students,
        placement_rate=placement_rate,
        companies_hired=companies_hired,
        companies_hired_pct=companies_hired_pct,
        drive_approval_rate=drive_approval_rate,
        avg_apps_per_drive=avg_apps_per_drive,
        status_counts=status_counts,
        shortlist_rate=shortlist_rate,
        rejection_rate=rejection_rate,
        drive_status=drive_status,
        company_names=company_names,
        company_applicants=company_applicants,
        company_selected=company_selected,
        company_selection_rates=company_selection_rates,
        top_company=top_company,
        dept_labels=dept_labels,
        dept_counts=dept_counts,
        top_dept=top_dept,
        monthly_labels=monthly_labels,
        monthly_counts=monthly_counts,
        resume_count=resume_count,
    )

    return render_template('admin/analytics.html', stats=stats)


@app.route('/company/dashboard')
def company_dashboard():
    guard = login_required('company')
    if guard: return guard

    company = Company.query.filter_by(user_id=session['user_id']).first_or_404()
    drives  = PlacementDrive.query.filter_by(company_id=company.id)\
                                  .order_by(PlacementDrive.created_at.desc()).all()

    total_applicants = sum(d.applications.count() for d in drives)
    selected_count   = sum(d.applications.filter_by(status='selected').count() for d in drives)

    return render_template(
        'company/dashboard.html',
        company=company,
        drives=drives,
        total_applicants=total_applicants,
        selected_count=selected_count,
    )


@app.route('/company/drives')
def company_drives():
    guard = login_required('company')
    if guard: return guard

    company = Company.query.filter_by(user_id=session['user_id']).first_or_404()
    drives  = PlacementDrive.query.filter_by(company_id=company.id)\
                                  .order_by(PlacementDrive.created_at.desc()).all()
    return render_template('company/drives.html', drives=drives)


@app.route('/company/drives/create', methods=['GET', 'POST'])
def company_create_drive():
    guard = login_required('company')
    if guard: return guard

    company = Company.query.filter_by(user_id=session['user_id']).first_or_404()

    if company.approval_status != 'approved':
        flash('Your company must be approved by admin before creating drives.', 'warning')
        return redirect(url_for('company_dashboard'))

    if request.method == 'POST':
        deadline_str = request.form.get('application_deadline', '').strip()
        deadline     = date.fromisoformat(deadline_str) if deadline_str else None

        drive = PlacementDrive(
            company_id           = company.id,
            drive_name           = request.form.get('drive_name', '').strip(),
            job_title            = request.form.get('job_title', '').strip(),
            job_description      = request.form.get('job_description', '').strip(),
            eligibility_criteria = request.form.get('eligibility_criteria', '').strip(),
            application_deadline = deadline,
            salary               = request.form.get('salary', '').strip(),
            location             = request.form.get('location', '').strip(),
            interview_mode       = request.form.get('interview_mode', '').strip(),
            status               = 'pending',
        )
        db.session.add(drive)
        db.session.commit()
        flash('Drive submitted for admin approval.', 'success')
        return redirect(url_for('company_drives'))

    return render_template('company/drive_form.html', drive=None)


@app.route('/company/drives/<int:drive_id>/edit', methods=['GET', 'POST'])
def company_edit_drive(drive_id):
    guard = login_required('company')
    if guard: return guard

    company = Company.query.filter_by(user_id=session['user_id']).first_or_404()
    drive   = PlacementDrive.query.filter_by(id=drive_id, company_id=company.id).first_or_404()

    if request.method == 'POST':
        deadline_str = request.form.get('application_deadline', '').strip()
        deadline     = date.fromisoformat(deadline_str) if deadline_str else None

        drive.drive_name           = request.form.get('drive_name', '').strip()
        drive.job_title            = request.form.get('job_title', '').strip()
        drive.job_description      = request.form.get('job_description', '').strip()
        drive.eligibility_criteria = request.form.get('eligibility_criteria', '').strip()
        drive.application_deadline = deadline
        drive.salary               = request.form.get('salary', '').strip()
        drive.location             = request.form.get('location', '').strip()
        drive.interview_mode       = request.form.get('interview_mode', '').strip()
        drive.status               = 'pending'

        db.session.commit()
        flash('Drive updated and re-submitted for approval.', 'success')
        return redirect(url_for('company_drives'))

    return render_template('company/drive_form.html', drive=drive)


@app.route('/company/drives/<int:drive_id>/delete', methods=['POST'])
def company_delete_drive(drive_id):
    guard = login_required('company')
    if guard: return guard

    company = Company.query.filter_by(user_id=session['user_id']).first_or_404()
    drive   = PlacementDrive.query.filter_by(id=drive_id, company_id=company.id).first_or_404()

    db.session.delete(drive)
    db.session.commit()
    flash('Drive deleted.', 'info')
    return redirect(url_for('company_drives'))


@app.route('/company/drives/<int:drive_id>/applications')
def company_drive_applications(drive_id):
    guard = login_required('company')
    if guard: return guard

    company      = Company.query.filter_by(user_id=session['user_id']).first_or_404()
    drive        = PlacementDrive.query.filter_by(id=drive_id, company_id=company.id).first_or_404()
    applications = Application.query.filter_by(drive_id=drive.id)\
                                    .order_by(Application.applied_at.desc()).all()
    return render_template('company/drive_applications.html', drive=drive, applications=applications)


@app.route('/company/drives/<int:drive_id>/applications/update', methods=['POST'])
def company_update_applications(drive_id):
    guard = login_required('company')
    if guard: return guard

    company      = Company.query.filter_by(user_id=session['user_id']).first_or_404()
    drive        = PlacementDrive.query.filter_by(id=drive_id, company_id=company.id).first_or_404()
    applications = Application.query.filter_by(drive_id=drive.id).all()

    valid_statuses = {'applied', 'shortlisted', 'selected', 'rejected'}
    for app in applications:
        new_status = request.form.get(f'status_{app.id}', '').strip()
        if new_status in valid_statuses:
            app.status = new_status

    db.session.commit()
    flash('Application statuses updated.', 'success')
    return redirect(url_for('company_drive_applications', drive_id=drive.id))


@app.route('/student/dashboard')
def student_dashboard():
    guard = login_required('student')
    if guard: return guard

    student = Student.query.filter_by(user_id=session['user_id']).first_or_404()

    applied_drive_ids   = {a.drive_id for a in student.applications.all()}
    latest_drives       = PlacementDrive.query.filter_by(status='approved')\
                                              .order_by(PlacementDrive.created_at.desc())\
                                              .limit(5).all()
    recent_applications = student.applications.order_by(Application.applied_at.desc()).limit(5).all()

    open_drives    = PlacementDrive.query.filter_by(status='approved').count()
    applied_count  = student.applications.count()
    selected_count = student.applications.filter_by(status='selected').count()

    return render_template(
        'student/dashboard.html',
        student=student,
        latest_drives=latest_drives,
        applied_drive_ids=applied_drive_ids,
        recent_applications=recent_applications,
        open_drives=open_drives,
        applied_count=applied_count,
        selected_count=selected_count,
    )


@app.route('/student/drives')
def student_drives():
    guard = login_required('student')
    if guard: return guard

    student           = Student.query.filter_by(user_id=session['user_id']).first_or_404()
    applied_drive_ids = {a.drive_id for a in student.applications.all()}
    drives            = PlacementDrive.query.filter_by(status='approved')\
                                            .order_by(PlacementDrive.created_at.desc()).all()
    return render_template('student/drives.html', drives=drives, applied_drive_ids=applied_drive_ids)


@app.route('/student/drives/<int:drive_id>/apply', methods=['POST'])
def student_apply(drive_id):
    guard = login_required('student')
    if guard: return guard

    student = Student.query.filter_by(user_id=session['user_id']).first_or_404()
    drive   = PlacementDrive.query.filter_by(id=drive_id, status='approved').first_or_404()

    existing = Application.query.filter_by(student_id=student.id, drive_id=drive.id).first()
    if existing:
        flash('You have already applied for this drive.', 'warning')
        return redirect(url_for('student_drives'))

    application = Application(
        student_id     = student.id,
        drive_id       = drive.id,
        status         = 'applied',
        interview_mode = drive.interview_mode,
    )
    db.session.add(application)
    db.session.commit()
    flash(f'Successfully applied for "{drive.job_title}"!', 'success')
    return redirect(url_for('student_drives'))


@app.route('/student/applications')
def student_applications():
    guard = login_required('student')
    if guard: return guard

    student      = Student.query.filter_by(user_id=session['user_id']).first_or_404()
    applications = student.applications.order_by(Application.applied_at.desc()).all()
    return render_template('student/applications.html', applications=applications)


@app.route('/student/history')
def student_history():
    guard = login_required('student')
    if guard: return guard

    student = Student.query.filter_by(user_id=session['user_id']).first_or_404()
    history = student.applications.order_by(Application.applied_at.desc()).all()
    return render_template('student/history.html', history=history)


@app.route('/student/profile/edit', methods=['GET', 'POST'])
def student_edit_profile():
    guard = login_required('student')
    if guard: return guard

    student = Student.query.filter_by(user_id=session['user_id']).first_or_404()
    user    = student.user

    if request.method == 'POST':
        user.name               = request.form.get('name', '').strip() or user.name
        student.age             = request.form.get('age', type=int)
        student.cgpa            = request.form.get('cgpa', type=float) or student.cgpa
        student.graduation_year = request.form.get('graduation_year', type=int)
        student.department      = request.form.get('department', '').strip() or student.department
        student.contact_info    = request.form.get('contact_info', '').strip() or student.contact_info
        student.skills          = request.form.get('skills', '').strip()

        new_pw  = request.form.get('new_password', '')
        conf_pw = request.form.get('confirm_password', '')
        if new_pw:
            if new_pw != conf_pw:
                flash('Passwords do not match.', 'danger')
                return render_template('student/edit_profile.html', student=student, user=user)
            user.set_password(new_pw)

        resume_file = request.files.get('resume')
        if resume_file and resume_file.filename and allowed_file(resume_file.filename):
            filename  = secure_filename(f'student_{student.id}_{resume_file.filename}')
            save_path = os.path.join(UPLOAD_FOLDER, filename)
            resume_file.save(save_path)
            student.resume_path = filename

        db.session.commit()
        session['name'] = user.name
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('student_dashboard'))

    return render_template('student/edit_profile.html', student=student, user=user)



@app.route('/resume/<int:student_id>')
def view_resume(student_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    student = Student.query.get_or_404(student_id)
    role    = session.get('role')

    if role == 'student' and student.user_id != session['user_id']:
        flash('Access denied.', 'danger')
        return redirect(url_for('student_dashboard'))

    if not student.resume_path:
        flash('No resume uploaded.', 'warning')
        return redirect(request.referrer or url_for('index'))

    return send_from_directory(UPLOAD_FOLDER, student.resume_path)
