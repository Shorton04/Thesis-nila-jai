# documents/utils/nlp_validation.py
import spacy
import re
from typing import Dict, List, Tuple


class NLPValidator:
    """Validates text fields using NLP."""

    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")

    def validate_business_name(self, name: str) -> Tuple[bool, str]:
        """
        Validate business name format and content.
        Returns (is_valid, error_message)
        """
        try:
            # Basic format validation
            if len(name) < 3:
                return False, "Business name is too short"

            if len(name) > 255:
                return False, "Business name is too long"

            # Check for invalid characters
            if not re.match("^[a-zA-Z0-9&'., -]+$", name):
                return False, "Business name contains invalid characters"

            # NLP analysis
            doc = self.nlp(name)

            # Check for sensitive terms
            if self._contains_sensitive_terms(doc):
                return False, "Business name contains restricted terms"

            return True, ""
        except Exception as e:
            print(f"Business Name Validation Error: {str(e)}")
            return False, "Validation error occurred"

    def validate_address(self, address: str) -> Tuple[bool, Dict]:
        """
        Validate and structure address information.
        Returns (is_valid, structured_address)
        """
        try:
            doc = self.nlp(address)

            # Extract address components
            components = {
                'street_number': None,
                'street_name': None,
                'city': None,
                'state': None,
                'postal_code': None
            }

            # Process tokens
            for ent in doc.ents:
                if ent.label_ == 'GPE':
                    if not components['city']:
                        components['city'] = ent.text
                    elif not components['state']:
                        components['state'] = ent.text

            # Extract postal code using regex
            postal_match = re.search(r'\b\d{5}\b', address)
            if postal_match:
                components['postal_code'] = postal_match.group()

            # Validate completeness
            required_fields = ['street_number', 'street_name', 'city']
            is_valid = all(components.get(field) for field in required_fields)

            return is_valid, components
        except Exception as e:
            print(f"Address Validation Error: {str(e)}")
            return False, {}
