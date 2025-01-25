# documents/services/document_workflow.py

import logging
import re
from typing import Dict, Any, List, Optional
from django.conf import settings
from django.core.files.base import File
from django.utils import timezone
from django.db import transaction
from ..models import Document, DocumentVersion, BusinessApplication
from .document_verification import DocumentVerificationService
from .document_verification_utils import DocumentVerificationUtils
from .notification_service import NotificationService

logger = logging.getLogger(__name__)


class DocumentWorkflowService:
    """
    Service responsible for orchestrating the complete document processing workflow,
    including verification, versioning, and notification management.
    """

    def __init__(self):
        self.verification_service = DocumentVerificationService()
        self.notification_service = NotificationService()
        self.utils = DocumentVerificationUtils()

    @transaction.atomic
    def process_new_document(self, document: Document) -> Dict[str, Any]:
        """
        Process a newly uploaded document through the complete workflow.
        """
        try:
            workflow_results = {
                'success': True,
                'document_id': document.id,
                'workflow_status': 'initiated',
                'stages': {},
                'final_status': None,
                'issues': [],
                'next_actions': []
            }

            # Stage 1: Initial Validation
            workflow_results['stages']['initial_validation'] = \
                self._perform_initial_validation(document)

            if not workflow_results['stages']['initial_validation']['success']:
                workflow_results['success'] = False
                workflow_results['workflow_status'] = 'failed_validation'
                return workflow_results

            # Stage 2: Document Verification
            workflow_results['stages']['verification'] = \
                self._perform_verification(document)

            if not workflow_results['stages']['verification']['success']:
                workflow_results['success'] = False
                workflow_results['workflow_status'] = 'failed_verification'
                return workflow_results

            # Stage 3: Consistency Check
            workflow_results['stages']['consistency_check'] = \
                self._perform_consistency_check(document)

            # Stage 4: Risk Assessment
            workflow_results['stages']['risk_assessment'] = \
                self._perform_risk_assessment(document, workflow_results)

            # Determine final workflow status
            workflow_results['final_status'] = self._determine_final_status(workflow_results)
            workflow_results['next_actions'] = self._determine_next_actions(workflow_results)

            # Update document status
            self._update_document_status(document, workflow_results)

            # Send notifications
            self._send_workflow_notifications(document, workflow_results)

            return workflow_results

        except Exception as e:
            logger.error(f"Document workflow error: {str(e)}")
            return {
                'success': False,
                'document_id': document.id,
                'workflow_status': 'error',
                'error': str(e)
            }

    def _perform_initial_validation(self, document: Document) -> Dict[str, Any]:
        """
        Perform initial validation checks on the document.
        """
        validation_results = {
            'success': True,
            'issues': []
        }

        try:
            # Get document requirements
            requirements = self.utils.get_verification_requirements(document.document_type)

            # Validate file type
            file_extension = document.file.name.split('.')[-1].lower()
            if file_extension not in requirements['allowed_file_types']:
                validation_results['success'] = False
                validation_results['issues'].append(
                    f"Invalid file type: {file_extension}. Allowed types: "
                    f"{', '.join(requirements['allowed_file_types'])}"
                )

            # Validate file size
            if document.file.size > requirements['max_file_size']:
                validation_results['success'] = False
                validation_results['issues'].append(
                    f"File size exceeds maximum allowed size of "
                    f"{requirements['max_file_size'] / (1024 * 1024):.1f}MB"
                )

            # Additional custom validations
            custom_validations = self._perform_custom_validations(document, requirements)
            if not custom_validations['success']:
                validation_results['success'] = False
                validation_results['issues'].extend(custom_validations['issues'])

            return validation_results

        except Exception as e:
            logger.error(f"Initial validation error: {str(e)}")
            return {
                'success': False,
                'issues': [f"Validation error: {str(e)}"]
            }

    def _perform_verification(self, document: Document) -> Dict[str, Any]:
        """
        Perform comprehensive document verification.
        """
        try:
            # Execute verification process
            verification_results = self.verification_service.verify_document(document)

            # Process verification results
            processed_results = {'success': verification_results['success'],
                                 'status': verification_results['verification_status'],
                                 'confidence_score': verification_results.get('ocr_results', {}).get('confidence', 0),
                                 'fraud_score': verification_results.get('fraud_detection', {}).get('fraud_score', 0),
                                 'extracted_data': verification_results.get('extracted_data', {}),
                                 'issues': verification_results.get('issues', []), 'metadata': {
                                 'verification_date': timezone.now(),
                                 'verification_method': 'automated',
                                 'verification_version': settings.VERIFICATION_ENGINE_VERSION
                }}

            # Add verification metadata

            return processed_results

        except Exception as e:
            logger.error(f"Verification process error: {str(e)}")
            return {
                'success': False,
                'status': 'error',
                'issues': [f"Verification error: {str(e)}"]
            }

    def _perform_consistency_check(self, document: Document) -> Dict[str, Any]:
        """
        Check consistency with other documents in the same application.
        """
        try:
            # Get all documents from the same application
            application_documents = Document.objects.filter(
                application=document.application
            ).exclude(id=document.id)

            if not application_documents.exists():
                return {
                    'success': True,
                    'status': 'no_related_documents',
                    'consistency_score': 1.0
                }

            # Prepare documents for consistency check
            documents_data = []
            for doc in application_documents:
                doc_data = {
                    'document_type': doc.document_type,
                    'extracted_data': doc.extracted_text,
                    'metadata': doc.metadata
                }
                documents_data.append(doc_data)

            # Add current document
            documents_data.append({
                'document_type': document.document_type,
                'extracted_data': document.extracted_text,
                'metadata': document.metadata
            })

            # Perform consistency validation
            consistency_results = self.utils.validate_document_consistency(documents_data)

            return {
                'success': consistency_results['is_consistent'],
                'status': 'consistent' if consistency_results['is_consistent'] else 'inconsistent',
                'consistency_score': 1.0 - consistency_results['risk_score'],
                'inconsistencies': consistency_results.get('inconsistencies', [])
            }

        except Exception as e:
            logger.error(f"Consistency check error: {str(e)}")
            return {
                'success': False,
                'status': 'error',
                'consistency_score': 0.0,
                'error': str(e)
            }

    def _perform_risk_assessment(self, document: Document,
                                 workflow_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform comprehensive risk assessment based on all workflow stages.
        """
        try:
            risk_assessment = {
                'overall_risk_score': 0.0,
                'risk_factors': [],
                'recommendations': []
            }

            # Calculate risk scores from different stages
            verification_risk = self._calculate_verification_risk(
                workflow_results['stages']['verification']
            )
            consistency_risk = self._calculate_consistency_risk(
                workflow_results['stages']['consistency_check']
            )
            historical_risk = self._calculate_historical_risk(document)

            # Combine risk scores
            risk_weights = {
                'verification': 0.4,
                'consistency': 0.3,
                'historical': 0.3
            }

            overall_risk = (
                    verification_risk * risk_weights['verification'] +
                    consistency_risk * risk_weights['consistency'] +
                    historical_risk * risk_weights['historical']
            )

            risk_assessment['overall_risk_score'] = min(overall_risk, 1.0)

            # Determine risk factors
            if verification_risk > 0.7:
                risk_assessment['risk_factors'].append({
                    'type': 'verification',
                    'severity': 'high',
                    'description': 'High verification risk detected'
                })

            if consistency_risk > 0.7:
                risk_assessment['risk_factors'].append({
                    'type': 'consistency',
                    'severity': 'high',
                    'description': 'Significant inconsistencies with other documents'
                })

            if historical_risk > 0.7:
                risk_assessment['risk_factors'].append({
                    'type': 'historical',
                    'severity': 'high',
                    'description': 'Concerning patterns in document history'
                })

            # Generate recommendations
            risk_assessment['recommendations'] = \
                self._generate_risk_recommendations(risk_assessment)

            return risk_assessment

        except Exception as e:
            logger.error(f"Risk assessment error: {str(e)}")
            return {
                'overall_risk_score': 1.0,
                'risk_factors': [{
                    'type': 'error',
                    'severity': 'high',
                    'description': f"Risk assessment error: {str(e)}"
                }],
                'recommendations': ['Manual review required due to risk assessment error']
            }

    def _calculate_verification_risk(self, verification_results: Dict[str, Any]) -> float:
        """
        Calculate risk score based on verification results.
        """
        risk_score = 0.0

        # Consider confidence score
        confidence = verification_results.get('confidence_score', 0)
        if confidence < settings.MIN_OCR_CONFIDENCE:
            risk_score += 0.3

        # Consider fraud score
        fraud_score = verification_results.get('fraud_score', 0)
        risk_score += fraud_score * 0.4

        # Consider number of issues
        issues_count = len(verification_results.get('issues', []))
        risk_score += min(issues_count * 0.1, 0.3)

        return min(risk_score, 1.0)

    def _calculate_consistency_risk(self, consistency_results: Dict[str, Any]) -> float:
        """
        Calculate risk score based on consistency check results.
        """
        if not consistency_results['success']:
            return 1.0

        return 1.0 - consistency_results.get('consistency_score', 0)

    def _calculate_historical_risk(self, document: Document) -> float:
        """
        Calculate risk score based on document history.
        """
        try:
            history = self.utils.analyze_verification_history(document.id)

            risk_score = 0.0

            # Consider failure rate
            risk_score += history.get('failure_rate', 0) * 0.4

            # Consider number of risk patterns
            risk_patterns = len(history.get('risk_patterns', []))
            risk_score += min(risk_patterns * 0.2, 0.4)

            # Consider verification attempts
            attempts = history.get('verification_attempts', 0)
            if attempts > 3:
                risk_score += 0.2

            return min(risk_score, 1.0)

        except Exception as e:
            logger.error(f"Historical risk calculation error: {str(e)}")
            return 0.5  # Default to medium risk on error

    def _determine_final_status(self, workflow_results: Dict[str, Any]) -> str:
        """
        Determine final workflow status based on all results.
        """
        if not workflow_results['success']:
            return 'failed'

        verification_status = workflow_results['stages']['verification']['status']
        risk_score = workflow_results['stages']['risk_assessment']['overall_risk_score']

        if verification_status == 'verified' and risk_score < 0.3:
            return 'approved'
        elif risk_score > 0.7:
            return 'rejected'
        else:
            return 'needs_review'

    def _determine_next_actions(self, workflow_results: Dict[str, Any]) -> List[str]:
        """
        Determine required next actions based on workflow results.
        """
        next_actions = []
        final_status = workflow_results['final_status']

        if final_status == 'approved':
            next_actions.append("Document has been approved - no further action required")
        elif final_status == 'rejected':
            next_actions.extend([
                "Document has been rejected",
                "Please submit a new document addressing the identified issues",
                "Contact support if you need assistance"
            ])
        elif final_status == 'needs_review':
            next_actions.extend([
                "Document requires manual review",
                "A verification officer will review your document",
                "You will be notified once the review is complete"
            ])

        # Add specific actions based on issues
        for stage, results in workflow_results['stages'].items():
            if isinstance(results, dict) and 'issues' in results:
                for issue in results['issues']:
                    next_actions.append(f"Address {stage} issue: {issue}")

        return next_actions

    def _update_document_status(self, document: Document,
                                workflow_results: Dict[str, Any]) -> None:
        """
        Update document status based on workflow results.
        """
        try:
            with transaction.atomic():
                document.status = workflow_results['final_status']
                document.last_processed = timezone.now()
                document.processing_results = workflow_results
                document.save()

                # Create document version if needed
                if workflow_results['final_status'] != 'approved':
                    DocumentVersion.objects.create(
                        document=document,
                        file=document.file,
                        version_number=self._get_next_version_number(document),
                        processing_results=workflow_results
                    )

        except Exception as e:
            logger.error(f"Error updating document status: {str(e)}")
            raise

    def _send_workflow_notifications(self, document: Document,
                                     workflow_results: Dict[str, Any]) -> None:
        """
        Send appropriate notifications based on workflow results.
        """
        try:
            notification_data = {
                'document_type': document.get_document_type_display(),
                'workflow_status': workflow_results['final_status'],
                'issues': workflow_results.get('issues', []),
                'next_actions': workflow_results['next_actions']
            }

            self.notification_service.notify_verification_results(
                document, notification_data
            )

        except Exception as e:
            logger.error(f"Notification error: {str(e)}")
            # Don't raise the exception as notification failure shouldn't fail the workflow

    def _get_next_version_number(self, document: Document) -> int:
        """
        Get the next version number for a document.
        """
        latest_version = DocumentVersion.objects.filter(document=document) \
            .order_by('-version_number').first()
        return (latest_version.version_number + 1) if latest_version else 1

    def process_document_update(self, document: Document,
                                new_file: File) -> Dict[str, Any]:
        """
        Process an updated version of an existing document.
        """
        try:
            update_results = {
                'success': True,
                'document_id': document.id,
                'version_number': None,
                'workflow_results': None,
                'comparison_results': None,
                'issues': []
            }

            # Store original content for comparison
            original_content = {
                'extracted_text': document.extracted_text,
                'metadata': document.metadata
            }

            # Create new version
            new_version = DocumentVersion.objects.create(
                document=document,
                file=new_file,
                version_number=self._get_next_version_number(document)
            )
            update_results['version_number'] = new_version.version_number

            # Process new version through workflow
            workflow_results = self.process_new_document(document)
            update_results['workflow_results'] = workflow_results

            # Compare versions
            comparison_results = self.utils.compare_document_versions(
                original_content,
                {
                    'extracted_text': document.extracted_text,
                    'metadata': document.metadata
                }
            )
            update_results['comparison_results'] = comparison_results

            # Handle significant changes
            if comparison_results['risk_level'] == 'high':
                update_results['issues'].append(
                    "Significant changes detected - manual review required"
                )
                document.status = 'needs_review'
                document.save()

            return update_results

        except Exception as e:
            logger.error(f"Document update error: {str(e)}")
            return {
                'success': False,
                'document_id': document.id,
                'error': str(e)
            }

    def process_document_batch(self, documents: List[Document]) -> Dict[str, Any]:
        """
        Process multiple documents in batch, maintaining consistency checks.
        """
        try:
            batch_results = {
                'success': True,
                'processed_count': 0,
                'results': [],
                'batch_issues': [],
                'consistency_check': None
            }

            # Process each document
            for document in documents:
                result = self.process_new_document(document)
                batch_results['results'].append({
                    'document_id': document.id,
                    'success': result['success'],
                    'status': result.get('final_status'),
                    'issues': result.get('issues', [])
                })

                if result['success']:
                    batch_results['processed_count'] += 1

            # Perform batch-level consistency check
            if batch_results['processed_count'] > 0:
                consistency_check = self._perform_batch_consistency_check(documents)
                batch_results['consistency_check'] = consistency_check

                if not consistency_check['is_consistent']:
                    batch_results['batch_issues'].extend(
                        consistency_check['inconsistencies']
                    )

            return batch_results

        except Exception as e:
            logger.error(f"Batch processing error: {str(e)}")
            return {
                'success': False,
                'processed_count': 0,
                'error': str(e)
            }

    def _perform_batch_consistency_check(self, documents: List[Document]) -> Dict[str, Any]:
        """
        Perform consistency validation across a batch of documents.
        """
        try:
            # Prepare documents data for consistency check
            documents_data = []
            for doc in documents:
                doc_data = {
                    'document_type': doc.document_type,
                    'extracted_data': doc.extracted_text,
                    'metadata': doc.metadata
                }
                documents_data.append(doc_data)

            # Perform consistency validation
            return self.utils.validate_document_consistency(documents_data)

        except Exception as e:
            logger.error(f"Batch consistency check error: {str(e)}")
            return {
                'is_consistent': False,
                'error': str(e)
            }

    def _perform_custom_validations(self, document: Document,
                                    requirements: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform document type-specific custom validations.
        """
        validation_results = {
            'success': True,
            'issues': []
        }

        try:
            # Get document type specific validation rules
            validation_rules = requirements.get('validation_rules', {})

            for field, rules in validation_rules.items():
                field_value = getattr(document, field, None)
                if field_value:
                    # Date validations
                    if 'max_age_years' in rules:
                        max_age = timezone.now() - timezone.timedelta(
                            days=rules['max_age_years'] * 365
                        )
                        if field_value < max_age:
                            validation_results['success'] = False
                            validation_results['issues'].append(
                                f"{field} exceeds maximum age of {rules['max_age_years']} years"
                            )

                    if rules.get('no_future_dates') and field_value > timezone.now():
                        validation_results['success'] = False
                        validation_results['issues'].append(
                            f"{field} cannot be a future date"
                        )

                    # Format validations
                    if 'format' in rules:
                        if not re.match(rules['format'], str(field_value)):
                            validation_results['success'] = False
                            validation_results['issues'].append(
                                f"{field} does not match required format"
                            )

            return validation_results

        except Exception as e:
            logger.error(f"Custom validation error: {str(e)}")
            return {
                'success': False,
                'issues': [f"Validation error: {str(e)}"]
            }

    def _generate_risk_recommendations(self,
                                       risk_assessment: Dict[str, Any]) -> List[str]:
        """
        Generate specific recommendations based on risk assessment results.
        """
        recommendations = []
        risk_score = risk_assessment['overall_risk_score']

        if risk_score > 0.7:
            recommendations.extend([
                "Immediate manual review required",
                "Additional document verification recommended",
                "Consider requesting supporting documentation"
            ])
        elif risk_score > 0.4:
            recommendations.extend([
                "Standard manual review recommended",
                "Verify key information against external sources"
            ])

        # Add specific recommendations based on risk factors
        for factor in risk_assessment.get('risk_factors', []):
            if factor['type'] == 'verification':
                recommendations.append(
                    "Enhance document quality for better verification results"
                )
            elif factor['type'] == 'consistency':
                recommendations.append(
                    "Review and reconcile inconsistencies across documents"
                )
            elif factor['type'] == 'historical':
                recommendations.append(
                    "Review document history for pattern analysis"
                )

        return recommendations

    def reprocess_document(self, document: Document) -> Dict[str, Any]:
        """
        Reprocess an existing document through the workflow.
        """
        try:
            # Store original status
            original_status = document.status

            # Reset processing fields
            document.status = 'pending'
            document.last_processed = None
            document.processing_results = {}
            document.save()

            # Reprocess through workflow
            workflow_results = self.process_new_document(document)

            # Add reprocessing metadata
            workflow_results['reprocessing_metadata'] = {
                'original_status': original_status,
                'reprocessing_date': timezone.now(),
                'triggered_by': 'system'
            }

            return workflow_results

        except Exception as e:
            logger.error(f"Document reprocessing error: {str(e)}")
            return {
                'success': False,
                'document_id': document.id,
                'error': str(e)
            }