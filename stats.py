from models import db, Applicant
from sqlalchemy import func

class StatsGenerator:
    @staticmethod
    def get_dashboard_stats():
        """Quick stats for dashboard."""
        total_applicants = Applicant.query.count()
        unique_applicants = total_applicants
        called = Applicant.query.filter_by(is_called=True).count()
        passed = Applicant.query.filter_by(is_passed=True).count()
        return {
            'total_applicants': total_applicants,
            'unique_applicants': unique_applicants,
            'called': called,
            'passed': passed,
            'call_pass_ratio': f"{called}/{passed}" if passed else f"{called}/0"
        }

    @staticmethod
    def get_all_stats():
        """Comprehensive statistics."""
        stats = {}

        stats['total_applicants'] = Applicant.query.count()
        stats['called'] = Applicant.query.filter_by(is_called=True).count()
        stats['passed'] = Applicant.query.filter_by(is_passed=True).count()

        # By job position
        job_counts = db.session.query(Applicant.job_title, func.count(Applicant.id)).group_by(Applicant.job_title).all()
        stats['by_job'] = {job: count for job, count in job_counts if job}

        # By region
        region_counts = db.session.query(Applicant.region, func.count(Applicant.id)).group_by(Applicant.region).all()
        stats['by_region'] = {region: count for region, count in region_counts if region}

        # By gender
        gender_counts = db.session.query(Applicant.gender, func.count(Applicant.id)).group_by(Applicant.gender).all()
        stats['by_gender'] = {gender: count for gender, count in gender_counts if gender}

        # By education level
        edu_counts = db.session.query(Applicant.education_level, func.count(Applicant.id)).group_by(Applicant.education_level).all()
        stats['by_education'] = {edu: count for edu, count in edu_counts if edu}

        # Vacancy-wise summary
        vacancy_stats = []
        jobs = db.session.query(Applicant.job_title.distinct()).all()
        for (job,) in jobs:
            if not job:
                continue
            total = Applicant.query.filter_by(job_title=job).count()
            called = Applicant.query.filter_by(job_title=job, is_called=True).count()
            passed = Applicant.query.filter_by(job_title=job, is_passed=True).count()
            vacancy_stats.append({
                'job': job,
                'total': total,
                'called': called,
                'passed': passed
            })
        stats['vacancy_summary'] = vacancy_stats

        return stats