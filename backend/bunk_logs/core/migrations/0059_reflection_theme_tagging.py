"""Add the reflection theme-tagging tables (Growth Dashboard by Grade Level).

Purely additive -- two new tables, no existing table touched -- so the
previous code version keeps running unaffected while this applies.
"""
import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0058_classroom_challenge'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReflectionThemeTagging',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('taxonomy_version', models.CharField(help_text="Taxonomy version this row's tags were produced against.", max_length=16)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed_retryable', 'Failed (retrying)'), ('failed_terminal', 'Failed (terminal)')], db_index=True, default='pending', max_length=24)),
                ('model_id', models.CharField(blank=True, default='', help_text='Anthropic model that produced the tags, for reproducibility.', max_length=128)),
                ('attempt_count', models.PositiveSmallIntegerField(default=0)),
                ('tokens_used', models.PositiveIntegerField(default=0, help_text='Total input+output tokens reported by the Anthropic response.')),
                ('last_error', models.TextField(blank=True, default='', help_text='Exception message captured on the most recent failed attempt.')),
                ('celery_task_id', models.CharField(blank=True, default='', help_text='Currently-enqueued Celery task id, so re-tagging on edit can revoke the pending task before queueing a fresh one.', max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reflection_theme_taggings', to='core.organization')),
                ('reflection', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='theme_taggings', to='core.reflection')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ReflectionThemeTag',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('field_key', models.CharField(help_text='Template schema field key this tag was derived from.', max_length=100)),
                ('dashboard_role', models.CharField(help_text='One of open_concern / wins / improvements.', max_length=32)),
                ('theme_key', models.CharField(db_index=True, max_length=64)),
                ('grade_level', models.IntegerField(blank=True, help_text="Author's grade level at tag time; NULL when unknown.", null=True)),
                ('period_start', models.DateField(db_index=True, help_text='Copied from the reflection so date windowing needs no join.')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reflection_theme_tags', to='core.organization')),
                ('program', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reflection_theme_tags', to='core.program')),
                ('reflection', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='theme_tags', to='core.reflection')),
                ('tagging', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tags', to='core.reflectionthemetagging')),
            ],
            options={
                'ordering': ['theme_key'],
            },
        ),
        migrations.AddIndex(
            model_name='reflectionthemetagging',
            index=models.Index(fields=['organization', 'status'], name='core_reflec_organiz_a26c63_idx'),
        ),
        migrations.AddIndex(
            model_name='reflectionthemetagging',
            index=models.Index(fields=['status', 'created_at'], name='core_reflec_status_ee8d46_idx'),
        ),
        migrations.AddConstraint(
            model_name='reflectionthemetagging',
            constraint=models.UniqueConstraint(fields=('reflection', 'taxonomy_version'), name='uniq_theme_tagging_reflection_version'),
        ),
        migrations.AddIndex(
            model_name='reflectionthemetag',
            index=models.Index(fields=['organization', 'grade_level', 'theme_key'], name='core_reflec_organiz_cdf99b_idx'),
        ),
        migrations.AddIndex(
            model_name='reflectionthemetag',
            index=models.Index(fields=['program', 'period_start'], name='core_reflec_program_061ba0_idx'),
        ),
        migrations.AddConstraint(
            model_name='reflectionthemetag',
            constraint=models.UniqueConstraint(fields=('tagging', 'field_key', 'theme_key'), name='uniq_theme_tag_per_field'),
        ),
    ]
