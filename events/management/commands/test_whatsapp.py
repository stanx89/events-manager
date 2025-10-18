from django.core.management.base import BaseCommand
from django.conf import settings
from events.models import Pledges, Messages
from events.tasks import send_whatsapp, send_whatsapp_template
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test WhatsApp message sending functionality'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--phone',
            type=str,
            help='Phone number to send test message to (e.g., +254712345678 or 0712345678)',
            required=True
        )
        parser.add_argument(
            '--message',
            type=str,
            help='Test message to send',
            default='Hello! This is a test message from Events Management System.'
        )
        parser.add_argument(
            '--template',
            action='store_true',
            help='Send template message instead of text message'
        )
        parser.add_argument(
            '--template-name',
            type=str,
            help='Template name to use (default: hello_world)',
            default='hello_world'
        )
    
    def handle(self, *args, **options):
        phone_number = options['phone']
        message_text = options['message']
        use_template = options['template']
        template_name = options['template_name']
        
        self.stdout.write(f"Testing WhatsApp sending to: {phone_number}")
        
        # Check if WhatsApp is configured
        whatsapp_token = getattr(settings, 'WHATSAPP_ACCESS_TOKEN', None)
        whatsapp_phone_id = getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', None)
        
        if not whatsapp_token or whatsapp_token == 'your-whatsapp-access-token-here':
            self.stdout.write(
                self.style.ERROR(
                    'WhatsApp not configured! Please set WHATSAPP_ACCESS_TOKEN in settings.py'
                )
            )
            return
        
        if not whatsapp_phone_id:
            self.stdout.write(
                self.style.ERROR(
                    'WhatsApp Phone Number ID not configured! Please set WHATSAPP_PHONE_NUMBER_ID in settings.py'
                )
            )
            return
        
        self.stdout.write(f"WhatsApp Token: {whatsapp_token[:10]}..." if whatsapp_token else "Not set")
        self.stdout.write(f"WhatsApp Phone ID: {whatsapp_phone_id}")
        
        try:
            # Find or create a test pledge
            pledge, created = Pledges.objects.get_or_create(
                mobile_number=phone_number,
                defaults={
                    'name': 'Test User',
                    'amount': 100.00,
                    'status': 'new',
                    'whatsapp_status': True
                }
            )
            
            if created:
                self.stdout.write(f"Created test pledge for {phone_number}")
            else:
                self.stdout.write(f"Using existing pledge for {phone_number}")
            
            # Create a test message
            test_message = Messages.objects.create(
                pledge=pledge,
                message=message_text,
                method='whatsapp',
                status='queued'
            )
            
            self.stdout.write(f"Created test message ID: {test_message.id}")
            
            # Send the message
            if use_template:
                self.stdout.write(f"Sending template message '{template_name}'...")
                success = send_whatsapp_template(test_message, template_name)
            else:
                self.stdout.write(f"Sending text message...")
                success = send_whatsapp(test_message)
            
            if success:
                self.stdout.write(
                    self.style.SUCCESS(f'WhatsApp message sent successfully to {phone_number}!')
                )
                test_message.status = 'sent'
            else:
                self.stdout.write(
                    self.style.ERROR(f'Failed to send WhatsApp message to {phone_number}')
                )
                test_message.status = 'failed'
            
            test_message.save()
            
            self.stdout.write(f"Message status updated to: {test_message.status}")
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during WhatsApp test: {str(e)}')
            )
            logger.error(f"WhatsApp test error: {str(e)}")