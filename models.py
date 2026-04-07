from app import db, app
from datetime import datetime


class User(db.Model):
    __tablename__ = 'users'
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(120), nullable=False)
    email      = db.Column(db.String(120), unique=True, nullable=False)
    password   = db.Column(db.String(256), nullable=False)          # store hashed value
    role       = db.Column(db.String(20),  nullable=False)          # 'admin' | 'company' | 'student'
    is_active  = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    student = db.relationship('Student', backref='user', uselist=False)
    company = db.relationship('Company', backref='user', uselist=False)

    def set_password(self, plain_password):
        from werkzeug.security import generate_password_hash
        self.password = generate_password_hash(plain_password)

    def check_password(self, plain_password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password, plain_password)

    def __repr__(self):
        return f'<User id={self.id} email={self.email} role={self.role}>'


class Student(db.Model):
    __tablename__ = 'students'
    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    age             = db.Column(db.Integer,     nullable=True)
    department      = db.Column(db.String(120), nullable=False)   
    graduation_year = db.Column(db.Integer,     nullable=True)
    cgpa            = db.Column(db.Float,       nullable=False)
    contact_info    = db.Column(db.String(120), nullable=False)
    skills          = db.Column(db.Text,        nullable=True)    # free-text / comma-separated

    
    resume_path     = db.Column(db.Text, nullable=True)           

    applications = db.relationship('Application', backref='student', lazy='dynamic')

    def __repr__(self):
        return f'<Student id={self.id} user_id={self.user_id}>'


class Company(db.Model):
    __tablename__ = 'companies'

    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    company_name    = db.Column(db.String(200), nullable=False)   
    hr_contact      = db.Column(db.String(120), nullable=True)    
    website         = db.Column(db.String(200), nullable=True)
    overview        = db.Column(db.Text,        nullable=True)   
    approval_status = db.Column(db.String(20), default='pending', nullable=False)
    # 'pending' | 'approved' | 'rejected' | 'blacklisted'

    registered_at   = db.Column(db.DateTime, default=datetime.utcnow)

    drives = db.relationship('PlacementDrive', backref='company', lazy='dynamic')

    def __repr__(self):
        return f'<Company id={self.id} name={self.company_name} status={self.approval_status}>'


class PlacementDrive(db.Model):
    __tablename__ = 'placement_drives'

    id                   = db.Column(db.Integer, primary_key=True)
    company_id           = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    drive_name           = db.Column(db.String(200), nullable=False)
    job_title            = db.Column(db.String(200), nullable=False)
    job_description      = db.Column(db.Text,        nullable=True)
    eligibility_criteria = db.Column(db.Text,        nullable=True)
    application_deadline = db.Column(db.Date,        nullable=True)
    salary               = db.Column(db.String(50),  nullable=True)   # "Salary: 600000"
    location             = db.Column(db.String(200), nullable=True)   # "location: Chennai"
    interview_mode       = db.Column(db.String(50),  nullable=True)   # "In-person" in history table
    status     = db.Column(db.String(20), default='pending', nullable=False)
    # 'pending', 'approved', 'selected', 'rejected' 
    created_at = db.Column(db.DateTime,  default=datetime.utcnow)

    applications = db.relationship('Application', backref='drive', lazy='dynamic')

    def __repr__(self):
        return f'<PlacementDrive id={self.id} title={self.job_title} status={self.status}>'


class Application(db.Model):
    __tablename__ = 'applications'

    id         = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'),          nullable=False)
    drive_id   = db.Column(db.Integer, db.ForeignKey('placement_drives.id'),  nullable=False)

    applied_at     = db.Column(db.DateTime, default=datetime.utcnow)
    status         = db.Column(db.String(20), default='applied', nullable=False)
    # 'applied' | 'shortlisted' | 'selected' | 'rejected'

    interview_mode = db.Column(db.String(50), nullable=True)   
    remark         = db.Column(db.Text,       nullable=True)  

    # Prevent duplicate applications
    __table_args__ = (
        db.UniqueConstraint('student_id', 'drive_id', name='uq_student_drive'),
    )

    def __repr__(self):
        return (f'<Application id={self.id} student={self.student_id} '
                f'drive={self.drive_id} status={self.status}>')


with app.app_context():
    db.create_all()

    # Seed the pre-existing admin user if not already present
    if not User.query.filter_by(role='admin').first():
        admin = User(
            name      = 'Admin',
            email     = 'admin@placement.com',
            role      = 'admin',
            is_active = True,
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()



