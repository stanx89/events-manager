"""
Events Management System Models

This module contains the data models for managing events, pledges, transactions, and messages.
"""

from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from django.utils import timezone
from decimal import Decimal


class EventUserManager(BaseUserManager):
    """
    Custom user manager for EventUser model that uses email as the unique identifier
    """
    
    def create_user(self, email, password=None, **extra_fields):
        """
        Create and save a regular user with the given email and password.
        """
        if not email:
            raise ValueError('The Email field must be set')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and save a superuser with the given email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_verified', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class EventUser(AbstractUser):
    """
    Custom user model that uses email as username
    """
    # Remove the default username field
    username = None
    
    # Phone number validation regex
    phone_regex = RegexValidator(
        regex=r'^\+?255[67]\d{8}$|^\+?0[67]\d{8}$',
        message="Phone number must be a valid Tanzanian number (e.g., +255123456789 or 0123456789)"
    )
    
    # Use email as the unique identifier
    email = models.EmailField(
        unique=True,
        verbose_name="Email Address",
        help_text="Email address for login and notifications"
    )
    
    # Additional fields
    full_name = models.CharField(
        max_length=200,
        verbose_name="Full Name",
        help_text="Full name of the user"
    )
    mobile_number = models.CharField(
        validators=[phone_regex],
        max_length=17,
        verbose_name="Mobile Number",
        help_text="Tanzanian mobile number (e.g., +255123456789)"
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name="Email Verified",
        help_text="Whether the email has been verified"
    )
    verification_token = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Verification Token",
        help_text="Token for email verification"
    )
    verification_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Verification Sent At",
        help_text="When the verification email was last sent"
    )
    privacy_agreement_accepted = models.BooleanField(
        default=False,
        verbose_name="Privacy Agreement Accepted",
        help_text="Whether the user accepted the privacy policy and terms of service"
    )
    marketing_consent = models.BooleanField(
        default=False,
        verbose_name="Marketing Consent",
        help_text="Whether the user consented to receive marketing communications"
    )
    privacy_accepted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Privacy Accepted At",
        help_text="When the user accepted the privacy policy"
    )
    
    # Set email as the username field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']
    
    # Use the custom manager
    objects = EventUserManager()
    
    class Meta:
        db_table = 'event_users'
        verbose_name = 'Event User'
        verbose_name_plural = 'Event Users'
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.full_name} ({self.email})"

    def generate_verification_token(self):
        """Generate a unique verification token"""
        import uuid
        self.verification_token = str(uuid.uuid4())
        self.verification_sent_at = timezone.now()
        self.save()
        return self.verification_token

    def verify_email(self):
        """Mark email as verified and activate account"""
        self.is_verified = True
        self.is_active = True
        self.verification_token = ''
        self.save()

    def get_full_name(self):
        """Return the full name for the user"""
        return self.full_name or self.email

    def get_short_name(self):
        """Return the short name for the user"""
        return self.full_name.split()[0] if self.full_name else self.email


