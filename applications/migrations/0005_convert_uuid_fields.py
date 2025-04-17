from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('applications', '0004_businessapplication_is_released_and_more'),
        # Make sure this matches your previous migration
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            -- Add UUID extension
            CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

            -- First, temporarily disable the foreign key constraints
            ALTER TABLE applications_applicationrequirement DROP CONSTRAINT IF EXISTS applications_applica_application_id_060c23e0_fk_applicati;
            ALTER TABLE applications_applicationrevision DROP CONSTRAINT IF EXISTS applications_applica_application_id_7b0d098d_fk_applicati;
            ALTER TABLE applications_applicationassessment DROP CONSTRAINT IF EXISTS applications_applica_application_id_c8eb9c80_fk_applicati;
            ALTER TABLE applications_applicationactivity DROP CONSTRAINT IF EXISTS applications_applica_application_id_f95c1f17_fk_applicati;
            ALTER TABLE documents_document DROP CONSTRAINT IF EXISTS documents_document_application_id_7e26c646_fk_applicati;
            ALTER TABLE queuing_queueappointment DROP CONSTRAINT IF EXISTS queuing_queueappoin_application_id_a8d3d8fd_fk_applicati;

            -- Convert application_id columns in related tables to varchar
            ALTER TABLE applications_applicationrequirement ALTER COLUMN application_id TYPE varchar(36);
            ALTER TABLE applications_applicationrevision ALTER COLUMN application_id TYPE varchar(36);
            ALTER TABLE applications_applicationassessment ALTER COLUMN application_id TYPE varchar(36);
            ALTER TABLE applications_applicationactivity ALTER COLUMN application_id TYPE varchar(36);
            ALTER TABLE documents_document ALTER COLUMN application_id TYPE varchar(36);
            ALTER TABLE queuing_queueappointment ALTER COLUMN application_id TYPE varchar(36);

            -- Convert primary keys to varchar
            ALTER TABLE applications_businessapplication ALTER COLUMN id TYPE varchar(36);
            ALTER TABLE queuing_queueappointment ALTER COLUMN id TYPE varchar(36);
            ALTER TABLE documents_document ALTER COLUMN id TYPE varchar(36);

            -- Fill with proper UUIDs where needed
            UPDATE applications_businessapplication SET id = uuid_generate_v4() WHERE id IS NULL OR id = '';
            UPDATE queuing_queueappointment SET id = uuid_generate_v4() WHERE id IS NULL OR id = '';
            UPDATE documents_document SET id = uuid_generate_v4() WHERE id IS NULL OR id = '';

            -- Convert primary keys to UUID type
            ALTER TABLE applications_businessapplication ALTER COLUMN id TYPE uuid USING id::uuid;
            ALTER TABLE queuing_queueappointment ALTER COLUMN id TYPE uuid USING id::uuid;
            ALTER TABLE documents_document ALTER COLUMN id TYPE uuid USING id::uuid;

            -- Convert foreign keys to UUID type
            ALTER TABLE applications_applicationrequirement ALTER COLUMN application_id TYPE uuid USING application_id::uuid;
            ALTER TABLE applications_applicationrevision ALTER COLUMN application_id TYPE uuid USING application_id::uuid;
            ALTER TABLE applications_applicationassessment ALTER COLUMN application_id TYPE uuid USING application_id::uuid;
            ALTER TABLE applications_applicationactivity ALTER COLUMN application_id TYPE uuid USING application_id::uuid;
            ALTER TABLE documents_document ALTER COLUMN application_id TYPE uuid USING application_id::uuid;
            ALTER TABLE queuing_queueappointment ALTER COLUMN application_id TYPE uuid USING application_id::uuid;

            -- Re-establish foreign key constraints
            ALTER TABLE applications_applicationrequirement 
                ADD CONSTRAINT applications_applica_application_id_060c23e0_fk_applicati 
                FOREIGN KEY (application_id) REFERENCES applications_businessapplication(id);

            ALTER TABLE applications_applicationrevision 
                ADD CONSTRAINT applications_applica_application_id_7b0d098d_fk_applicati 
                FOREIGN KEY (application_id) REFERENCES applications_businessapplication(id);

            ALTER TABLE applications_applicationassessment 
                ADD CONSTRAINT applications_applica_application_id_c8eb9c80_fk_applicati 
                FOREIGN KEY (application_id) REFERENCES applications_businessapplication(id);

            ALTER TABLE applications_applicationactivity 
                ADD CONSTRAINT applications_applica_application_id_f95c1f17_fk_applicati 
                FOREIGN KEY (application_id) REFERENCES applications_businessapplication(id);

            ALTER TABLE documents_document 
                ADD CONSTRAINT documents_document_application_id_7e26c646_fk_applicati 
                FOREIGN KEY (application_id) REFERENCES applications_businessapplication(id);

            ALTER TABLE queuing_queueappointment 
                ADD CONSTRAINT queuing_queueappoin_application_id_a8d3d8fd_fk_applicati 
                FOREIGN KEY (application_id) REFERENCES applications_businessapplication(id);
            """,
            reverse_sql="""
            -- This would convert everything back to varchar if needed
            -- Disable constraints first
            ALTER TABLE applications_applicationrequirement DROP CONSTRAINT applications_applica_application_id_060c23e0_fk_applicati;
            ALTER TABLE applications_applicationrevision DROP CONSTRAINT applications_applica_application_id_7b0d098d_fk_applicati;
            ALTER TABLE applications_applicationassessment DROP CONSTRAINT applications_applica_application_id_c8eb9c80_fk_applicati;
            ALTER TABLE applications_applicationactivity DROP CONSTRAINT applications_applica_application_id_f95c1f17_fk_applicati;
            ALTER TABLE documents_document DROP CONSTRAINT documents_document_application_id_7e26c646_fk_applicati;
            ALTER TABLE queuing_queueappointment DROP CONSTRAINT queuing_queueappoin_application_id_a8d3d8fd_fk_applicati;

            -- Convert back to varchar
            ALTER TABLE applications_businessapplication ALTER COLUMN id TYPE varchar(36);
            ALTER TABLE queuing_queueappointment ALTER COLUMN id TYPE varchar(36);
            ALTER TABLE documents_document ALTER COLUMN id TYPE varchar(36);

            ALTER TABLE applications_applicationrequirement ALTER COLUMN application_id TYPE varchar(36);
            ALTER TABLE applications_applicationrevision ALTER COLUMN application_id TYPE varchar(36);
            ALTER TABLE applications_applicationassessment ALTER COLUMN application_id TYPE varchar(36);
            ALTER TABLE applications_applicationactivity ALTER COLUMN application_id TYPE varchar(36);
            ALTER TABLE documents_document ALTER COLUMN application_id TYPE varchar(36);
            ALTER TABLE queuing_queueappointment ALTER COLUMN application_id TYPE varchar(36);
            """
        )
    ]