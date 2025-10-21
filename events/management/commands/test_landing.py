from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from events.models import RegistrationRequest
from events.views import send_verification_email
from datetime import datetime, timedelta
from django.utils import timezone


class Command(BaseCommand):
    help = 'Test the landing page functionality'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-email',
            type=str,
            help='Test email sending functionality with this email address',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Testing Landing Page Functionality'))
        
        if options['test_email']:
            # Test email functionality
            email = options['test_email']
            
            # Create a test registration request
            test_request = RegistrationRequest(
                full_name="Test User",
                email=email,
                mobile_number="+255123456789",
                event_name="Test Event",
                event_date=timezone.now() + timedelta(days=30),
                expires_at=timezone.now() + timedelta(hours=24)
            )
            test_request.save()
            
            try:
                # Test sending verification email
                send_verification_email(test_request)
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Test verification email sent to {email}')
                )
                
                # Display verification URL for testing
                from django.urls import reverse
                verification_url = f"http://127.0.0.1:8000{reverse('events:verify_email', kwargs={'token': test_request.verification_token})}"
                self.stdout.write(
                    self.style.WARNING(f'🔗 Verification URL: {verification_url}')
                )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Failed to send email: {str(e)}')
                )
                
            # Clean up test data
            test_request.delete()
            
        else:
            # General system check
            self.stdout.write('🔍 Checking system configuration...')
            
            # Check database
            try:
                from events.models import Event, EventUser, RegistrationRequest
                self.stdout.write('✅ Database models accessible')
                
                # Check counts
                events_count = Event.objects.count()
                users_count = EventUser.objects.count()
                requests_count = RegistrationRequest.objects.count()
                
                self.stdout.write(f'📊 System Stats:')
                self.stdout.write(f'   - Events: {events_count}')
                self.stdout.write(f'   - Verified Users: {users_count}')
                self.stdout.write(f'   - Pending Registrations: {requests_count}')
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Database error: {str(e)}'))
            
            # Check email configuration
            self.stdout.write('📧 Email Configuration:')
            self.stdout.write(f'   - Backend: {settings.EMAIL_BACKEND}')
            self.stdout.write(f'   - From Email: {settings.DEFAULT_FROM_EMAIL}')
            
            # Check URLs
            self.stdout.write('🌐 Important URLs:')
            self.stdout.write('   - Landing Page: http://127.0.0.1:8000/landing/')
            self.stdout.write('   - Dashboard: http://127.0.0.1:8000/')
            
        self.stdout.write(self.style.SUCCESS('\n🎉 Landing page system is ready!'))
        self.stdout.write('To test registration:')
        self.stdout.write('1. Visit: http://127.0.0.1:8000/landing/')
        self.stdout.write('2. Fill out the registration form')
        self.stdout.write('3. Check email for verification link')
        self.stdout.write('4. Click verification link to complete registration')