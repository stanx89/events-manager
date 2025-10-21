from django.core.management.base import BaseCommand
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send a detailed test email with HTML formatting'

    def add_arguments(self, parser):
        parser.add_argument(
            '--to',
            type=str,
            default='stankayombo@gmail.com',
            help='Email address to send test email to'
        )
        parser.add_argument(
            '--html',
            action='store_true',
            help='Send HTML formatted email instead of plain text'
        )

    def handle(self, *args, **options):
        recipient_email = options['to']
        use_html = options['html']
        
        subject = 'Enhanced Test Email from Events Management System'
        
        # Plain text version
        text_content = """
Hello from the Events Management System!

This is an enhanced test email to verify email delivery.

Email Configuration:
- From: events@nifty.co.tz
- Host: mail.nifty.co.tz
- Port: 587 (TLS)

If you receive this email, your email system is working correctly!

Best regards,
Events Management Team
        """.strip()
        
        # HTML version
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Test Email</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2196F3; border-bottom: 2px solid #2196F3; padding-bottom: 10px;">
                    Events Management System - Test Email
                </h2>
                
                <p>Hello! 👋</p>
                
                <p>This is an <strong>enhanced test email</strong> to verify that your email delivery system is working correctly.</p>
                
                <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #555;">Email Configuration Details:</h3>
                    <ul style="margin: 0;">
                        <li><strong>From:</strong> events@nifty.co.tz</li>
                        <li><strong>SMTP Host:</strong> mail.nifty.co.tz</li>
                        <li><strong>Port:</strong> 587 (TLS Encrypted)</li>
                        <li><strong>Timestamp:</strong> """ + str(settings.USE_TZ) + """</li>
                    </ul>
                </div>
                
                <div style="background-color: #e8f5e8; padding: 15px; border-left: 4px solid #4CAF50; margin: 20px 0;">
                    <p style="margin: 0;"><strong>✅ Success!</strong> If you receive this email, your email configuration is working perfectly!</p>
                </div>
                
                <p style="margin-top: 30px;">
                    Best regards,<br>
                    <strong>Events Management Team</strong>
                </p>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="font-size: 12px; color: #666;">
                    This is an automated test email from your Events Management System.
                </p>
            </div>
        </body>
        </html>
        """.strip()

        try:
            self.stdout.write(f'Sending enhanced test email to: {recipient_email}')
            self.stdout.write(f'HTML formatting: {"Yes" if use_html else "No"}')
            
            if use_html:
                # Send HTML email
                msg = EmailMultiAlternatives(
                    subject=subject,
                    body=text_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[recipient_email]
                )
                msg.attach_alternative(html_content, "text/html")
                msg.send()
            else:
                # Send plain text email
                send_mail(
                    subject=subject,
                    message=text_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient_email],
                    fail_silently=False,
                )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Enhanced test email sent successfully to {recipient_email}!'
                )
            )
            
            # Provide delivery tips
            self.stdout.write('')
            self.stdout.write('📧 Email Delivery Tips:')
            self.stdout.write('   1. Check your spam/junk folder')
            self.stdout.write('   2. Add events@nifty.co.tz to your contacts')
            self.stdout.write('   3. Check if your email provider blocks unknown senders')
            self.stdout.write('   4. Gmail may take 1-5 minutes to deliver')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to send enhanced test email: {str(e)}')
            )
            logger.error(f'Enhanced email test failed: {str(e)}')