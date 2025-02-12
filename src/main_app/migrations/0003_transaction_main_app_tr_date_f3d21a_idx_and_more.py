# Generated by Django 5.1.4 on 2025-02-01 07:05

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main_app', '0002_parserule_negate_amount'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['date'], name='main_app_tr_date_f3d21a_idx'),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['user', 'date'], name='main_app_tr_user_id_92a068_idx'),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['user', 'category'], name='main_app_tr_user_id_72fa7c_idx'),
        ),
    ]
