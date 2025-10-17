from django.core.management.base import BaseCommand
from django.utils import timezone
from events.models import Messages
from events.tasks import send_message_background
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process queued messages and send them'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=10,
            help='Number of messages to process at once (default: 10)',
        )
        parser.add_argument(
            '--max-retries',
            type=int,
            default=3,
            help='Maximum number of retry attempts for failed messages (default: 3)',
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        max_retries = options['max_retries']
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting message processing with batch size: {batch_size}')
        )
        
        # Get queued messages
        queued_messages = Messages.objects.filter(status='queued')[:batch_size]
        
        if not queued_messages:
            self.stdout.write(
                self.style.WARNING('No queued messages found.')
            )
            return
        
        processed_count = 0
        
        for message in queued_messages:
            try:
                # Update status to pending before processing
                message.status = 'pending'
                message.save()
                
                # Send message in background
                send_message_background(message.id)
                processed_count += 1
                
                self.stdout.write(
                    f'Processing message {message.id} for {message.pledge.name}'
                )
                
            except Exception as e:
                logger.error(f'Error processing message {message.id}: {str(e)}')
                self.stdout.write(
                    self.style.ERROR(f'Failed to process message {message.id}: {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'Processed {processed_count} messages successfully.')
        )
        
        # Also process any failed messages that should be retried
        failed_messages = Messages.objects.filter(status='failed')
        retry_count = 0
        
        for message in failed_messages[:batch_size]:
            # Simple retry logic - in production, you'd want more sophisticated retry handling
            if not hasattr(message, 'retry_count') or message.retry_count < max_retries:
                try:
                    message.status = 'queued'
                    message.save()
                    retry_count += 1
                    
                    self.stdout.write(
                        f'Retrying message {message.id} for {message.pledge.name}'
                    )
                except Exception as e:
                    logger.error(f'Error retrying message {message.id}: {str(e)}')
        
        if retry_count > 0:
            self.stdout.write(
                self.style.WARNING(f'Queued {retry_count} failed messages for retry.')
            )