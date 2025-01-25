# documents/utils/nlp_validation.py
import re
import json
import numpy as np
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.metrics.distance import edit_distance
import nltk
from datetime import datetime
import pandas as pd


class NLPValidator:
    def __init__(self):
        # Download required NLTK data
        try:
            nltk.data.find('tokenizers/punkt')
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('punkt')
            nltk.download('stopwords')

        self.stop_words = set(stopwords.words('english'))
        self.business_keywords = {'inc', 'corp', 'corporation', 'llc', 'ltd', 'limited', 'co', 'company'}

        # Registration number patterns
        self.registration_patterns = {
            'DTI': r'^(?:DTI-)?[0-9]{4}-[0-9]{6}$',
            'SEC': r'^(?:SEC-)?[A-Z][0-9]{4}-[0-9]{6}-[0-9]{3}$',
            'CDA': r'^(?:CDA-)?[0-9]{4}-[0-9]{4}-[A-Z]{2}$'
        }

    def validate_registration_number(self, number, reg_type='DTI'):
        """
        Validate registration number format based on type (DTI, SEC, or CDA).
        """
        validation = {
            'is_valid': True,
            'issues': [],
            'suggestions': []
        }

        # Remove any whitespace
        number = number.strip()

        # Check if registration type is supported
        if reg_type not in self.registration_patterns:
            validation['is_valid'] = False
            validation['issues'].append(f"Unsupported registration type: {reg_type}")
            return validation

        # Check format against pattern
        if not re.match(self.registration_patterns[reg_type], number):
            validation['is_valid'] = False
            validation['issues'].append(f"Invalid {reg_type} registration number format")

            # Add prefix suggestion if missing
            if not number.startswith(f"{reg_type}-"):
                validation['suggestions'].append(f"Add '{reg_type}-' prefix")

            # Format suggestion based on type
            if reg_type == 'DTI':
                validation['suggestions'].append("Format should be: DTI-YYYY-XXXXXX")
            elif reg_type == 'SEC':
                validation['suggestions'].append("Format should be: SEC-AXXXX-XXXXXX-XXX")
            elif reg_type == 'CDA':
                validation['suggestions'].append("Format should be: CDA-YYYY-XXXX-AA")

        # Check year in registration number
        if reg_type in ['DTI', 'CDA']:
            year_match = re.search(r'(\d{4})', number)
            if year_match:
                year = int(year_match.group(1))
                current_year = datetime.now().year
                if year > current_year:
                    validation['is_valid'] = False
                    validation['issues'].append("Registration year cannot be in the future")
                elif year < 1900:
                    validation['is_valid'] = False
                    validation['issues'].append("Invalid registration year")

        return validation

    def validate_capitalization(self, amount):
        """
        Validate business capitalization amount.
        """
        validation = {
            'is_valid': True,
            'issues': [],
            'suggestions': []
        }

        try:
            # Convert to float if string
            if isinstance(amount, str):
                amount = float(amount.replace(',', ''))

            # Check minimum capitalization
            if amount < 5000:  # Example minimum threshold
                validation['is_valid'] = False
                validation['issues'].append("Capitalization amount is below minimum requirement")

            # Check for reasonable maximum
            if amount > 1000000000:  # Example maximum threshold
                validation['issues'].append("Unusually high capitalization amount - please verify")

            # Format suggestion
            validation['suggestions'].append(f"Suggested format: {'{:,.2f}'.format(amount)}")

        except ValueError:
            validation['is_valid'] = False
            validation['issues'].append("Invalid capitalization amount format")

        return validation

    def validate_business_activity(self, activity, line_of_business):
        """
        Validate business activity and line of business.
        """
        validation = {
            'is_valid': True,
            'issues': [],
            'suggestions': []
        }

        # Load predefined business activities and PSIC codes
        psic_codes = self.load_psic_codes()

        # Check against PSIC codes
        matched_codes = []
        for code, description in psic_codes.items():
            if line_of_business.lower() in description.lower():
                matched_codes.append(code)

        if not matched_codes:
            validation['issues'].append("Business activity does not match any standard PSIC code")
            # Find closest matches
            closest_matches = self.find_closest_matches(line_of_business, psic_codes.values())
            if closest_matches:
                validation['suggestions'].extend([
                    f"Did you mean: {match}" for match in closest_matches[:3]
                ])

        # Validate activity description
        min_words = 5
        max_words = 50
        words = word_tokenize(activity)

        if len(words) < min_words:
            validation['issues'].append("Business activity description is too brief")
        elif len(words) > max_words:
            validation['issues'].append("Business activity description is too long")

        return validation

    def validate_business_area(self, area, business_type):
        """
        Validate business area based on business type.
        """
        validation = {
            'is_valid': True,
            'issues': [],
            'suggestions': []
        }

        try:
            area = float(area)

            # Minimum area requirements by business type
            min_areas = {
                'single': 20,  # 20 sq.m
                'partnership': 30,
                'corporation': 50,
                'cooperative': 40,
                'opc': 25
            }

            if business_type in min_areas:
                if area < min_areas[business_type]:
                    validation['is_valid'] = False
                    validation['issues'].append(
                        f"Business area is below minimum requirement of {min_areas[business_type]} sq.m "
                        f"for {business_type} business type"
                    )

            # Check for reasonable maximum
            if area > 10000:  # 10,000 sq.m
                validation['issues'].append("Unusually large business area - please verify")

        except ValueError:
            validation['is_valid'] = False
            validation['issues'].append("Invalid business area format")

        return validation

    def load_psic_codes(self):
        """
        Load Philippine Standard Industrial Classification codes.
        """
        # This would typically load from a JSON file or database
        # Simplified example
        return {
            'A': 'Agriculture, Forestry and Fishing',
            'B': 'Mining and Quarrying',
            'C': 'Manufacturing',
            'D': 'Electricity, Gas, Steam and Air Conditioning Supply',
            'E': 'Water Supply; Sewerage, Waste Management',
            'F': 'Construction',
            'G': 'Wholesale and Retail Trade',
            'H': 'Transportation and Storage',
            'I': 'Accommodation and Food Service Activities',
            'J': 'Information and Communication',
            'K': 'Financial and Insurance Activities',
            'L': 'Real Estate Activities',
            'M': 'Professional, Scientific and Technical Activities',
            'N': 'Administrative and Support Service Activities',
            'O': 'Public Administration and Defense',
            'P': 'Education',
            'Q': 'Human Health and Social Work Activities',
            'R': 'Arts, Entertainment and Recreation',
            'S': 'Other Service Activities'
        }

    def find_closest_matches(self, query, choices, n=3):
        """
        Find the closest matching strings using Levenshtein distance.
        """
        distances = [(choice, edit_distance(query.lower(), choice.lower()))
                     for choice in choices]
        return [x[0] for x in sorted(distances, key=lambda x: x[1])[:n]]

    def validate_all_fields(self, data):
        """
        Validate all fields in a business permit application.
        """
        validation_results = {
            'is_valid': True,
            'fields': {},
            'overall_issues': []
        }

        # Validate business name
        validation_results['fields']['business_name'] = self.validate_business_name(
            data.get('business_name', '')
        )

        # Validate address
        validation_results['fields']['address'] = self.validate_address(
            data.get('business_address', '')
        )

        # Validate contact info
        validation_results['fields']['phone'] = self.validate_contact_number(
            data.get('telephone', '')
        )
        validation_results['fields']['email'] = self.validate_email(
            data.get('email', '')
        )

        # Validate registration
        validation_results['fields']['registration'] = self.validate_registration_number(
            data.get('registration_number', ''),
            data.get('registration_type', 'DTI')
        )

        # Validate business details
        validation_results['fields']['capitalization'] = self.validate_capitalization(
            data.get('capitalization', 0)
        )
        validation_results['fields']['business_area'] = self.validate_business_area(
            data.get('business_area', 0),
            data.get('business_type', '')
        )
        validation_results['fields']['business_activity'] = self.validate_business_activity(
            data.get('business_activity', ''),
            data.get('line_of_business', '')
        )

        # Check overall validity
        validation_results['is_valid'] = all(
            field['is_valid']
            for field in validation_results['fields'].values()
            if 'is_valid' in field
        )

        # Collect all issues
        for field_name, field_validation in validation_results['fields'].items():
            if field_validation.get('issues'):
                validation_results['overall_issues'].extend([
                    f"{field_name}: {issue}"
                    for issue in field_validation['issues']
                ])

        return validation_results