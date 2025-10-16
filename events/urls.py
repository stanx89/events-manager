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
    
    # Utility URLs
    path('pledges/<int:pledge_id>/status-update/', views.pledge_status_update, name='pledge_status_update'),
    path('pledges/<int:pledge_id>/whatsapp-status-update/', views.pledge_whatsapp_status_update, name='pledge_whatsapp_status_update'),
    path('bulk-message/', views.bulk_message_send, name='bulk_message_send'),
    path('export/pledges/', views.export_pledges_csv, name='export_pledges_csv'),
    
    # API endpoints
    path('api/pledges/', views.api_pledges, name='api_pledges'),
    path('api/transactions/', views.api_transactions, name='api_transactions'),
    path('api/messages/', views.api_messages, name='api_messages'),
    path('api/dashboard-stats/', views.dashboard_stats, name='dashboard_stats'),
]