import threading
import time
import logging
from django.core.mail import send_mail
from django.conf import settings
from .models import Messages, Pledges

logger = logging.getLogger(__name__)


def create_and_queue_message(pledge, message_text, method='sms'):
    """
    Helper function to create a message and log the queuing process
    """
    try:
        message = Messages.objects.create(
            pledge=pledge,
            message=message_text,
            method=method,
            status='queued'
        )
        logger.info(f"Message {message.id} created and queued for {pledge.name} ({pledge.mobile_number}) via {method}")
        logger.debug(f"Message {message.id} content preview: {message_text[:100]}{'...' if len(message_text) > 100 else ''}")
        return message
    except Exception as e:
        logger.error(f"Failed to create message for {pledge.name}: {str(e)}")
        raise


def log_message_queue_stats():
    """
    Log current message queue statistics
    """
    try:
        from django.db.models import Count
        stats = Messages.objects.values('status').annotate(count=Count('id'))
        stats_dict = {item['status']: item['count'] for item in stats}
        
        logger.info("Message queue statistics:")
        for status in ['queued', 'pending', 'sent', 'failed', 'delivered']:
            count = stats_dict.get(status, 0)
            if count > 0:
                logger.info(f"  {status.upper()}: {count} messages")
        
        total = sum(stats_dict.values())
        logger.info(f"  TOTAL: {total} messages in queue")
        
    except Exception as e:
        logger.error(f"Failed to log message queue stats: {str(e)}")


def send_message_background(message_id):
    """
    Background task to send a single message
    This is a placeholder for actual sending logic (SMS, WhatsApp, Email, etc.)
    """
    logger.info(f"Starting to process message {message_id}")
    
    try:
        message = Messages.objects.get(id=message_id)
        logger.info(f"Retrieved message {message_id} for {message.pledge.name} ({message.pledge.mobile_number})")
        
        # Update status to processing
        message.status = 'pending'
        message.save()
        logger.info(f"Updated message {message_id} status to 'pending'")
        
        # Simulate sending delay (replace with actual API calls)
        time.sleep(2)  # Remove this in production
        
        # Here you would implement actual sending logic based on method:
        logger.info(f"Attempting to send message {message_id} via {message.method}")
        
        if message.method == 'sms':
            success = send_sms(message)
        elif message.method == 'whatsapp':
            success = send_whatsapp(message)
        elif message.method == 'email':
            success = send_email_message(message)
        else:
            logger.error(f"Unknown message method '{message.method}' for message {message_id}")
            success = False
            
        # Update message status
        if success:
            message.status = 'sent'
            logger.info(f"Message {message_id} sent successfully to {message.pledge.name}")
        else:
            message.status = 'failed'
            logger.error(f"Failed to send message {message_id} to {message.pledge.name}")
            
        message.save()
        logger.info(f"Updated message {message_id} final status to '{message.status}'")
        
    except Messages.DoesNotExist:
        logger.error(f"Message {message_id} not found in database")
    except Exception as e:
        logger.error(f"Unexpected error sending message {message_id}: {str(e)}")
        try:
            message = Messages.objects.get(id=message_id)
            message.status = 'failed'
            message.save()
            logger.info(f"Updated message {message_id} status to 'failed' due to exception")
        except Exception as save_error:
            logger.error(f"Failed to update message {message_id} status after error: {str(save_error)}")


