# Generated by Django 5.1.5 on 2025-01-27 10:49

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('applications', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Document',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('document_type', models.CharField(choices=[('dti_sec_registration', 'DTI/SEC Registration'), ('business_permit', 'Business Permit'), ('lease_contract', 'Lease Contract'), ('fire_safety', 'Fire Safety Certificate'), ('sanitary_permit', 'Sanitary Permit'), ('barangay_clearance', 'Barangay Clearance'), ('other', 'Other')], max_length=50)),
                ('file', models.FileField(upload_to='documents/%Y/%m/%d/', validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])])),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('is_verified', models.BooleanField(default=False)),
                ('extracted_text', models.TextField(blank=True)),
                ('confidence_score', models.FloatField(default=0.0)),
                ('fraud_score', models.FloatField(default=0.0)),
                ('fraud_flags', models.JSONField(default=dict)),
                ('is_flagged', models.BooleanField(default=False)),
                ('validation_results', models.JSONField(default=dict)),
                ('is_valid', models.BooleanField(default=False)),
                ('application', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='applications.businessapplication')),
            ],
            options={
                'ordering': ['-uploaded_at'],
            },
        ),
        migrations.CreateModel(
            name='DocumentVersion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='documents/versions/%Y/%m/%d/', validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])])),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('version_number', models.IntegerField()),
                ('notes', models.TextField(blank=True)),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='documents.document')),
            ],
            options={
                'ordering': ['-version_number'],
            },
        ),
    ]
