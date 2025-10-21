from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Pledges, Transactions, Messages, MessageTemplate, Event, EventUser, RegistrationRequest

# Register your models here.

@admin.register(Pledges)
class PledgesAdmin(admin.ModelAdmin):
    list_display = ['name', 'event_id', 'pledge', 'amount_paid', 'status', 'created_at']
    list_filter = ['status', 'event_id', 'whatsapp_status']
    search_fields = ['name', 'mobile_number', 'event_id']
    ordering = ['-created_at']

@admin.register(Transactions)
class TransactionsAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'pledge', 'amount', 'method', 'created_at']
    list_filter = ['method', 'created_at']
    search_fields = ['transaction_id', 'pledge__name']
    ordering = ['-created_at']

@admin.register(Messages)
class MessagesAdmin(admin.ModelAdmin):
    list_display = ['pledge', 'method', 'status', 'created_at']
    list_filter = ['method', 'status', 'created_at']
    search_fields = ['pledge__name', 'message']
    ordering = ['-created_at']

@admin.register(MessageTemplate)
class MessageTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'event_id', 'type', 'is_active', 'created_at']
    list_filter = ['type', 'event_id', 'is_active', 'created_at']
    search_fields = ['name', 'event_id', 'message']
    ordering = ['event_id', 'type', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('event_id', 'name', 'type', 'is_active')
        }),
        ('Template Content', {
            'fields': ('message',),
            'description': 'Available placeholders: {name}, {pledge_amount}, {amount_paid}, {balance}, {event_id}, {mobile}, {status}'
        }),
    )

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['name', 'date', 'created_by', 'is_active', 'created_at']
    list_filter = ['is_active', 'date', 'created_at']
    search_fields = ['name', 'description', 'location', 'created_by__full_name']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Event Information', {
            'fields': ('name', 'date', 'description', 'location')
        }),
        ('Settings', {
            'fields': ('created_by', 'is_active')
        }),
    )

@admin.register(EventUser)
class EventUserAdmin(UserAdmin):
    list_display = ['email', 'full_name', 'is_verified', 'is_active', 'date_joined']
    list_filter = ['is_verified', 'is_active', 'date_joined']
    search_fields = ['email', 'full_name', 'mobile_number']
    ordering = ['-date_joined']
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'mobile_number')}),
        ('Verification', {'fields': ('is_verified', 'verification_token', 'verification_sent_at')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'mobile_number', 'password1', 'password2'),
        }),
    )

@admin.register(RegistrationRequest)
class RegistrationRequestAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'email', 'event_name', 'event_date', 'is_verified', 'created_at', 'expires_at']
    list_filter = ['is_verified', 'created_at', 'expires_at']
    search_fields = ['full_name', 'email', 'event_name']
    ordering = ['-created_at']
    readonly_fields = ['verification_token', 'expires_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('full_name', 'email', 'mobile_number')
        }),
        ('Event Information', {
            'fields': ('event_name', 'event_date')
        }),
        ('Verification', {
            'fields': ('is_verified', 'verification_token', 'expires_at')
        }),
    )
