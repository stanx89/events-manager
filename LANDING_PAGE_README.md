# Events Management System with Landing Page

A comprehensive Django-based events management system with user registration, email verification, and landing page functionality.

## 🚀 New Features Added

### Landing Page & Registration System
- **Beautiful Landing Page** - Modern, responsive design with service information
- **User Registration** - Complete registration form with validation
- **Email Verification** - Secure email verification system with expiration
- **Automatic Account Creation** - Creates user and event automatically after verification
- **Responsive Design** - Works perfectly on mobile and desktop

## 📁 Recent Changes

### New Models Added:
1. **Event** - Stores event information
2. **EventUser** - Manages event organizers
3. **RegistrationRequest** - Handles pending registrations with email verification

### New Views:
- `landing_page` - Main landing page with registration form
- `verify_email` - Email verification handler
- `resend_verification` - Resend verification emails

### New Templates:
- `landing_page.html` - Modern landing page with Tailwind CSS
- `verification_email.html` - Professional email template

## 🌐 URLs

| URL | Description |
|-----|-------------|
| `/landing/` | Landing page with registration form |
| `/verify-email/<token>/` | Email verification endpoint |
| `/resend-verification/` | Resend verification email |
| `/` | Main dashboard (after login) |
| `/admin/` | Admin interface |

## 🎯 How It Works

### Registration Flow:
1. **Visit Landing Page** - User fills out registration form
2. **Email Sent** - Verification email with 24-hour expiration
3. **Email Verification** - User clicks link to verify email
4. **Account Creation** - System creates EventUser and Event automatically
5. **Redirect to Dashboard** - User can start managing pledges

### Features:
- ✅ Email verification with expiration (24 hours)
- ✅ Duplicate email validation
- ✅ Professional email templates
- ✅ Mobile-responsive design
- ✅ Integration with existing pledge system
- ✅ Admin interface for all models

## 📧 Email Configuration

Currently configured for development (console backend):
```python
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

For production, update settings.py:
```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
```

## 🛠 Setup Instructions

### 1. Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 2. Create Superuser (Optional)
```bash
python manage.py createsuperuser
```

### 3. Start Development Server
```bash
python manage.py runserver
```

### 4. Test the System
```bash
# Test landing page functionality
python manage.py test_landing

# Test with email sending
python manage.py test_landing --test-email your@email.com
```

## 📱 Landing Page Features

### Hero Section
- Eye-catching gradient background
- Clear value proposition
- Call-to-action buttons

### Statistics Display
- Live counts of events, users, and pledges
- Builds trust and credibility

### Features Section
- 6 key features highlighted with icons
- Pledge management, WhatsApp/SMS, analytics, etc.

### Registration Form
- Comprehensive form with validation
- Mobile-responsive design
- Clear error messages and help text

### How It Works
- 3-step process explanation
- Visual step indicators

## 🔧 Technical Details

### Models:
- **EventUser**: Manages event organizers with email verification
- **Event**: Stores event details linked to users
- **RegistrationRequest**: Temporary storage for pending registrations

### Security:
- CSRF protection on all forms
- Email verification with UUID tokens
- 24-hour expiration on verification links
- Duplicate email prevention

### Integration:
- Seamless integration with existing pledge system
- Shared Material Design styling
- Compatible with WhatsApp messaging features

## 🎨 Design

The landing page uses:
- **Tailwind CSS** for responsive styling
- **Material Design** principles for consistency
- **Gradient backgrounds** for modern appeal
- **Icon integration** for visual hierarchy
- **Professional typography** for readability

## 📊 Admin Interface

All new models are registered in Django admin with:
- List views with filtering and search
- Detailed fieldsets for organization
- Read-only fields for sensitive data
- Proper ordering and display

## 🚀 Next Steps

1. **Configure Email Provider** - Set up SMTP for production
2. **Domain Configuration** - Update SITE_ID and domain settings
3. **Email Templates** - Customize verification email branding
4. **Analytics** - Track registration conversions
5. **User Dashboard** - Create user-specific event management interface

## 📞 Support

The system is now ready for production use. Users can:
1. Register for events via the landing page
2. Receive professional verification emails
3. Access the full pledge management system
4. Send automated WhatsApp/SMS reminders

All existing functionality remains intact and enhanced!