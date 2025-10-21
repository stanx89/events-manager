from django.core.management.base import BaseCommand
from events.models import RegistrationRequest
from events.views import send_verification_email
from datetime import datetime, timedelta
import uuid


class Command(BaseCommand):
    help = 'Test enhanced email logging'

    def handle(self, *args, **options):
        self.stdout.write('🧪 Testing Enhanced Email Logging System')
        self.stdout.write('=' * 50)
        
        # Create test registration
        registration_request = RegistrationRequest.objects.create(
            full_name='Enhanced Logging Test User',
            email='stankayombo@gmail.com',
            mobile_number='0714569755',
            event_name='Logging Test Event',
            event_date=datetime.now() + timedelta(days=30),
            password='test_password_hash',
            verification_token=str(uuid.uuid4()),
            expires_at=datetime.now() + timedelta(hours=24)
        )
        
        self.stdout.write(f'✅ Created test registration ID: {registration_request.id}')
        self.stdout.write('📧 Sending verification email with enhanced logging...')
        self.stdout.write('📋 Check the detailed logs below and in the log file:')
        self.stdout.write('')
        
        # Send email with enhanced logging
        try:
            result = send_verification_email(registration_request)
            
            if result:
                self.stdout.write('✅ Email sending completed successfully!')
            else:
                self.stdout.write('❌ Email sending failed!')
                
        except Exception as e:
            self.stdout.write(f'💥 Exception occurred: {str(e)}')
            
        self.stdout.write('')
        self.stdout.write('📄 To see detailed logs, run:')
        self.stdout.write('   tail -f /Users/stan/Ndondo/events/logs/background_tasks.log')
        self.stdout.write('')
        self.stdout.write('🎯 The logs now include:')
        self.stdout.write('   • Email configuration details')
        self.stdout.write('   • Recipient and registration information')
        self.stdout.write('   • URL generation process')
        self.stdout.write('   • Template rendering status')
        self.stdout.write('   • Email sending statistics (duration, timestamp)')
        self.stdout.write('   • Detailed error information if failures occur')