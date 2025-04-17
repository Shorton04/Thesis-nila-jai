import re
import random


def validate_business_name(name):
    """
    Simulates NLP validation of business names.
    In a real system, this would use NLP libraries to check naming conventions.
    """
    # Check if the name matches common patterns
    if not name or len(name) < 3:
        return False, "Business name is too short"

    # Check for prohibited words
    prohibited_words = ['scam', 'illegal', 'fake']
    for word in prohibited_words:
        if word.lower() in name.lower():
            return False, f"Business name contains prohibited word: {word}"

    # Check for business name pattern
    valid_pattern = re.match(r'^[A-Za-z0-9\s\.\&\-\']+$', name)
    if not valid_pattern:
        return False, "Business name contains invalid characters"

    return True, "Business name is valid"


def validate_address(address):
    """
    Simulates NLP validation of addresses.
    In a real system, this would use NLP/geocoding to validate addresses.
    """
    # Check if address is empty
    if not address or len(address) < 5:
        return False, "Address is too short"

    # Check for address pattern (very basic check)
    if not re.search(r'\d+', address):  # Should contain at least one number
        return False, "Address should include a number"

    # Simulate geocoding validation
    confidence = random.uniform(0.7, 0.99)

    return confidence > 0.8, f"Address validation confidence: {confidence:.2f}"


def suggest_corrections(text, field_type):
    """
    Simulates NLP suggestions for corrections.
    In a real system, this would use NLP to suggest proper formatting.
    """
    suggestions = []

    if field_type == 'business_name':
        # Suggest proper capitalization
        words = text.split()
        capitalized = ' '.join([w.capitalize() for w in words])
        if capitalized != text:
            suggestions.append(capitalized)

        # Suggest common suffixes
        if not any(suffix in text for suffix in ['Inc.', 'LLC', 'Corp.', 'Co.']):
            suggestions.append(f"{text} Inc.")

    elif field_type == 'address':
        # Suggest proper street abbreviations
        for old, new in [('Street', 'St.'), ('Avenue', 'Ave.'), ('Road', 'Rd.')]:
            if old in text:
                suggestions.append(text.replace(old, new))

        # Ensure proper city formatting
        if ',' not in text:
            suggestions.append(f"{text}, City")

    return suggestions[:3]  # Return top 3 suggestions