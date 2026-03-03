from models import Applicant
from sqlalchemy import and_

class Deduplicator:
    @staticmethod
    def find_duplicate(row):
        """
        Find an existing applicant based on phone number AND full name.
        Both must match (case‑insensitive, after cleaning) to be considered a duplicate.
        Returns the Applicant object if found, else None.
        """
        phone = row.get('ስልክ/ሞባይል')
        full_name = row.get('ሙሉ ስም')

        # Both phone and name must be present and non‑empty
        if not phone or not full_name:
            return None

        # Clean: phone already normalized to digits, name normalized to title case
        # Use case‑insensitive match for name (though normalized, but safe)
        applicant = Applicant.query.filter(
            and_(
                Applicant.phone == phone,
                Applicant.full_name.ilike(full_name)  # ilike for safety
            )
        ).first()

        return applicant