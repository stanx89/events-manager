from django.core.management.base import BaseCommand
from events.models import RegistrationRequest
from events.views import send_verification_email
from datetime import datetime, timedelta
import uuid


class Command(BaseCommand):
    help = 'Simple test to create a registration and send verification email'

    def handle(self, *args, **options):
        email = 'stankayombo@gmail.com'
        
        self.stdout.write('Creating test registration...')
        
        # Create a simple test registration
        registration_request = RegistrationRequest.objects.create(
            full_name='Test User',
            email=email,
            mobile_number='0714569755',
            event_name='Test Event',
            event_date=datetime.now() + timedelta(days=30),
            password='hashed_password',
            verification_token=str(uuid.uuid4()),
            expires_at=datetime.now() + timedelta(hours=24)
        )
        
        self.stdout.write(f'✅ Created registration ID: {registration_request.id}')
        self.stdout.write(f'📧 Sending verification email to: {email}')
        
        # Try to send verification email
        try:
            result = send_verification_email(registration_request)
            if result:
                self.stdout.write('✅ Email sent successfully!')
            else:
                self.stdout.write('❌ Email sending returned False')
        except Exception as e:
            self.stdout.write(f'❌ Exception during email sending: {str(e)}')
            
        self.stdout.write('\n📋 Check the logs for detailed information:')
        self.stdout.write('  tail -f /Users/stan/Ndondo/events/logs/background_tasks.log')
        
        # Show the verification URL for testing
        from django.urls import reverse
        try:
            verification_url = f"http://localhost:8000{reverse('events:verify_email', kwargs={'token': registration_request.verification_token})}"
            self.stdout.write(f'\n🔗 Manual verification URL: {verification_url}')
        except:
            self.stdout.write(f'\n🔗 Token for manual testing: {registration_request.verification_token}')