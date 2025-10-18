import threading
import time
import logging
import requests
import json
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
    WhatsApp sending implementation using Facebook Graph API
    """
    logger.info(f"Attempting WhatsApp send to {message.pledge.mobile_number} for {message.pledge.name}")
    
    try:
        # WhatsApp API configuration - these should be in your settings.py
        whatsapp_token = getattr(settings, 'WHATSAPP_ACCESS_TOKEN', None)
        whatsapp_phone_id = getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', '878543835331362')  # Default from your example
        whatsapp_api_url = f"https://graph.facebook.com/v22.0/{whatsapp_phone_id}/messages"
        
        if not whatsapp_token:
            logger.error("WHATSAPP_ACCESS_TOKEN not configured in settings")
            return False
        
        # Format phone number (remove any non-digits and ensure it has country code)
        phone_number = message.pledge.mobile_number
        # Remove any non-digit characters
        phone_number = ''.join(filter(str.isdigit, phone_number))
        
        # If number doesn't start with country code, assume it's a local number
        # You may need to adjust this logic based on your country
        if not phone_number.startswith('255'):  # Kenya country code example
            if phone_number.startswith('0'):
                phone_number = '255' + phone_number[1:]  # Replace leading 0 with country code
            else:
                phone_number = '255' + phone_number  # Add country code
        
        logger.info(f"Formatted phone number: {phone_number}")
        
        # Prepare the request headers
        headers = {
            'Authorization': f'Bearer {whatsapp_token[:10]}...{whatsapp_token[-4:]}',  # Masked token for logging
            'Content-Type': 'application/json'
        }
        
        # Log headers (with masked token for security)
        logger.info(f"WhatsApp API request headers: {headers}")
        
        # Try to send as text message first
        try:
            # Prepare the message payload for text message
            payload = {
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "template",
                "template": {
                    "name": "hello_world",
                    "language": {"code": "en_US"}
                }
            }
            
            logger.info(f"WhatsApp API URL: {whatsapp_api_url}")
            logger.info(f"WhatsApp request payload:")
            logger.info(f"{json.dumps(payload, indent=2)}")
            
            # Prepare actual headers for request (with full token)
            actual_headers = {
                'Authorization': f'Bearer {whatsapp_token}',
                'Content-Type': 'application/json'
            }
            
            # Make the API request
            logger.info(f"Sending WhatsApp API request...")
            response = requests.post(
                whatsapp_api_url,
                headers=actual_headers,
                json=payload,
                timeout=30
            )
            
            logger.info(f"WhatsApp API response received - Status Code: {response.status_code}")
            logger.info(f"WhatsApp API response headers: {dict(response.headers)}")
            logger.info(f"WhatsApp API response body:")
            logger.info(f"{response.text}")
            
            # Try to parse response as JSON for better logging
            try:
                response_json = response.json()
                logger.info(f"WhatsApp API response JSON:")
                logger.info(f"{json.dumps(response_json, indent=2)}")
            except json.JSONDecodeError:
                logger.warning(f"WhatsApp API response is not valid JSON")
            
            if response.status_code == 200:
                response_data = response.json()
                if 'messages' in response_data and len(response_data['messages']) > 0:
                    message_id = response_data['messages'][0].get('id', 'unknown')
                    logger.info(f"WhatsApp message sent successfully to {phone_number} ({message.pledge.name}). Message ID: {message_id}")
                    return True
                else:
                    logger.warning(f"WhatsApp API returned 200 but no message ID found: {response_data}")
                    return False
            else:
                logger.error(f"WhatsApp API error {response.status_code}: {response.text}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"WhatsApp API request failed: {str(e)}")
            return False
            
    except Exception as e:
        logger.error(f"WhatsApp sending failed for {message.pledge.mobile_number}: {str(e)}")
        return False


def send_whatsapp_template(message, template_name='hello_world', language_code='en_US'):
    """
    Send WhatsApp template message (for cases where template is required)
    """
    logger.info(f"Attempting WhatsApp template send to {message.pledge.mobile_number} for {message.pledge.name}")
    
    try:
        whatsapp_token = getattr(settings, 'WHATSAPP_ACCESS_TOKEN', None)
        whatsapp_phone_id = getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', '878543835331362')
        whatsapp_api_url = f"https://graph.facebook.com/v22.0/{whatsapp_phone_id}/messages"
        
        if not whatsapp_token:
            logger.error("WHATSAPP_ACCESS_TOKEN not configured in settings")
            return False
        
        # Format phone number
        phone_number = message.pledge.mobile_number
        phone_number = ''.join(filter(str.isdigit, phone_number))
        
        if not phone_number.startswith('255'):
            if phone_number.startswith('0'):
                phone_number = '255' + phone_number[1:]
            else:
                phone_number = '255' + phone_number
        
        # Prepare headers (with masked token for logging)
        headers_masked = {
            'Authorization': f'Bearer {whatsapp_token[:10]}...{whatsapp_token[-4:]}',  # Masked token for logging
            'Content-Type': 'application/json'
        }
        
        # Actual headers for request
        headers = {
            'Authorization': f'Bearer {whatsapp_token}',
            'Content-Type': 'application/json'
        }
        
        logger.info(f"WhatsApp template API request headers: {headers_masked}")
        
        # Template message payload (as per your example)
        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": language_code
                }
            }
        }
        
        logger.info(f"WhatsApp template API URL: {whatsapp_api_url}")
        logger.info(f"WhatsApp template request payload:")
        logger.info(f"{json.dumps(payload, indent=2)}")
        
        logger.info(f"Sending WhatsApp template API request...")
        response = requests.post(
            whatsapp_api_url,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        logger.info(f"WhatsApp template API response received - Status Code: {response.status_code}")
        logger.info(f"WhatsApp template API response headers: {dict(response.headers)}")
        logger.info(f"WhatsApp template API response body:")
        logger.info(f"{response.text}")
        
        # Try to parse response as JSON for better logging
        try:
            response_json = response.json()
            logger.info(f"WhatsApp template API response JSON:")
            logger.info(f"{json.dumps(response_json, indent=2)}")
        except json.JSONDecodeError:
            logger.warning(f"WhatsApp template API response is not valid JSON")
        
        if response.status_code == 200:
            response_data = response.json()
            if 'messages' in response_data and len(response_data['messages']) > 0:
                message_id = response_data['messages'][0].get('id', 'unknown')
                logger.info(f"WhatsApp template sent successfully to {phone_number} ({message.pledge.name}). Message ID: {message_id}")
                return True
            else:
                logger.warning(f"WhatsApp template API returned 200 but no message ID found: {response_data}")
                return False
        else:
            logger.error(f"WhatsApp template API error {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"WhatsApp template sending failed for {message.pledge.mobile_number}: {str(e)}")
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