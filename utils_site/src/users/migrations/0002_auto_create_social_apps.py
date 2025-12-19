"""
Auto-create social applications for Google and Facebook
"""
from django.db import migrations
def create_social_apps(apps, _schema_editor):
    """Create social applications if they don't exist"""
    SocialApp = apps.get_model('socialaccount', 'SocialApp')
    SiteModel = apps.get_model('sites', 'Site')
    
    # Get current site
    try:
        current_site = SiteModel.objects.get(id=1)
    except SiteModel.DoesNotExist:
        current_site = SiteModel.objects.create(
            id=1,
            domain='localhost:8003',
            name='Convertica'
        )
    
    # Create Google Social App
    if not SocialApp.objects.filter(provider='google').exists():
        google_app = SocialApp.objects.create(
            provider='google',
            name='Google',
            client_id='542121284706-gnpklp992hic5tni5k9ffqum4q8gsk9c.apps.googleusercontent.com',
            secret='',  # Add your Google client secret here
        )
        google_app.sites.add(current_site)
    
    # Create Facebook Social App (placeholder)
    if not SocialApp.objects.filter(provider='facebook').exists():
        facebook_app = SocialApp.objects.create(
            provider='facebook',
            name='Facebook',
            client_id='',  # Add your Facebook app ID here
            secret='',     # Add your Facebook app secret here
        )
        facebook_app.sites.add(current_site)


def remove_social_apps(apps, _schema_editor):
    """Remove social applications"""
    SocialApp = apps.get_model('socialaccount', 'SocialApp')
    
    SocialApp.objects.filter(provider='google').delete()
    SocialApp.objects.filter(provider='facebook').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('sites', '0002_alter_domain_unique'),
        ('socialaccount', '0003_extra_data_default_dict'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_social_apps, remove_social_apps),
    ]
