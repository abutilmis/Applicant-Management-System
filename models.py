from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Association table for applicant-upload many-to-many
applicant_upload = db.Table('applicant_upload',
    db.Column('applicant_id', db.Integer, db.ForeignKey('applicant.id'), primary_key=True),
    db.Column('upload_batch_id', db.Integer, db.ForeignKey('upload_batch.id'), primary_key=True)
)

class UploadBatch(db.Model):
    __tablename__ = 'upload_batch'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    upload_type = db.Column(db.String(20), nullable=False)  # 'applicant', 'called', 'passed'
    uploaded_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class Applicant(db.Model):
    __tablename__ = 'applicant'
    id = db.Column(db.Integer, primary_key=True)
    serial = db.Column(db.String(50))
    full_name = db.Column(db.String(200))
    labor_id = db.Column(db.String(50), unique=False)   # or just omit unique=True
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))
    region = db.Column(db.String(100))
    experience_years = db.Column(db.Float)
    phone = db.Column(db.String(50))
    alt_phone = db.Column(db.String(50))
    passport = db.Column(db.String(50))
    job_title = db.Column(db.String(200))
    education_level = db.Column(db.String(100))
    education_field = db.Column(db.String(200))
    experience_description = db.Column(db.Text)
    education_document = db.Column(db.String(200))
    cv_file = db.Column(db.String(200))
    passport_file = db.Column(db.String(200))
    submission_id = db.Column(db.String(100))
    submission_create_date = db.Column(db.String(20))  # store as string, can be parsed later
    submission_status = db.Column(db.String(50))

    is_called = db.Column(db.Boolean, default=False)
    is_passed = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    # Relationships
    upload_batches = db.relationship('UploadBatch', secondary=applicant_upload, backref=db.backref('applicants', lazy='dynamic'))
    called_records = db.relationship('Called', backref='applicant', lazy=True)
    passed_records = db.relationship('Passed', backref='applicant', lazy=True)

class Called(db.Model):
    __tablename__ = 'called'
    id = db.Column(db.Integer, primary_key=True)
    applicant_id = db.Column(db.Integer, db.ForeignKey('applicant.id'), nullable=False)
    upload_batch_id = db.Column(db.Integer, db.ForeignKey('upload_batch.id'), nullable=False)
    called_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class Passed(db.Model):
    __tablename__ = 'passed'
    id = db.Column(db.Integer, primary_key=True)
    applicant_id = db.Column(db.Integer, db.ForeignKey('applicant.id'), nullable=False)
    upload_batch_id = db.Column(db.Integer, db.ForeignKey('upload_batch.id'), nullable=False)
    passed_at = db.Column(db.DateTime, default=db.func.current_timestamp())