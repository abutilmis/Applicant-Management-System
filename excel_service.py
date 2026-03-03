import pandas as pd
import re

class ExcelService:
    # Canonical column names (as used in the database)
    CANONICAL_COLUMNS = [
        'ተራ ቁ', 'ሙሉ ስም', 'የሰራተኛ መለያ ቁጥር', 'ዕድሜ', 'ጾታ',
        'ነዋሪ የሆኑበት ክልል', 'የሥራ ልምድ ዓመት፡', 'ስልክ/ሞባይል',
        'አማራጭ ስልክ ቁጥር', 'ፓስፖርት', 'የስራ መደብ', 'የትምህርት ደረጃ',
        'የሰለጠኑበት ትምህርት ዘርፍ:', 'የስራ ልምድ', 'የትምህርት ማስረጃ',
        'CV ያስገቡ', 'ፓስፖርትፋይል', 'Submission ID',
        'Submission Create Date', 'Submission Status'
    ]

    # Mapping from possible variations (English, Amharic, abbreviations) to canonical name
    COLUMN_MAPPING = {
        'ተራ ቁ': ['ተራ ቁ', 'ተራቁ', 'ተራ ቁጥር', 'serial', 's.no', 'no', '#', 'number'],
        'ሙሉ ስም': ['ሙሉ ስም', 'ሙሉስም', 'ስም', 'full name', 'name', 'fullname', 'full_name'],
        'የሰራተኛ መለያ ቁጥር': ['የሰራተኛ መለያ ቁጥር', 'መለያ ቁጥር', 'labor id', 'labour id', 'employee id', 'id', 'labor_id'],
        'ዕድሜ': ['ዕድሜ', 'እድሜ', 'age', 'years', 'age(years)'],
        'ጾታ': ['ጾታ', 'ሴት/ወንድ', 'gender', 'sex'],
        'ነዋሪ የሆኑበት ክልል': ['ነዋሪ የሆኑበት ክልል', 'ክልል', 'region', 'የክልል'],
        'የሥራ ልምድ ዓመት፡': ['የሥራ ልምድ ዓመት፡', 'የሥራ ልምድ', 'experience years', 'experience(years)', 'work experience'],
        'ስልክ/ሞባይል': ['ስልክ/ሞባይል', 'ስልክ', 'phone', 'mobile', 'telephone', 'phone number'],
        'አማራጭ ስልክ ቁጥር': ['አማራጭ ስልክ ቁጥር', 'አማራጭ ስልክ', 'alt phone', 'alternative phone', 'secondary phone'],
        'ፓስፖርት': ['ፓስፖርት', 'passport', 'passport no'],
        'የስራ መደብ': ['የስራ መደብ', 'ስራ', 'job title', 'job', 'position'],
        'የትምህርት ደረጃ': ['የትምህርት ደረጃ', 'education level', 'edu level', 'qualification'],
        'የሰለጠኑበት ትምህርት ዘርፍ:': ['የሰለጠኑበት ትምህርት ዘርፍ:', 'field of study', 'major', 'subject', 'ዘርፍ'],
        'የስራ ልምድ': ['የስራ ልምድ', 'experience description', 'work history', 'job experience'],
        'የትምህርት ማስረጃ': ['የትምህርት ማስረጃ', 'education document', 'certificate', 'diploma'],
        'CV ያስገቡ': ['CV ያስገቡ', 'cv', 'resume', 'curriculum vitae'],
        'ፓስፖርትፋይል': ['ፓስፖርትፋይል', 'passport file', 'passport copy'],
        'Submission ID': ['Submission ID', 'submission id', 'sub id', 'application id'],
        'Submission Create Date': ['Submission Create Date', 'submission date', 'apply date', 'date'],
        'Submission Status': ['Submission Status', 'status', 'submission status', 'app status']
    }

    # Common placeholder strings that should be treated as null
    PLACEHOLDERS = {
        'n/a', 'na', 'N/A', 'NA', 'null', 'NULL', 'none', 'None', 'NONE',
        '-', '--', '?', '??', 'unknown', 'Unknown', ' ', '', 'nil', 'Nil'
    }

    @staticmethod
    def normalize_columns(df):
        """
        Rename DataFrame columns to canonical names using fuzzy matching.
        Returns the DataFrame with renamed columns.
        """
        # Clean column names: strip whitespace
        df.columns = df.columns.str.strip()

        # Build a lookup dictionary: for each possible variation (normalized), store canonical name
        lookup = {}
        for canonical, variations in ExcelService.COLUMN_MAPPING.items():
            for var in variations:
                # Normalize: remove punctuation, lowercase, strip
                norm = re.sub(r'[^\w]', '', var).lower()
                lookup[norm] = canonical
                # Also store the original variation (with punctuation) for exact matches
                lookup[var] = canonical

        # Map actual column names
        rename_map = {}
        for col in df.columns:
            if col in lookup:
                rename_map[col] = lookup[col]
                continue

            # Try normalized version of column name
            col_norm = re.sub(r'[^\w]', '', col).lower()
            if col_norm in lookup:
                rename_map[col] = lookup[col_norm]
                continue

            # Try partial matching (if one contains the other)
            for pattern, canonical in lookup.items():
                if pattern in col_norm or col_norm in pattern:
                    rename_map[col] = canonical
                    break

        df.rename(columns=rename_map, inplace=True)
        return df

    @staticmethod
    def clean_value(value):
        """Convert a single value: strip, replace placeholders with None."""
        if pd.isna(value):
            return None
        if isinstance(value, str):
            value = value.strip()
            # If the value is a known placeholder, return None
            if value.lower() in [p.lower() for p in ExcelService.PLACEHOLDERS]:
                return None
        return value

    @staticmethod
    def safe_convert_to_int(value):
        """Convert to int if possible, else return None."""
        value = ExcelService.clean_value(value)
        if value is None:
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def safe_convert_to_float(value):
        """Convert to float if possible, else return None."""
        value = ExcelService.clean_value(value)
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def clean_dataframe(df):
        """Clean and normalize all rows in the dataframe."""
        # Normalize column names
        df = ExcelService.normalize_columns(df)

        # Apply cleaning to all object (string) columns
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].apply(ExcelService.clean_value)

        # Normalize phone numbers (only if not None)
        if 'ስልክ/ሞባይል' in df.columns:
            df['ስልክ/ሞባይል'] = df['ስልክ/ሞባይል'].apply(
                lambda x: ExcelService.normalize_phone(x) if x is not None else None
            )
        if 'አማራጭ ስልክ ቁጥር' in df.columns:
            df['አማራጭ ስልክ ቁጥር'] = df['አማራጭ ስልክ ቁጥር'].apply(
                lambda x: ExcelService.normalize_phone(x) if x is not None else None
            )

        # Normalize names
        if 'ሙሉ ስም' in df.columns:
            df['ሙሉ ስም'] = df['ሙሉ ስም'].apply(
                lambda x: ExcelService.normalize_name(x) if x is not None else None
            )

        # Convert numeric fields safely
        if 'ዕድሜ' in df.columns:
            df['ዕድሜ'] = df['ዕድሜ'].apply(ExcelService.safe_convert_to_int)
        if 'የሥራ ልምድ ዓመት፡' in df.columns:
            df['የሥራ ልምድ ዓመት፡'] = df['የሥራ ልምድ ዓመት፡'].apply(ExcelService.safe_convert_to_float)

        return df

    @staticmethod
    def clean_row(row):
        """Clean a single row (dictionary) – used for called/passed matching."""
        cleaned = {}
        for k, v in row.items():
            v = ExcelService.clean_value(v)
            if k in ('ስልክ/ሞባይል', 'አማራጭ ስልክ ቁጥር') and v is not None:
                v = ExcelService.normalize_phone(v)
            if k == 'ሙሉ ስም' and v is not None:
                v = ExcelService.normalize_name(v)
            cleaned[k] = v
        return cleaned

    @staticmethod
    def normalize_phone(phone):
        if not phone:
            return None
        phone = str(phone).strip()
        digits = re.sub(r'\D', '', phone)
        if phone.startswith('+'):
            return '+' + digits
        return digits

    @staticmethod
    def normalize_name(name):
        if not name:
            return None
        name = str(name).strip()
        return name.title()

    @staticmethod
    def applicants_to_dataframe(applicants):
        """Convert list of Applicant objects to DataFrame with original column names."""
        data = []
        for app in applicants:
            data.append({
                'ተራ ቁ': app.serial,
                'ሙሉ ስም': app.full_name,
                'የሰራተኛ መለያ ቁጥር': app.labor_id,
                'ዕድሜ': app.age,
                'ጾታ': app.gender,
                'ነዋሪ የሆኑበት ክልል': app.region,
                'የሥራ ልምድ ዓመት፡': app.experience_years,
                'ስልክ/ሞባይል': app.phone,
                'አማራጭ ስልክ ቁጥር': app.alt_phone,
                'ፓስፖርት': app.passport,
                'የስራ መደብ': app.job_title,
                'የትምህርት ደረጃ': app.education_level,
                'የሰለጠኑበት ትምህርት ዘርፍ:': app.education_field,
                'የስራ ልምድ': app.experience_description,
                'የትምህርት ማስረጃ': app.education_document,
                'CV ያስገቡ': app.cv_file,
                'ፓስፖርትፋይል': app.passport_file,
                'Submission ID': app.submission_id,
                'Submission Create Date': app.submission_create_date,
                'Submission Status': app.submission_status
            })
        return pd.DataFrame(data)