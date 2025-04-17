from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def verification_status_badge(status):
    """
    Return a Bootstrap badge with appropriate color for verification status.
    """
    badges = {
        'pending': '<span class="badge badge-warning">Pending</span>',
        'verified': '<span class="badge badge-success">Verified</span>',
        'fraud': '<span class="badge badge-danger">Potential Fraud</span>',
        'rejected': '<span class="badge badge-danger">Rejected</span>'
    }

    return mark_safe(badges.get(status, '<span class="badge badge-secondary">Unknown</span>'))


@register.filter
def document_type_display(doc_type, document_types):
    """
    Return the display name for a document type.
    """
    for type_code, type_name in document_types:
        if type_code == doc_type:
            return type_name
    return doc_type


@register.filter
def format_percentage(value):
    """
    Format a float as a percentage with 2 decimal places.
    """
    if value is None:
        return '-'
    return f"{value:.2f}%"


@register.simple_tag
def document_requirement_status(application, doc_type, document_types):
    """
    Return the status of a required document for an application.
    """
    documents = application.documents.filter(document_type=doc_type)

    if not documents.exists():
        return mark_safe('<span class="badge badge-secondary">Not Uploaded</span>')

    # Get the latest document
    latest_doc = documents.order_by('-uploaded_at').first()

    return verification_status_badge(latest_doc.verification_status)