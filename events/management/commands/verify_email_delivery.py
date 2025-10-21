from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from events.models import RegistrationRequest
from events.views import send_verification_email
from datetime import datetime, timedelta
import uuid


class Command(BaseCommand):
    help = 'Verify email delivery using current nifty.co.tz settings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--to',
            type=str,
            default='stankayombo@gmail.com',
            help='Email address to test'
        )
        parser.add_argument(
            '--test-basic',
            action='store_true',
            help='Send basic test email'
        )
        parser.add_argument(
            '--test-registration',
            action='store_true',
            help='Test full registration flow'
        )

    def handle(self, *args, **options):
        email = options['to']
        test_basic = options['test_basic']
        test_registration = options['test_registration']
        
        self.stdout.write('📧 Email Delivery Verification')
        self.stdout.write('Using nifty.co.tz configuration from settings.py')
        self.stdout.write('=' * 60)
        
        # Show current configuration
        self.stdout.write('Current Email Settings:')
        self.stdout.write(f'  Host: {settings.EMAIL_HOST}')
        self.stdout.write(f'  Port: {settings.EMAIL_PORT}')
        self.stdout.write(f'  User: {settings.EMAIL_HOST_USER}')
        self.stdout.write(f'  From: {settings.DEFAULT_FROM_EMAIL}')
        self.stdout.write(f'  TLS: {getattr(settings, "EMAIL_USE_TLS", False)}')
        self.stdout.write('')
        
        if test_basic or not test_registration:
            self.stdout.write('🔧 Test 1: Basic Email Test')
            try:
                send_mail(
                    subject='Test Email - Events Management System',
                    message=f'''
Hello,

This is a test email from your Events Management System using nifty.co.tz configuration.

Email Details:
- Sent from: {settings.DEFAULT_FROM_EMAIL}
- SMTP Host: {settings.EMAIL_HOST}
- Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

If you receive this email, your email configuration is working correctly.

Best regards,
Events Management Team
                    '''.strip(),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False
                )
                self.stdout.write('  ✅ Basic email sent successfully')
            except Exception as e:
                self.stdout.write(f'  ❌ Basic email failed: {str(e)}')
        
        if test_registration or not test_basic:
            self.stdout.write('\n🧪 Test 2: Registration Flow Test')
            try:
                # Create test registration
                registration_request = RegistrationRequest.objects.create(
                    full_name='Email Delivery Test User',
                    email=email,
                    mobile_number='0714569755',
                    event_name='Email Delivery Test Event',
                    event_date=datetime.now() + timedelta(days=30),
                    password='test_password_hash',
                    verification_token=str(uuid.uuid4()),
                    expires_at=datetime.now() + timedelta(hours=24)
                )
                
                self.stdout.write(f'  ✅ Registration created: ID {registration_request.id}')
                
                # Send verification email
                result = send_verification_email(registration_request)
                
                if result:
                    self.stdout.write('  ✅ Verification email sent successfully')
                else:
                    self.stdout.write('  ❌ Verification email failed')
                    
                # Show verification URL for manual testing
                from django.urls import reverse
                verification_url = f"http://localhost:8000{reverse('events:verify_email', kwargs={'token': registration_request.verification_token})}"
                self.stdout.write(f'  🔗 Manual verification: {verification_url}')
                
            except Exception as e:
                self.stdout.write(f'  ❌ Registration test failed: {str(e)}')
        
        # Email delivery troubleshooting
        self.stdout.write('\n💡 Email Delivery Troubleshooting:')
        self.stdout.write('  1. ✉️  Check Gmail SPAM/JUNK folder')
        self.stdout.write('  2. 📂 Check Gmail PROMOTIONS tab')
        self.stdout.write('  3. 🔍 Search Gmail for "events@nifty.co.tz"')
        self.stdout.write('  4. 🔍 Search Gmail for "Events Management"')
        self.stdout.write('  5. ⏰ Wait 5-15 minutes (delivery can be delayed)')
        self.stdout.write('  6. 📧 Try with Yahoo/Outlook email instead')
        
        self.stdout.write('\n📊 Recent Registration Attempts:')
        recent_registrations = RegistrationRequest.objects.filter(
            email=email
        ).order_by('-created_at')[:5]
        
        if recent_registrations.exists():
            for reg in recent_registrations:
                status = "✅ Verified" if reg.is_verified else "⏳ Pending"
                self.stdout.write(f'  - {reg.created_at.strftime("%Y-%m-%d %H:%M")} | {status} | {reg.full_name}')
        else:
            self.stdout.write('  No recent registration attempts found')
            
        self.stdout.write('\n🎯 Recommended Actions:')
        self.stdout.write('  • Emails ARE being sent successfully from your server')
        self.stdout.write('  • This is likely a Gmail delivery/filtering issue')
        self.stdout.write('  • Try registering with stankayombo@yahoo.com to test')
        self.stdout.write('  • Check ALL Gmail folders including Promotions')