from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
import logging
import smtplib
import socket

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test email sending functionality'

    def add_arguments(self, parser):
        parser.add_argument(
            '--to',
            type=str,
            default='stankayombo@gmail.com',
            help='Email address to send test email to'
        )
        parser.add_argument(
            '--subject',
            type=str,
            default='Test Email from Events Management System',
            help='Subject line for the test email'
        )
        parser.add_argument(
            '--use-smtp',
            action='store_true',
            help='Use SMTP backend instead of console backend'
        )
        parser.add_argument(
            '--check-connection',
            action='store_true',
            help='Check SMTP connection without sending email'
        )

    def check_smtp_connection(self):
        """Test SMTP connection without sending email"""
        try:
            host = getattr(settings, 'EMAIL_HOST', '')
            port = getattr(settings, 'EMAIL_PORT', 587)
            user = getattr(settings, 'EMAIL_HOST_USER', '')
            password = getattr(settings, 'EMAIL_HOST_PASSWORD', '')
            
            self.stdout.write(f'Testing connection to {host}:{port}')
            
            # Test basic connection
            if port == 465:
                server = smtplib.SMTP_SSL(host, port, timeout=10)
            else:
                server = smtplib.SMTP(host, port, timeout=10)
                if getattr(settings, 'EMAIL_USE_TLS', False):
                    server.starttls()
            
            self.stdout.write(self.style.SUCCESS('✓ Connection established'))
            
            # Test authentication
            if user and password:
                server.login(user, password)
                self.stdout.write(self.style.SUCCESS('✓ Authentication successful'))
            #0714569755
            server.quit()
            return True
            
        except socket.timeout:
            self.stdout.write(self.style.ERROR('✗ Connection timeout - check host and port'))
            return False
        except smtplib.SMTPAuthenticationError:
            self.stdout.write(self.style.ERROR('✗ Authentication failed - check username and password'))
            return False
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Connection failed: {str(e)}'))
            return False

    def handle(self, *args, **options):
        recipient_email = options['to']
        subject = options['subject']
        use_smtp = options['use_smtp']
        check_connection = options['check_connection']
        
        # Display current settings
        self.stdout.write('Current Email Settings:')
        self.stdout.write(f'  Backend: {settings.EMAIL_BACKEND}')
        self.stdout.write(f'  Host: {getattr(settings, "EMAIL_HOST", "Not set")}')
        self.stdout.write(f'  Port: {getattr(settings, "EMAIL_PORT", "Not set")}')
        self.stdout.write(f'  User: {getattr(settings, "EMAIL_HOST_USER", "Not set")}')
        self.stdout.write(f'  Use TLS: {getattr(settings, "EMAIL_USE_TLS", False)}')
        self.stdout.write(f'  Use SSL: {getattr(settings, "EMAIL_USE_SSL", False)}')
        self.stdout.write(f'  From Email: {settings.DEFAULT_FROM_EMAIL}')
        self.stdout.write('')
        
        # If just checking connection
        if check_connection:
            if self.check_smtp_connection():
                self.stdout.write(self.style.SUCCESS('SMTP connection test passed!'))
            else:
                self.stdout.write(self.style.ERROR('SMTP connection test failed!'))
            return
        
        # Switch backend if requested
        original_backend = settings.EMAIL_BACKEND
        if use_smtp:
            settings.EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
            self.stdout.write(
                self.style.WARNING('Switching to SMTP backend for this test')
            )
        
        message = f"""
Hello from the Events Management System!

This is a test email to verify that the email configuration is working properly.

Email Configuration Details:
- Backend: {settings.EMAIL_BACKEND}
- Host: {getattr(settings, 'EMAIL_HOST', 'Not configured')}
- Port: {getattr(settings, 'EMAIL_PORT', 'Not configured')}
- User: {getattr(settings, 'EMAIL_HOST_USER', 'Not configured')}
- From Email: {settings.DEFAULT_FROM_EMAIL}

If you receive this email, your email configuration is working correctly!

Best regards,
Events Management System
        """.strip()

        try:
            self.stdout.write(f'Sending test email to: {recipient_email}')
            self.stdout.write(f'Subject: {subject}')
            self.stdout.write(f'Using backend: {settings.EMAIL_BACKEND}')
            
            if settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend':
                self.stdout.write(
                    self.style.WARNING(
                        'Using console backend - email will appear in terminal output below:'
                    )
                )
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email],
                fail_silently=False,
            )
            
            if settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend':
                self.stdout.write(
                    self.style.SUCCESS(
                        'Test email sent successfully! (Check terminal output above for email content)'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Test email sent successfully to {recipient_email}!'
                    )
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to send test email: {str(e)}')
            )
            logger.error(f'Email test failed: {str(e)}')
            
        finally:
            # Restore original backend
            if use_smtp:
                settings.EMAIL_BACKEND = original_backend
                self.stdout.write(
                    self.style.WARNING(f'Restored original backend: {original_backend}')
                )