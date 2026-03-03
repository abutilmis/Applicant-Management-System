import os
import uuid
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from models import db, UploadBatch, Applicant, applicant_upload, Called, Passed
from excel_service import ExcelService
from deduplicator import Deduplicator
from stats import StatsGenerator
import pandas as pd
import io

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback-dev-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///applicants.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = '/tmp/uploads'   # Render has writable /tmp

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)
with app.app_context():
    print("Creating database tables...")
    db.create_all()
    print("Tables created successfully (or already exist).")

# ------------------------------
# Presenter Routes (unchanged)
# ------------------------------

@app.route('/')
def index():
    stats = StatsGenerator.get_dashboard_stats()
    return render_template('index.html', stats=stats)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        upload_type = request.form.get('upload_type')
        file = request.files.get('file')
        if not file or file.filename == '':
            flash('No file selected', 'danger')
            return redirect(request.url)
        if not file.filename.endswith(('.xlsx', '.xls')):
            flash('Please upload an Excel file (.xlsx or .xls)', 'danger')
            return redirect(request.url)

        filename = f"{uuid.uuid4()}_{file.filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            df = pd.read_excel(filepath, dtype=str)
            df = ExcelService.normalize_columns(df)
            expected_columns = ExcelService.CANONICAL_COLUMNS
            missing = set(expected_columns) - set(df.columns)
            if missing:
                flash(f'Missing columns after mapping: {", ".join(missing)}', 'danger')
                return redirect(request.url)

            df = ExcelService.clean_dataframe(df)

            batch = UploadBatch(filename=file.filename, upload_type=upload_type)
            db.session.add(batch)
            db.session.flush()

            if upload_type == 'applicant':
                processed = 0
                linked_applicant_ids = set()
                for _, row in df.iterrows():
                    row_dict = row.to_dict()
                    existing = Deduplicator.find_duplicate(row_dict)
                    if existing:
                        applicant = existing
                    else:
                        applicant = Applicant(
                            serial=row_dict.get('ተራ ቁ'),
                            full_name=row_dict.get('ሙሉ ስም'),
                            labor_id=row_dict.get('የሰራተኛ መለያ ቁጥር'),
                            age=row_dict.get('ዕድሜ'),
                            gender=row_dict.get('ጾታ'),
                            region=row_dict.get('ነዋሪ የሆኑበት ክልል'),
                            experience_years=row_dict.get('የሥራ ልምድ ዓመት፡'),
                            phone=row_dict.get('ስልክ/ሞባይል'),
                            alt_phone=row_dict.get('አማራጭ ስልክ ቁጥር'),
                            passport=row_dict.get('ፓስፖርት'),
                            job_title=row_dict.get('የስራ መደብ'),
                            education_level=row_dict.get('የትምህርት ደረጃ'),
                            education_field=row_dict.get('የሰለጠኑበት ትምህርት ዘርፍ:'),
                            experience_description=row_dict.get('የስራ ልምድ'),
                            education_document=row_dict.get('የትምህርት ማስረጃ'),
                            cv_file=row_dict.get('CV ያስገቡ'),
                            passport_file=row_dict.get('ፓስፖርትፋይል'),
                            submission_id=row_dict.get('Submission ID'),
                            submission_create_date=row_dict.get('Submission Create Date'),
                            submission_status=row_dict.get('Submission Status')
                        )
                        db.session.add(applicant)
                        db.session.flush()
                        processed += 1

                    if applicant.id not in linked_applicant_ids:
                        db.session.execute(applicant_upload.insert().values(
                            applicant_id=applicant.id,
                            upload_batch_id=batch.id
                        ))
                        linked_applicant_ids.add(applicant.id)

                db.session.commit()
                flash(f'Applicants uploaded: {processed} new, {len(df)-processed} duplicates skipped/updated.', 'success')

            elif upload_type == 'called':
                matched = 0
                for _, row in df.iterrows():
                    row_dict = row.to_dict()
                    row_dict = ExcelService.clean_row(row_dict)
                    applicant = Deduplicator.find_duplicate(row_dict)
                    if applicant:
                        if not applicant.is_called:
                            applicant.is_called = True
                            called_record = Called(applicant_id=applicant.id, upload_batch_id=batch.id)
                            db.session.add(called_record)
                            matched += 1
                db.session.commit()
                flash(f'Called applicants matched: {matched}', 'success')

            elif upload_type == 'passed':
                matched = 0
                for _, row in df.iterrows():
                    row_dict = row.to_dict()
                    row_dict = ExcelService.clean_row(row_dict)
                    applicant = Deduplicator.find_duplicate(row_dict)
                    if applicant:
                        if not applicant.is_passed:
                            applicant.is_passed = True
                            passed_record = Passed(applicant_id=applicant.id, upload_batch_id=batch.id)
                            db.session.add(passed_record)
                            matched += 1
                db.session.commit()
                flash(f'Passed applicants matched: {matched}', 'success')

        except Exception as e:
            db.session.rollback()
            flash(f'Error processing file: {str(e)}', 'danger')
        finally:
            os.remove(filepath)

        return redirect(url_for('index'))

    return render_template('upload.html')