class Pledges(models.Model):
    """
    Model representing a pledge made by a person for an event.
    
    Tracks pledge amounts, payments, and current status.
    """
    # Status choices for pledge tracking
    STATUS_CHOICES = [
        ('new', '🆕 New'),
        ('pending', '⏳ Pending'),
        ('partial', '📊 Partial Payment'),
        ('completed', '✅ Completed'),
        ('cancelled', '❌ Cancelled'),
    ]
    
    # Phone number validation regex
    phone_regex = RegexValidator(
        regex=r'^\+?255[67]\d{8}$|^\+?0[67]\d{8}$',
        message="Phone number must be a valid Tanzanian number (e.g., +255123456789 or 0123456789)"
    )
    
    # Basic Information
    event_id = models.CharField(
        max_length=100, 
        verbose_name="Event ID",
        help_text="Unique identifier for the event"
    )
    name = models.CharField(
        max_length=200, 
        verbose_name="Full Name",
        help_text="Full name of the person making the pledge"
    )
    mobile_number = models.CharField(
        validators=[phone_regex], 
        max_length=17,
        verbose_name="Mobile Number",
        help_text="Tanzanian mobile number (e.g., +255123456789)"
    )
    
    # Financial Information
    pledge = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        verbose_name="Pledge Amount",
        help_text="Total amount pledged (TSH)"
    )
    amount_paid = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        verbose_name="Amount Paid",
        help_text="Total amount paid so far (TSH)"
    )
    
    # Status Tracking
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='new',
        verbose_name="Pledge Status",
        help_text="Current status of the pledge"
    )
    whatsapp_status = models.BooleanField(
        default=False,
        verbose_name="Is WhatsApp Number?",
        help_text="Whether this mobile number supports WhatsApp"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Last Updated"
    )
    
    class Meta:
        db_table = 'pledges'
        verbose_name = 'Pledge'
        verbose_name_plural = 'Pledges'
        ordering = ['-created_at', 'name']
        indexes = [
            models.Index(fields=['event_id']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        """String representation of the pledge."""
        return f"{self.name} - {self.event_id} - TSH {self.pledge:,.2f}"
    
    def balance(self):
        """
        Calculate the outstanding balance on this pledge.
        
        Returns:
            Decimal: The remaining balance (pledge - amount_paid), minimum 0
        """
        calculated_balance = self.pledge - self.amount_paid
        return max(Decimal('0.00'), calculated_balance)
    
    def payment_percentage(self):
        """
        Calculate the percentage of the pledge that has been paid.
        
        Returns:
            float: Percentage paid (0-100)
        """
        if self.pledge <= 0:
            return 0.0
        return min(100.0, (float(self.amount_paid) / float(self.pledge)) * 100)
    
    def is_fully_paid(self):
        """Check if the pledge is fully paid."""
        return self.amount_paid >= self.pledge
    
    def is_overdue(self, days=30):
        """
        Check if pledge is overdue (created more than specified days ago with balance).
        
        Args:
            days (int): Number of days after which a pledge is considered overdue
            
        Returns:
            bool: True if pledge is overdue
        """
        from datetime import timedelta
        cutoff_date = timezone.now() - timedelta(days=days)
        return self.created_at < cutoff_date and self.balance() > 0
    
    def update_status(self):
        """Automatically update status based on payment amount."""
        if self.amount_paid >= self.pledge:
            self.status = 'completed'
        elif self.amount_paid > 0:
            self.status = 'partial'
        else:
            # Keep existing status if no payment made
            pass
        self.save()


class Transactions(models.Model):
    """
    Model representing a payment transaction for a pledge.
    
    Tracks individual payments made towards pledges with different payment methods.
    """
    
    PAYMENT_METHODS = [
        ('cash', '💰 Cash'),
        ('mpesa', '📱 M-Pesa'),
        ('tigopesa', '📲 Tigo Pesa'),
        ('airtelmoney', '📞 Airtel Money'),
        ('bank_transfer', '🏦 Bank Transfer'),
        ('card', '💳 Card Payment'),
        ('cheque', '📋 Cheque'),
        ('other', '🔄 Other'),
    ]
    
    # Relationship
    pledge = models.ForeignKey(
        Pledges, 
        on_delete=models.CASCADE, 
        related_name='transactions',
        verbose_name="Related Pledge",
        help_text="The pledge this transaction is for"
    )
    
    # Transaction Details
    amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        verbose_name="Transaction Amount",
        help_text="Amount of this transaction (TSH)"
    )
    method = models.CharField(
        max_length=20, 
        choices=PAYMENT_METHODS,
        verbose_name="Payment Method",
        help_text="How the payment was made"
    )
    transaction_id = models.CharField(
        max_length=100, 
        unique=True,
        verbose_name="Transaction ID",
        help_text="Unique identifier for this transaction"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Transaction Date"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Last Updated"
    )
    
    class Meta:
        db_table = 'transactions'
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['pledge']),
            models.Index(fields=['method']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        """String representation of the transaction."""
        return f"{self.transaction_id} - TSH {self.amount:,.2f} via {self.get_method_display()}"
    
    def save(self, *args, **kwargs):
        """Override save to update pledge's amount_paid and status."""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            # Update pledge's total amount paid
            self.pledge.amount_paid = self.pledge.transactions.aggregate(
                total=models.Sum('amount')
            )['total'] or Decimal('0.00')
            self.pledge.update_status()


class Messages(models.Model):
    """
    Model representing a message sent to a pledger.
    
    Tracks communication with pledgers via various channels.
    """
    
    MESSAGE_METHODS = [
        ('sms', '📱 SMS'),
        ('whatsapp', '💬 WhatsApp'),
        ('email', '✉️ Email'),
        ('voice_call', '📞 Voice Call'),
        ('in_person', '🤝 In Person'),
    ]
    
    MESSAGE_STATUS = [
        ('queued', '🕐 Queued'),
        ('pending', '⏳ Pending'),
        ('sent', '📤 Sent'),
        ('delivered', '📥 Delivered'),
        ('failed', '❌ Failed'),
        ('read', '👁️ Read'),
    ]
    
    # Relationship
    pledge = models.ForeignKey(
        Pledges, 
        on_delete=models.CASCADE, 
        related_name='messages',
        verbose_name="Related Pledge",
        help_text="The pledge this message relates to"
    )
    
    # Message Details
    message = models.TextField(
        verbose_name="Message Content",
        help_text="Content of the message sent"
    )
    method = models.CharField(
        max_length=20, 
        choices=MESSAGE_METHODS,
        verbose_name="Communication Method",
        help_text="How the message was sent"
    )
    status = models.CharField(
        max_length=20, 
        choices=MESSAGE_STATUS, 
        default='pending',
        verbose_name="Message Status",
        help_text="Current status of the message"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Sent At"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Last Updated"
    )
    
    class Meta:
        db_table = 'messages'
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['pledge']),
            models.Index(fields=['method']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        """String representation of the message."""
        return f"Message to {self.pledge.name} via {self.get_method_display()} - {self.get_status_display()}"
    
    def is_delivered(self):
        """Check if message was successfully delivered."""
        return self.status in ['delivered', 'read']
    
    def mark_as_sent(self):
        """Mark message as sent."""
        self.status = 'sent'
        self.save()
    
    def mark_as_delivered(self):
        """Mark message as delivered."""
        self.status = 'delivered'
        self.save()
    
    def mark_as_failed(self):
        """Mark message as failed."""
        self.status = 'failed'
        self.save()


class MessageTemplate(models.Model):
    """
    Model representing predefined message templates for different event types.
    
    Allows for consistent messaging across different communication scenarios.
    """
    
    TEMPLATE_TYPES = [
        ('reminder', '🔔 Reminder'),
        ('new_pledge', '🆕 New Pledge'),
        ('pledge_completed', '✅ Pledge Completed'),
        ('card', '💳 Card'),
        ('thanks', '🙏 Thanks'),
    ]
    
    # Relationship
    event_id = models.CharField(
        max_length=100,
        verbose_name="Event ID",
        help_text="Event this template belongs to"
    )
    
    # Template Details
    message = models.TextField(
        verbose_name="Template Message",
        help_text="The message template content"
    )
    type = models.CharField(
        max_length=20,
        choices=TEMPLATE_TYPES,
        verbose_name="Template Type",
        help_text="Type/category of this message template"
    )
    
    # Metadata
    name = models.CharField(
        max_length=100,
        verbose_name="Template Name",
        help_text="Descriptive name for this template"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Is Active",
        help_text="Whether this template is currently available for use"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Last Updated"
    )
    
    class Meta:
        db_table = 'message_templates'
        verbose_name = 'Message Template'
        verbose_name_plural = 'Message Templates'
        ordering = ['event_id', 'type', 'name']
        indexes = [
            models.Index(fields=['event_id']),
            models.Index(fields=['type']),
            models.Index(fields=['is_active']),
        ]
        unique_together = []  # Remove unique constraint since event_id is now default
    
    def __str__(self):
        """String representation of the message template."""
        return f"{self.event_id} - {self.get_type_display()} - {self.name}"
    
    def get_formatted_message(self, pledge=None, **kwargs):
        """
        Get formatted message with placeholders replaced.
        
        Args:
            pledge: Pledge object to use for placeholder replacement
            **kwargs: Additional variables for placeholder replacement
            
        Returns:
            str: Formatted message with placeholders replaced
        """
        message = self.message
        
        if pledge:
            replacements = {
                '{name}': pledge.name,
                '{pledge_amount}': f"TSH {pledge.pledge:,.2f}",
                '{amount_paid}': f"TSH {pledge.amount_paid:,.2f}",
                '{balance}': f"TSH {pledge.balance():,.2f}",
                '{event_id}': pledge.event_id,
                '{mobile}': pledge.mobile_number,
                '{status}': pledge.get_status_display(),
            }
            
            for placeholder, value in replacements.items():
                message = message.replace(placeholder, str(value))
        
        # Apply any additional replacements from kwargs
        for key, value in kwargs.items():
            placeholder = f"{{{key}}}"
            message = message.replace(placeholder, str(value))
        
        return message
    
    def preview(self, pledge=None):
        """
        Generate a preview of this template.
        
        Args:
            pledge: Optional pledge object for realistic preview
            
        Returns:
            str: Preview of the formatted message
        """
        if pledge:
            return self.get_formatted_message(pledge)
        else:
            # Use sample data for preview
            sample_data = {
                'name': 'John Doe',
                'pledge_amount': 'TSH 100,000.00',
                'amount_paid': 'TSH 50,000.00',
                'balance': 'TSH 50,000.00',
                'event_id': 'EVENT2025',
                'mobile': '+255123456789',
                'status': 'Partial Payment',
            }
            return self.get_formatted_message(**sample_data)


class Event(models.Model):
    """
    Model representing an event that users can register for
    """
    name = models.CharField(
        max_length=200,
        verbose_name="Event Name",
        help_text="Name of the event"
    )
    date = models.DateTimeField(
        verbose_name="Event Date",
        help_text="Date and time of the event"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Event Description",
        help_text="Description of the event"
    )
    location = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Event Location",
        help_text="Location where the event will take place"
    )
    created_by = models.ForeignKey(
        'EventUser',
        on_delete=models.CASCADE,
        related_name='events',
        verbose_name="Created By"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Is Active",
        help_text="Whether this event is currently active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'events'
        verbose_name = 'Event'
        verbose_name_plural = 'Events'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.date.strftime('%Y-%m-%d')}"


