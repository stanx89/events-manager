# Background Message Processing

This application now supports background processing for sending messages, which prevents the main application thread from being blocked during message sending operations.

## How It Works

### 1. Message Creation
When a message is created (individual or bulk), it is:
- Saved to the database with status 'queued'
- Immediately passed to a background thread for processing
- The user gets immediate feedback that the message is "queued for sending"

### 2. Background Processing
The background task:
- Updates message status from 'queued' to 'pending'
- Attempts to send the message via the specified method (SMS, WhatsApp, Email)
- Updates status to 'sent' on success or 'failed' on error
- Logs all activities for monitoring

### 3. Message Status Flow
```
queued → pending → sent/failed
```

## Available Message Methods

- **SMS**: Placeholder for SMS API integration (Twilio, etc.)
- **WhatsApp**: Placeholder for WhatsApp Business API
- **Email**: Uses Django's email backend
- **Voice Call**: Manual tracking
- **In Person**: Manual tracking

## Monitoring

### Queue Status API
Check current queue status:
```
GET /api/message-queue-status/
```

Returns:
```json
{
  "status": "success",
  "queue_status": {
    "queued": 5,
    "pending": 2,
    "sent": 150,
    "delivered": 140,
    "failed": 3,
    "read": 120
  },
  "total_messages": 420,
  "recent_activity_24h": 25,
  "last_updated": "2025-10-16T10:30:00Z"
}
```

### Management Command
Process queued messages manually:
```bash
python manage.py process_messages --batch-size=10 --max-retries=3
```

## Configuration

### Logging
Logs are written to `logs/background_tasks.log` and console.

### Email Settings
Configure email settings in `settings.py`:
```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
```

## Production Deployment

For production environments, consider:

1. **Use Celery** for more robust background task processing
2. **Redis/RabbitMQ** as message brokers
3. **Separate worker processes** for sending messages
4. **Rate limiting** to avoid API limits
5. **Monitoring tools** for queue status

## Adding New Message Methods

To add a new message method:

1. Add to `MESSAGE_METHODS` in `models.py`
2. Implement sender function in `tasks.py`
3. Update the routing in `send_message_background()`

Example:
```python
def send_telegram(message):
    # Implement Telegram Bot API
    pass
```

## Error Handling

- Failed messages are logged with error details
- Simple retry logic is implemented in the management command
- For production, implement exponential backoff and dead letter queues

## Testing

The current implementation uses placeholder functions that simulate sending.
Replace with actual API integrations for production use.