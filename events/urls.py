from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    # Home page
    path('', views.index, name='index'),
    
    # Pledges URLs
    path('pledges/', views.pledge_list, name='pledge_list'),
    path('pledges/create/', views.pledge_create, name='pledge_create'),
    path('pledges/<int:pledge_id>/', views.pledge_detail, name='pledge_detail'),
    path('pledges/<int:pledge_id>/edit/', views.pledge_edit, name='pledge_edit'),
    path('pledges/<int:pledge_id>/delete/', views.pledge_delete, name='pledge_delete'),
    
    # Transactions URLs
    path('transactions/', views.transaction_list, name='transaction_list'),
    path('transactions/create/', views.transaction_create, name='transaction_create'),
    path('pledges/<int:pledge_id>/transactions/', views.pledge_transactions, name='pledge_transactions'),
    path('transactions/<int:transaction_id>/', views.transaction_detail, name='transaction_detail'),
    
    # Messages URLs
    path('messages/', views.message_list, name='message_list'),
    path('messages/create/', views.message_create, name='message_create'),
    path('pledges/<int:pledge_id>/messages/', views.pledge_messages, name='pledge_messages'),
    path('messages/<int:message_id>/', views.message_detail, name='message_detail'),
    
    # Message Templates URLs
    path('templates/', views.template_list, name='template_list'),
    path('templates/create/', views.template_create, name='template_create'),
    path('templates/<int:template_id>/', views.template_detail, name='template_detail'),
    path('templates/<int:template_id>/edit/', views.template_edit, name='template_edit'),
    path('templates/<int:template_id>/delete/', views.template_delete, name='template_delete'),
    path('templates/<int:template_id>/toggle-active/', views.template_toggle_active, name='template_toggle_active'),
    
    # Utility URLs
    path('pledges/<int:pledge_id>/status-update/', views.pledge_status_update, name='pledge_status_update'),
    path('pledges/<int:pledge_id>/whatsapp-status-update/', views.pledge_whatsapp_status_update, name='pledge_whatsapp_status_update'),
    path('bulk-reminder/', views.bulk_reminder_send, name='bulk_reminder_send'),
    path('export/pledges/', views.export_pledges_csv, name='export_pledges_csv'),
    
    # API endpoints
    path('api/pledges/', views.api_pledges, name='api_pledges'),
    path('api/transactions/', views.api_transactions, name='api_transactions'),
    path('api/messages/', views.api_messages, name='api_messages'),
    path('api/templates/', views.api_templates, name='api_templates'),
    path('api/dashboard-stats/', views.dashboard_stats, name='dashboard_stats'),
    path('api/message-queue-status/', views.message_queue_status, name='message_queue_status'),
]