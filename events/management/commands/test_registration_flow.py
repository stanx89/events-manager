from django.core.management.base import BaseCommand
from events.models import RegistrationRequest
from events.views import send_verification_email
from datetime import datetime, timedelta
import uuid
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test the registration process and verification email sending'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            default='stankayombo@gmail.com',
            help='Email address for test registration'
        )
        parser.add_argument(
            '--check-existing',
            action='store_true',
            help='Check existing registration requests'
        )

    def handle(self, *args, **options):
        email = options['email']
        check_existing = options['check_existing']
        
        self.stdout.write('🔍 Registration Process Diagnostic')
        self.stdout.write('=' * 50)
        
        if check_existing:
            # Check existing registrations
            self.stdout.write('📋 Existing Registration Requests:')
            registrations = RegistrationRequest.objects.filter(email=email).order_by('-created_at')
            
            if registrations.exists():
                for reg in registrations:
                    status = "✅ Verified" if reg.is_verified else "⏳ Pending"
                    expired = "❌ Expired" if reg.is_expired() else "✅ Valid"
                    
                    self.stdout.write(f'  - ID: {reg.id}')
                    self.stdout.write(f'    Email: {reg.email}')
                    self.stdout.write(f'    Name: {reg.full_name}')
                    self.stdout.write(f'    Event: {reg.event_name}')
                    self.stdout.write(f'    Created: {reg.created_at}')
                    self.stdout.write(f'    Status: {status}')
                    self.stdout.write(f'    Token: {expired}')
                    self.stdout.write('')
            else:
                self.stdout.write('  No existing registrations found.')
                
        # Test new registration
        self.stdout.write('\n🧪 Testing New Registration Process:')
        
        try:
            # Create test registration
            registration_request = RegistrationRequest.objects.create(
                full_name='Test Registration User',
                email=email,
                mobile_number='0714569755',
                event_name='Test Event Registration',
                event_date=datetime.now() + timedelta(days=30),
                password='test_password_hash',
                verification_token=str(uuid.uuid4()),
                expires_at=datetime.now() + timedelta(hours=24)
            )
            
            self.stdout.write(f'✅ Registration created: ID {registration_request.id}')
            self.stdout.write(f'   Email: {registration_request.email}')
            self.stdout.write(f'   Token: {registration_request.verification_token}')
            
            # Test email sending
            self.stdout.write('\n📧 Testing Verification Email:')
            
            try:
                result = send_verification_email(registration_request)
                
                if result:
                    self.stdout.write('✅ Email sent successfully!')
                else:
                    self.stdout.write('❌ Email sending failed!')
                    
            except Exception as e:
                self.stdout.write(f'❌ Email sending exception: {str(e)}')
                import traceback
                self.stdout.write(traceback.format_exc())
                
            # Show verification URL
            from django.urls import reverse
            verification_url = f"http://localhost:8000{reverse('events:verify_email', kwargs={'token': registration_request.verification_token})}"
            
            self.stdout.write(f'\n🔗 Verification URL:')
            self.stdout.write(f'   {verification_url}')
            
        except Exception as e:
            self.stdout.write(f'❌ Registration creation failed: {str(e)}')
            import traceback
            self.stdout.write(traceback.format_exc())
            
        self.stdout.write('\n💡 Troubleshooting Tips:')
        self.stdout.write('   1. Check logs in /logs/background_tasks.log')
        self.stdout.write('   2. Verify email configuration in settings.py')
        self.stdout.write('   3. Test email connection: python manage.py test_email --check-connection')
        self.stdout.write('   4. Check spam folder in your email client')