# Authentication System - Events Management

## 🔐 Overview
The Events Management System now requires user authentication for all dashboard functionality. Users must register, verify their email, and log in to access any administrative features.

## 🚀 Authentication Flow

### 1. **Public Access (No Login Required)**
- **Landing Page** (`/landing/`) - Registration form and service information
- **Email Verification** (`/verify-email/<token>/`) - Email verification endpoint
- **Login Page** (`/login/`) - User authentication form

### 2. **Protected Access (Login Required)**
- **Dashboard** (`/`) - Main admin interface
- **All CRUD Operations** - Pledges, Transactions, Messages, Templates
- **Bulk Operations** - Bulk reminders, exports
- **API Endpoints** - All data API calls

## 🔑 User Registration & Verification

### Registration Process:
1. **Visit Landing Page** - `/landing/`
2. **Fill Registration Form** - Full name, email, password, mobile, event details
3. **Email Verification** - Automatic email sent with verification link
4. **Account Activation** - Click verification link within 24 hours
5. **Auto-Login** - Automatically logged in after successful verification
6. **Access Dashboard** - Full access to events management system

### Password Requirements:
- Minimum 8 characters
- Password confirmation required
- Secure password hashing using Django's built-in system

## 🛡️ Security Features

### Authentication Protection:
- **Email as Username** - Uses email address instead of username
- **Custom User Model** - Extended Django AbstractUser
- **Login Required Decorators** - All admin views protected
- **Automatic Redirects** - Unauthenticated users redirected to login
- **Session Management** - Secure session handling

### Email Verification:
- **24-Hour Expiration** - Verification links expire automatically
- **Unique Tokens** - UUID-based verification tokens
- **Professional Templates** - HTML email templates with branding
- **Resend Functionality** - Users can request new verification emails

## 🎯 URL Structure

### Public URLs:
```
/landing/                    - Registration and service info
/login/                      - User login form
/logout/                     - User logout (redirects to landing)
/verify-email/<token>/       - Email verification endpoint
/resend-verification/        - Resend verification email
```

### Protected URLs (All require login):
```
/                           - Dashboard (home page)
/pledges/                   - Pledge management
/transactions/              - Transaction management  
/messages/                  - Message management
/templates/                 - Template management
/bulk-reminder/             - Bulk reminder system
/export/                    - Data exports
/api/                       - All API endpoints
```

## 🔧 Configuration

### Settings Added:
```python
# Custom User Model
AUTH_USER_MODEL = 'events.EventUser'

# Login URLs
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/landing/'
```

### Models:
- **EventUser** - Custom user model with email as username
- **RegistrationRequest** - Temporary storage for pending registrations
- **Event** - Event data linked to verified users

## 🎨 User Interface

### Navigation Updates:
- **Authentication Status** - Shows login/logout based on user status
- **Welcome Message** - Displays user's full name when logged in
- **Responsive Design** - Works on mobile and desktop
- **Material Design** - Consistent with existing interface

### Login Form Features:
- **Email-based Login** - Uses email address as username
- **Password Fields** - Secure password input
- **Remember Me** - Session persistence option
- **Error Handling** - Clear error messages
- **Registration Links** - Easy access to registration page

## 🚨 Error Handling

### Authentication Errors:
- **Invalid Credentials** - Clear error messages for wrong email/password
- **Unverified Account** - Specific message for unverified accounts
- **Expired Verification** - Handles expired verification links
- **Duplicate Registration** - Prevents duplicate email addresses

### Automatic Redirects:
- **Unauthenticated Access** - Redirects to login with `next` parameter
- **Post-Login Redirect** - Returns to intended page after login
- **Post-Logout Redirect** - Returns to landing page after logout

## 📧 Email System

### Development Configuration:
```python
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

### Production Configuration (Example):
```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
```

## 🎯 Benefits

### Security:
- ✅ Complete access control to sensitive data
- ✅ Email verification prevents fake accounts
- ✅ Secure password handling
- ✅ Session-based authentication

### User Experience:
- ✅ Smooth registration and verification process
- ✅ Professional email templates
- ✅ Automatic login after verification
- ✅ Clear navigation and status indicators

### Administrative:
- ✅ User management through Django admin
- ✅ Event ownership and isolation
- ✅ Audit trail for user actions
- ✅ Professional onboarding experience

## 🔄 Migration Notes

When deploying the authentication system:

1. **Create Migrations** - Run migrations for new user model
2. **Configure Email** - Set up email backend for production
3. **Update Settings** - Configure login URLs and user model
4. **Test Flow** - Verify registration and login process
5. **Admin Access** - Create superuser for admin access

The system is now production-ready with complete authentication and authorization!