@app.route('/applicants')
def applicants():
    filters = {
        'job_title': request.args.get('job_title'),
        'region': request.args.get('region'),
        'gender': request.args.get('gender'),
        'education_level': request.args.get('education_level'),
        'experience_min': request.args.get('experience_min'),
        'experience_max': request.args.get('experience_max'),
        'called': request.args.get('called'),
        'passed': request.args.get('passed'),
        'date_from': request.args.get('date_from'),
        'date_to': request.args.get('date_to')
    }
    filters = {k: v for k, v in filters.items() if v}

    query = Applicant.query
    if 'job_title' in filters:
        query = query.filter(Applicant.job_title.ilike(f"%{filters['job_title']}%"))
    if 'region' in filters:
        query = query.filter(Applicant.region == filters['region'])
    if 'gender' in filters:
        query = query.filter(Applicant.gender == filters['gender'])
    if 'education_level' in filters:
        query = query.filter(Applicant.education_level == filters['education_level'])
    if 'experience_min' in filters:
        query = query.filter(Applicant.experience_years >= float(filters['experience_min']))
    if 'experience_max' in filters:
        query = query.filter(Applicant.experience_years <= float(filters['experience_max']))
    if 'called' in filters:
        called_val = filters['called'].lower() == 'true'
        query = query.filter(Applicant.is_called == called_val)
    if 'passed' in filters:
        passed_val = filters['passed'].lower() == 'true'
        query = query.filter(Applicant.is_passed == passed_val)
    if 'date_from' in filters:
        query = query.filter(Applicant.submission_create_date >= filters['date_from'])
    if 'date_to' in filters:
        query = query.filter(Applicant.submission_create_date <= filters['date_to'])

    applicants_list = query.all()
    distinct_jobs = db.session.query(Applicant.job_title.distinct()).filter(Applicant.job_title.isnot(None)).all()
    job_titles = [job[0] for job in distinct_jobs if job[0]]

    return render_template('applicants.html', applicants=applicants_list, filters=filters, job_titles=job_titles)

@app.route('/statistics')
def statistics():
    stats = StatsGenerator.get_all_stats()
    return render_template('statistics.html', stats=stats)

@app.route('/export')
def export():
    export_type = request.args.get('type', 'master')
    if export_type == 'master':
        query = Applicant.query
        filename = 'master_applicants.xlsx'
    elif export_type == 'called':
        query = Applicant.query.filter(Applicant.is_called == True)
        filename = 'called_applicants.xlsx'
    elif export_type == 'passed':
        query = Applicant.query.filter(Applicant.is_passed == True)
        filename = 'passed_applicants.xlsx'
    elif export_type == 'filtered':
        # rebuild filter from request.args – simplified for brevity
        # you may reuse the same logic as in /applicants
        query = Applicant.query
        filename = 'filtered_applicants.xlsx'
    else:
        return "Invalid export type", 400

    data = query.all()
    df = ExcelService.applicants_to_dataframe(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Applicants')
    output.seek(0)
    return send_file(output, download_name=filename, as_attachment=True)

@app.route('/manage', methods=['POST'])
def manage_database():
    action = request.form.get('action')
    if action == 'refresh':
        flash('Data refreshed', 'success')
    elif action == 'undo_last':
        last_batch = UploadBatch.query.order_by(UploadBatch.id.desc()).first()
        if last_batch:
            db.session.execute(applicant_upload.delete().where(applicant_upload.c.upload_batch_id == last_batch.id))
            Called.query.filter_by(upload_batch_id=last_batch.id).delete()
            Passed.query.filter_by(upload_batch_id=last_batch.id).delete()
            db.session.delete(last_batch)
            db.session.commit()
            flash(f'Last upload batch ({last_batch.filename}) undone.', 'success')
        else:
            flash('No upload to undo.', 'warning')
    elif action == 'delete_batch':
        batch_id = request.form.get('batch_id')
        batch = UploadBatch.query.get(batch_id)
        if batch:
            db.session.execute(applicant_upload.delete().where(applicant_upload.c.upload_batch_id == batch.id))
            Called.query.filter_by(upload_batch_id=batch.id).delete()
            Passed.query.filter_by(upload_batch_id=batch.id).delete()
            db.session.delete(batch)
            db.session.commit()
            flash(f'Batch {batch.filename} deleted.', 'success')
        else:
            flash('Batch not found.', 'danger')
    elif action == 'clear_category':
        category = request.form.get('category')
        if category == 'applicant':
            db.session.execute(applicant_upload.delete())
            Called.query.delete()
            Passed.query.delete()
            Applicant.query.delete()
            UploadBatch.query.delete()
            db.session.commit()
            flash('All applicant data cleared.', 'success')
        elif category == 'called':
            Called.query.delete()
            Applicant.query.update({Applicant.is_called: False})
            db.session.commit()
            flash('Called records cleared.', 'success')
        elif category == 'passed':
            Passed.query.delete()
            Applicant.query.update({Applicant.is_passed: False})
            db.session.commit()
            flash('Passed records cleared.', 'success')
    elif action == 'reset_all':
        db.drop_all()
        db.create_all()
        flash('Database reset to empty.', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=False)   # debug must be False in production