class RegistrationRequest(models.Model):
    """
    Model representing a pending registration request before email verification
    """
    # Phone number validation regex
    phone_regex = RegexValidator(
        regex=r'^\+?255[67]\d{8}$|^\+?0[67]\d{8}$',
        message="Phone number must be a valid Tanzanian number (e.g., +255123456789 or 0123456789)"
    )
    
    full_name = models.CharField(
        max_length=200,
        verbose_name="Full Name"
    )
    email = models.EmailField(
        verbose_name="Email Address"
    )
    password = models.CharField(
        max_length=128,
        verbose_name="Password",
        help_text="Password for the account (will be hashed)"
    )
    mobile_number = models.CharField(
        validators=[phone_regex],
        max_length=17,
        verbose_name="Mobile Number"
    )
    event_name = models.CharField(
        max_length=200,
        verbose_name="Event Name"
    )
    event_date = models.DateTimeField(
        verbose_name="Event Date"
    )
    verification_token = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Verification Token"
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name="Is Verified"
    )
    privacy_agreement_accepted = models.BooleanField(
        default=False,
        verbose_name="Privacy Agreement Accepted",
        help_text="Whether the user accepted the privacy policy and terms of service"
    )
    marketing_consent = models.BooleanField(
        default=False,
        verbose_name="Marketing Consent",
        help_text="Whether the user consented to receive marketing communications"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        verbose_name="Expires At",
        help_text="When this registration request expires"
    )

    class Meta:
        db_table = 'registration_requests'
        verbose_name = 'Registration Request'
        verbose_name_plural = 'Registration Requests'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} - {self.event_name}"

    def is_expired(self):
        """Check if the registration request has expired"""
        return timezone.now() > self.expires_at

    def save(self, *args, **kwargs):
        # Set expiration time to 24 hours from creation if not set
        if not self.expires_at:
            from datetime import timedelta
            self.expires_at = timezone.now() + timedelta(hours=24)
        
        # Generate verification token if not set
        if not self.verification_token:
            import uuid
            self.verification_token = str(uuid.uuid4())
        
        super().save(*args, **kwargs)
