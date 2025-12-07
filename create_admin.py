#!/usr/bin/env python
"""
Script to create or update admin user.
Usage: python create_admin.py
"""
import os
import sys
from pathlib import Path

# Setup Django - use the same approach as manage.py
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils_site'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'utils_site.settings')

try:
    import django
    django.setup()
except ImportError as exc:
    raise ImportError(
        "Couldn't import Django. Are you sure it's installed and "
        "available on your PYTHONPATH environment variable? Did you "
        "forget to activate a virtual environment?"
    ) from exc

from django.contrib.auth import get_user_model

User = get_user_model()

def create_admin():
    username = 'admin'
    email = 'info@convertica.net'
    password = input('Enter password for admin user (or press Enter to generate random): ').strip()
    
    if not password:
        import secrets
        password = secrets.token_urlsafe(16)
        print(f'\nGenerated password: {password}')
        print('SAVE THIS PASSWORD SECURELY!\n')
    
    # Check if user exists
    user, created = User.objects.get_or_create(
        username=username,
        defaults={'email': email, 'is_staff': True, 'is_superuser': True}
    )
    
    if not created:
        # Update existing user
        user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()
        print(f'Updated existing user: {username}')
    else:
        user.set_password(password)
        user.save()
        print(f'Created new admin user: {username}')
    
    print(f'Username: {username}')
    print(f'Email: {email}')
    print(f'Password: {"[SET ABOVE]" if password else "[GENERATED]"}')
    
    # Get admin URL path from settings
    from django.conf import settings
    admin_path = getattr(settings, 'ADMIN_URL_PATH', 'admin')
    print(f'\nYou can now login at: /{admin_path}/')

if __name__ == '__main__':
    create_admin()