def send_bulk_messages_background(message_ids):
    """
    Background task to send multiple messages
    """
    def worker():
        logger.info(f"Starting bulk send process for {len(message_ids)} messages")
        
        # Log initial queue statistics
        log_message_queue_stats()
        
        sent_count = 0
        failed_count = 0
        
        for i, message_id in enumerate(message_ids, 1):
            logger.info(f"Processing message {i}/{len(message_ids)} (ID: {message_id})")
            
            try:
                # Check if message still exists and is in correct status
                message = Messages.objects.get(id=message_id)
                if message.status != 'queued':
                    logger.warning(f"Message {message_id} status is '{message.status}', expected 'queued'. Skipping.")
                    continue
                    
                send_message_background(message_id)
                
                # Check final status
                message.refresh_from_db()
                if message.status == 'sent':
                    sent_count += 1
                    logger.info(f"Bulk progress: {i}/{len(message_ids)} - Message {message_id} sent successfully")
                else:
                    failed_count += 1
                    logger.warning(f"Bulk progress: {i}/{len(message_ids)} - Message {message_id} failed")
                    
            except Messages.DoesNotExist:
                logger.error(f"Message {message_id} not found during bulk processing")
                failed_count += 1
            except Exception as e:
                logger.error(f"Error processing message {message_id} in bulk: {str(e)}")
                failed_count += 1
            
            # Small delay between messages to avoid rate limiting
            if i < len(message_ids):  # Don't sleep after the last message
                time.sleep(0.5)
                logger.debug(f"Pausing 0.5s before next message...")
            
        logger.info(f"Bulk send completed: {sent_count} sent, {failed_count} failed, {len(message_ids)} total")
        
        # Log final queue statistics
        log_message_queue_stats()
    
    # Start the worker in a separate thread
    logger.info(f"Starting background thread for bulk message sending")
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    logger.info(f"Background thread started for {len(message_ids)} messages")
    
    return thread


def send_sms(message):
    """
    Placeholder for SMS sending implementation
    Replace with your SMS provider's API (Twilio, etc.)
    """
    logger.info(f"Attempting SMS send to {message.pledge.mobile_number} for {message.pledge.name}")
    
    try:
        # Example SMS implementation
        # from twilio.rest import Client
        # client = Client(account_sid, auth_token)
        # message = client.messages.create(
        #     body=message.message,
        #     from_='+1234567890',
        #     to=message.pledge.mobile_number
        # )
        
        # For now, just simulate success
        logger.info(f"SMS simulation: Sending to {message.pledge.mobile_number}")
        logger.debug(f"SMS content preview: {message.message[:100]}{'...' if len(message.message) > 100 else ''}")
        
        # Simulate some processing time
        time.sleep(1)
        
        logger.info(f"SMS sent successfully to {message.pledge.mobile_number} ({message.pledge.name})")
        return True
        
    except Exception as e:
        logger.error(f"SMS sending failed for {message.pledge.mobile_number}: {str(e)}")
        return False


def send_whatsapp(message):
    """
    Placeholder for WhatsApp sending implementation
    Replace with WhatsApp Business API
    """
    logger.info(f"Attempting WhatsApp send to {message.pledge.mobile_number} for {message.pledge.name}")
    
    try:
        # Example WhatsApp implementation
        # Implementation depends on your WhatsApp provider
        
        logger.info(f"WhatsApp simulation: Sending to {message.pledge.mobile_number}")
        logger.debug(f"WhatsApp content preview: {message.message[:100]}{'...' if len(message.message) > 100 else ''}")
        
        # Simulate some processing time
        time.sleep(1.5)
        
        logger.info(f"WhatsApp sent successfully to {message.pledge.mobile_number} ({message.pledge.name})")
        return True
        
    except Exception as e:
        logger.error(f"WhatsApp sending failed for {message.pledge.mobile_number}: {str(e)}")
        return False


def send_email_message(message):
    """
    Email sending implementation
    """
    logger.info(f"Attempting email send to {message.pledge.name} ({message.pledge.mobile_number})")
    
    try:
        # Assuming you have email configured in settings
        recipient_email = f"{message.pledge.mobile_number}@email.com"  # Replace with actual email logic
        
        logger.debug(f"Email recipient: {recipient_email}")
        logger.debug(f"Email content preview: {message.message[:100]}{'...' if len(message.message) > 100 else ''}")
        
        send_mail(
            subject='Message from Events Management',
            message=message.message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=False,
        )
        
        logger.info(f"Email sent successfully to {message.pledge.name} at {recipient_email}")
        return True
        
    except Exception as e:
        logger.error(f"Email sending failed for {message.pledge.name}: {str(e)}")
        return False