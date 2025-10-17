from django.contrib import admin
from .models import Pledges, Transactions, Messages, MessageTemplate

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
