# documents/services/document_verification_utils.py

from typing import Dict, Any, List, Optional, Tuple
import hashlib
import os
import glob
import json
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


class DocumentVerificationUtils:
    """
    Utility methods for document verification processes.
    """

    @staticmethod
    def calculate_document_hash(content: bytes) -> str:
        """
        Calculate a secure hash of document content for integrity checking.
        """
        sha256_hash = hashlib.sha256()
        sha256_hash.update(content)
        return sha256_hash.hexdigest()

    @staticmethod
    def compare_document_versions(original_content: Dict[str, Any],
                                  new_content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare two versions of document content and identify differences.
        """
        comparison_results = {
            'has_changes': False,
            'changes': [],
            'risk_level': 'low'
        }

        try:
            # Compare each field in the contents
            for field in set(original_content.keys()) | set(new_content.keys()):
                original_value = original_content.get(field)
                new_value = new_content.get(field)

                if original_value != new_value:
                    comparison_results['has_changes'] = True
                    change = {
                        'field': field,
                        'original': original_value,
                        'new': new_value,
                        'change_type': 'modified' if field in original_content else 'added'
                    }

                    # Assess risk level for this change
                    risk_level = DocumentVerificationUtils.assess_change_risk(
                        field, original_value, new_value
                    )
                    change['risk_level'] = risk_level

                    comparison_results['changes'].append(change)

                    # Update overall risk level if necessary
                    if DocumentVerificationUtils.risk_hierarchy[risk_level] > \
                            DocumentVerificationUtils.risk_hierarchy[comparison_results['risk_level']]:
                        comparison_results['risk_level'] = risk_level

            return comparison_results

        except Exception as e:
            logger.error(f"Error comparing document versions: {str(e)}")
            return {
                'has_changes': True,
                'changes': [],
                'risk_level': 'high',
                'error': str(e)
            }

    risk_hierarchy = {
        'low': 1,
        'medium': 2,
        'high': 3
    }

    @staticmethod
    def assess_change_risk(field: str, original_value: Any, new_value: Any) -> str:
        """
        Assess the risk level of a specific change.
        """
        # High-risk fields that should rarely change
        high_risk_fields = {
            'registration_number', 'permit_number', 'business_type',
            'owner_name', 'tax_id'
        }

        # Medium-risk fields that may change but need verification
        medium_risk_fields = {
            'business_name', 'address', 'capital_amount',
            'business_activity', 'contact_number'
        }

        if field in high_risk_fields:
            return 'high'
        elif field in medium_risk_fields:
            return 'medium'
        return 'low'

    @staticmethod
    def validate_document_consistency(documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate consistency across multiple related documents.
        """
        consistency_results = {
            'is_consistent': True,
            'inconsistencies': [],
            'risk_score': 0.0
        }

        try:
            # Extract key information from all documents
            key_info = {}
            for doc in documents:
                doc_type = doc.get('document_type')
                extracted_data = doc.get('extracted_data', {})

                for field, value in extracted_data.items():
                    if field not in key_info:
                        key_info[field] = {}
                    key_info[field][doc_type] = value

            # Check for inconsistencies across documents
            for field, values in key_info.items():
                if len(values) > 1:
                    unique_values = set(str(v).lower() for v in values.values())
                    if len(unique_values) > 1:
                        consistency_results['is_consistent'] = False
                        consistency_results['inconsistencies'].append({
                            'field': field,
                            'values': values,
                            'severity': DocumentVerificationUtils.assess_change_risk(field, None, None)
                        })

            # Calculate risk score based on inconsistencies
            if consistency_results['inconsistencies']:
                severity_scores = {
                    'high': 1.0,
                    'medium': 0.6,
                    'low': 0.3
                }
                total_score = sum(
                    severity_scores[inc['severity']]
                    for inc in consistency_results['inconsistencies']
                )
                consistency_results['risk_score'] = min(1.0, total_score / len(documents))

            return consistency_results

        except Exception as e:
            logger.error(f"Error validating document consistency: {str(e)}")
            return {
                'is_consistent': False,
                'inconsistencies': [],
                'risk_score': 1.0,
                'error': str(e)
            }

    @staticmethod
    def analyze_verification_history(document_id: int,
                                     time_window: Optional[timedelta] = None) -> Dict[str, Any]:
        """
        Analyze verification history for a document over time.
        """
        if time_window is None:
            time_window = timedelta(days=90)  # Default to 90 days

        try:
            history_analysis = {
                'verification_attempts': 0,
                'failure_rate': 0.0,
                'common_issues': {},
                'risk_patterns': [],
                'last_verified': None
            }

            # Get verification history from storage
            results_dir = os.path.join(settings.MEDIA_ROOT, 'verification_results')
            pattern = f"verification_{document_id}_*.json"
            history_files = glob.glob(os.path.join(results_dir, pattern))

            cutoff_date = timezone.now() - time_window
            relevant_results = []

            for file_path in history_files:
                try:
                    with open(file_path, 'r') as f:
                        result = json.load(f)
                        result_date = datetime.fromisoformat(result['timestamp'])

                        if result_date >= cutoff_date:
                            relevant_results.append(result)
                except Exception as e:
                    logger.warning(f"Error reading verification history file: {str(e)}")
                    continue

            if relevant_results:
                # Sort by timestamp
                relevant_results.sort(key=lambda x: x['timestamp'])
                history_analysis['last_verified'] = relevant_results[-1]['timestamp']

                # Calculate statistics
                history_analysis['verification_attempts'] = len(relevant_results)

                failures = sum(1 for r in relevant_results
                               if r['results']['verification_status'] != 'verified')
                history_analysis['failure_rate'] = failures / len(relevant_results)

                # Analyze common issues
                for result in relevant_results:
                    for issue in result['results'].get('issues', []):
                        if issue in history_analysis['common_issues']:
                            history_analysis['common_issues'][issue] += 1
                        else:
                            history_analysis['common_issues'][issue] = 1

                # Identify risk patterns
                history_analysis['risk_patterns'] = \
                    DocumentVerificationUtils.identify_risk_patterns(relevant_results)

            return history_analysis

        except Exception as e:
            logger.error(f"Error analyzing verification history: {str(e)}")
            return {
                'error': str(e),
                'verification_attempts': 0,
                'failure_rate': 0.0,
                'common_issues': {},
                'risk_patterns': []
            }

    @staticmethod
    def identify_risk_patterns(verification_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Identify patterns that might indicate systematic risks.
        """
        risk_patterns = []

        try:
            # Look for repeated failures
            consecutive_failures = 0
            failure_threshold = 3

            for result in verification_results:
                if result['results']['verification_status'] != 'verified':
                    consecutive_failures += 1
                    if consecutive_failures >= failure_threshold:
                        risk_patterns.append({
                            'type': 'repeated_failures',
                            'count': consecutive_failures,
                            'severity': 'high',
                            'description': f'Document failed verification {consecutive_failures} times in a row'
                        })
                else:
                    consecutive_failures = 0

            # Check for oscillating verification status
            status_changes = sum(
                1 for i in range(1, len(verification_results))
                if verification_results[i]['results']['verification_status'] !=
                verification_results[i - 1]['results']['verification_status']
            )

            if status_changes >= 3:
                risk_patterns.append({
                    'type': 'inconsistent_verification',
                    'count': status_changes,
                    'severity': 'medium',
                    'description': 'Document verification status changes frequently'
                })

            # Check for patterns in fraud scores
            fraud_scores = [
                result['results'].get('fraud_detection', {}).get('fraud_score', 0)
                for result in verification_results
            ]

            if any(score > settings.FRAUD_DETECTION_THRESHOLD for score in fraud_scores):
                risk_patterns.append({
                    'type': 'high_fraud_scores',
                    'severity': 'high',
                    'description': 'Document has history of high fraud detection scores'
                })

            return risk_patterns

        except Exception as e:
            logger.error(f"Error identifying risk patterns: {str(e)}")
            return []

    @staticmethod
    def get_verification_requirements(document_type: str) -> Dict[str, Any]:
        """
        Get verification requirements for a specific document type.
        """
        try:
            # Cache key for requirements
            cache_key = f'verification_requirements_{document_type}'
            cached_requirements = cache.get(cache_key)

            if cached_requirements:
                return cached_requirements

            # Define base requirements
            requirements = {
                'required_fields': [],
                'field_formats': {},
                'validation_rules': {},
                'allowed_file_types': [],
                'max_file_size': 0
            }

            # Document-specific requirements
            if document_type == 'dti_sec_registration':
                requirements.update({
                    'required_fields': [
                        'registration_number',
                        'registration_date',
                        'business_name',
                        'business_type'
                    ],
                    'field_formats': {
                        'registration_number': r'^[A-Z0-9-]{5,15}$',
                        'registration_date': r'^\d{4}-\d{2}-\d{2}$'
                    },
                    'validation_rules': {
                        'registration_date': {
                            'max_age_years': 50,
                            'no_future_dates': True
                        }
                    },
                    'allowed_file_types': ['pdf', 'jpg', 'png'],
                    'max_file_size': 10 * 1024 * 1024  # 10MB
                })

            elif document_type == 'business_permit':
                requirements.update({
                    'required_fields': [
                        'permit_number',
                        'business_name',
                        'address',
                        'validity_date'
                    ],
                    'field_formats': {
                        'permit_number': r'^[A-Z0-9-]{8,12}$',
                        'validity_date': r'^\d{4}-\d{2}-\d{2}$'
                    },
                    'validation_rules': {
                        'validity_date': {
                            'must_be_future': True,
                            'max_validity_years': 1
                        }
                    },
                    'allowed_file_types': ['pdf', 'jpg', 'png'],
                    'max_file_size': 5 * 1024 * 1024  # 5MB
                })

            # Cache requirements for future use
            cache.set(cache_key, requirements, timeout=3600)  # Cache for 1 hour
            return requirements

        except Exception as e:
            logger.error(f"Error getting verification requirements: {str(e)}")
            return {}