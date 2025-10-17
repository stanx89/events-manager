from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.template.loader import render_to_string
from django.core.paginator import Paginator
from django.db import transaction
from django.urls import reverse
from .models import Pledges, Transactions, Messages, MessageTemplate
from .forms import PledgeForm, TransactionForm, MessageForm, PledgeSearchForm, TransactionSearchForm, MessageTemplateForm
from django.db.models import Sum, Q, Count, F
from .tasks import send_bulk_messages_background, send_message_background


# Home page
def index(request):
    # Dashboard data
    total_pledges = Pledges.objects.count()
    total_amount_pledged = Pledges.objects.aggregate(Sum('pledge'))['pledge__sum'] or 0
    total_amount_paid = Pledges.objects.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
    pending_pledges = Pledges.objects.filter(status__in=['new', 'pending', 'partial']).count()
    
    recent_pledges = Pledges.objects.order_by('-created_at')[:5]
    recent_transactions = Transactions.objects.order_by('-created_at')[:5]
    
    context = {
        'total_pledges': total_pledges,
        'total_amount_pledged': total_amount_pledged,
        'total_amount_paid': total_amount_paid,
        'pending_pledges': pending_pledges,
        'recent_pledges': recent_pledges,
        'recent_transactions': recent_transactions,
    }
    return render(request, 'events/index.html', context)


# Pledge Views
def pledge_list(request):
    pledges = Pledges.objects.all().order_by('-created_at')
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        pledges = pledges.filter(name__icontains=search_query)
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        pledges = pledges.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(pledges, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'events/pledge_list.html', context)


def pledge_create(request):
    is_modal = request.GET.get('modal') == '1'
    
    if request.method == 'POST':
        form = PledgeForm(request.POST)
        if form.is_valid():
            pledge = form.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'Pledge for {pledge.name} has been created successfully.',
                    'redirect': reverse('events:pledge_detail', args=[pledge.id])
                })
            else:
                messages.success(request, f'Pledge for {pledge.name} has been created successfully.')
                return redirect('events:pledge_detail', pledge_id=pledge.id)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                context = {
                    'form': form,
                    'title': 'Create New Pledge',
                    'submit_text': 'Create Pledge',
                    'is_modal': True
                }
                html = render(request, 'events/pledge_modal_form.html', context).content.decode('utf-8')
                return JsonResponse({
                    'success': False,
                    'html': html
                })
            else:
                messages.error(request, 'Please correct the errors below.')
    else:
        form = PledgeForm()
    
    context = {
        'form': form,
        'title': 'Create New Pledge',
        'submit_text': 'Create Pledge',
        'is_modal': is_modal
    }
    
    template = 'events/pledge_modal_form.html' if is_modal else 'events/pledge_form.html'
    return render(request, template, context)


def pledge_detail(request, pledge_id):
    pledge = get_object_or_404(Pledges, id=pledge_id)
    transactions = pledge.transactions.all().order_by('-created_at')
    messages_list = pledge.messages.all().order_by('-created_at')
    
    context = {
        'pledge': pledge,
        'transactions': transactions,
        'messages': messages_list,
    }
    return render(request, 'events/pledge_detail.html', context)


def pledge_edit(request, pledge_id):
    pledge = get_object_or_404(Pledges, id=pledge_id)
    is_modal = request.GET.get('modal') == '1' or request.POST.get('modal') == '1'
    
    if request.method == 'POST':
        form = PledgeForm(request.POST, instance=pledge)
        if form.is_valid():
            updated_pledge = form.save()
            if is_modal:
                return JsonResponse({
                    'success': True,
                    'message': f'Pledge for {updated_pledge.name} has been updated successfully.',
                    'redirect': reverse('events:pledge_list')
                })
            messages.success(request, f'Pledge for {updated_pledge.name} has been updated successfully.')
            return redirect('events:pledge_detail', pledge_id=updated_pledge.id)
        else:
            if is_modal:
                return JsonResponse({
                    'success': False,
                    'errors': form.errors,
                    'message': 'Please correct the errors below.'
                })
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PledgeForm(instance=pledge)
    
    context = {
        'form': form,
        'pledge': pledge,
        'title': f'Edit Pledge - {pledge.name}',
        'submit_text': 'Update Pledge'
    }
    
    if is_modal:
        return render(request, 'events/pledge_modal_form.html', context)
    return render(request, 'events/pledge_form.html', context)


def pledge_delete(request, pledge_id):
    pledge = get_object_or_404(Pledges, id=pledge_id)
    if request.method == 'POST':
        pledge.delete()
        messages.success(request, f'Pledge for {pledge.name} has been deleted.')
        return redirect('events:pledge_list')
    
    context = {'pledge': pledge}
    return render(request, 'events/pledge_confirm_delete.html', context)


# Transaction Views
def transaction_list(request):
    transactions = Transactions.objects.select_related('pledge').order_by('-created_at')
    search_form = TransactionSearchForm(request.GET or None)
    
    # Handle direct search parameters from template
    name_search = request.GET.get('name')
    transaction_id_search = request.GET.get('transaction_id')
    method_filter = request.GET.get('method')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Apply filters
    if name_search:
        transactions = transactions.filter(pledge__name__icontains=name_search)
    
    if transaction_id_search:
        transactions = transactions.filter(transaction_id__icontains=transaction_id_search)
    
    if method_filter:
        transactions = transactions.filter(method=method_filter)
    
    if date_from:
        transactions = transactions.filter(created_at__date__gte=date_from)
    
    if date_to:
        transactions = transactions.filter(created_at__date__lte=date_to)
    
    # Also handle the search form if it's valid (for backward compatibility)
    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search')
        if search_query:
            transactions = transactions.filter(
                Q(transaction_id__icontains=search_query) |
                Q(pledge__name__icontains=search_query)
            )
        
        form_method_filter = search_form.cleaned_data.get('method')
        if form_method_filter and not method_filter:  # Only apply if not already filtered
            transactions = transactions.filter(method=form_method_filter)
    
    # Pagination
    paginator = Paginator(transactions, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate total amount for current page
    total_amount = sum(transaction.amount for transaction in page_obj.object_list)
    
    # Get all pledges for the transaction modal selector
    all_pledges = Pledges.objects.all().order_by('name')
    
    context = {
        'page_obj': page_obj,
        'search_form': search_form,
        'all_pledges': all_pledges,
        'total_amount': total_amount,
    }
    return render(request, 'events/transaction_list.html', context)


def transaction_create(request):
    pledge_id = request.GET.get('pledge_id')
    is_modal = request.GET.get('modal') == '1'
    
    if request.method == 'POST':
        # Also check for pledge_id in POST data (hidden field)
        post_pledge_id = request.POST.get('pledge')
        if post_pledge_id:
            pledge_id = post_pledge_id
        

        
        form = TransactionForm(request.POST, pledge_id=pledge_id)
        if form.is_valid():
            with transaction.atomic():
                new_transaction = form.save()
                
                # Verify pledge is properly set
                if not hasattr(new_transaction, 'pledge') or not new_transaction.pledge:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': False,
                            'message': 'Error: Transaction created but pledge assignment failed.'
                        })
                    else:
                        messages.error(request, 'Error: Transaction created but pledge assignment failed.')
                        return redirect('events:transaction_list')
                
                # Update pledge amount_paid and status
                pledge = new_transaction.pledge
                total_paid = pledge.transactions.aggregate(Sum('amount'))['amount__sum'] or 0
                pledge.amount_paid = total_paid
                
                # Update status based on amount paid
                if total_paid >= pledge.pledge:
                    pledge.status = 'completed'
                elif total_paid > 0:
                    pledge.status = 'partial'
                else:
                    pledge.status = 'pending'
                
                pledge.save()
                
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'Transaction recorded successfully. Transaction ID: {new_transaction.transaction_id}',
                    'redirect': reverse('events:transaction_detail', args=[new_transaction.id])
                })
            else:
                messages.success(request, f'Transaction recorded successfully. Transaction ID: {new_transaction.transaction_id}')
                return redirect('events:transaction_detail', transaction_id=new_transaction.id)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                context = {
                    'form': form,
                    'title': 'Record New Transaction',
                    'submit_text': 'Record Transaction',
                    'is_modal': True,
                    'pledge_id': pledge_id
                }
                html = render(request, 'events/transaction_modal_form.html', context).content.decode('utf-8')
                return JsonResponse({
                    'success': False,
                    'html': html
                })
            else:
                messages.error(request, 'Please correct the errors below.')
    else:
        form = TransactionForm(pledge_id=pledge_id)
    
    context = {
        'form': form,
        'title': 'Record New Transaction',
        'submit_text': 'Record Transaction',
        'is_modal': is_modal,
        'pledge_id': pledge_id
    }
    
    template = 'events/transaction_modal_form.html' if is_modal else 'events/transaction_form.html'
    return render(request, template, context)


def transaction_detail(request, transaction_id):
    transaction = get_object_or_404(Transactions, id=transaction_id)
    context = {'transaction': transaction}
    return render(request, 'events/transaction_detail.html', context)


def pledge_transactions(request, pledge_id):
    pledge = get_object_or_404(Pledges, id=pledge_id)
    transactions = pledge.transactions.all().order_by('-created_at')
    
    context = {
        'pledge': pledge,
        'transactions': transactions,
    }
    return render(request, 'events/pledge_transactions.html', context)


# Message Views
def message_list(request):
    messages_list = Messages.objects.select_related('pledge').order_by('-created_at')
    
    # Handle search parameters
    search_query = request.GET.get('search')
    if search_query:
        messages_list = messages_list.filter(pledge__name__icontains=search_query)
    
    # Filter by method
    method_filter = request.GET.get('method')
    if method_filter:
        messages_list = messages_list.filter(method=method_filter)
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        messages_list = messages_list.filter(status=status_filter)
    
    # Filter by message content
    message_content = request.GET.get('message_content')
    if message_content:
        messages_list = messages_list.filter(message__icontains=message_content)
    
    paginator = Paginator(messages_list, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {'page_obj': page_obj}
    return render(request, 'events/message_list.html', context)


def message_create(request):
    pledge_id = request.GET.get('pledge_id')
    is_modal = request.GET.get('modal') == '1'
    
    if request.method == 'POST':
        form = MessageForm(request.POST, pledge_id=pledge_id)
        if form.is_valid():
            message = form.save(commit=False)
            message.status = 'queued'  # Set initial status as queued
            message.save()
            
            # Start background sending
            send_message_background(message.id)
            
            if is_modal and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'Message queued for sending via {message.get_method_display()}.',
                    'redirect': reverse('events:message_detail', args=[message.id])
                })
            else:
                messages.success(request, f'Message queued for sending via {message.get_method_display()}.')
                return redirect('events:message_detail', message_id=message.id)
        else:
            if is_modal and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                context = {
                    'form': form,
                    'title': 'Create New Message',
                    'submit_text': 'Send Message',
                    'pledge_id': pledge_id
                }
                html = render_to_string('events/message_modal_form.html', context, request=request)
                return JsonResponse({'success': False, 'html': html})
            else:
                messages.error(request, 'Please correct the errors below.')
    else:
        form = MessageForm(pledge_id=pledge_id)
    
    context = {
        'form': form,
        'title': 'Create New Message',
        'submit_text': 'Send Message',
        'pledge_id': pledge_id
    }
    
    if is_modal:
        return render(request, 'events/message_modal_form.html', context)
    else:
        return render(request, 'events/message_form.html', context)


def message_detail(request, message_id):
    message = get_object_or_404(Messages, id=message_id)
    context = {'message': message}
    return render(request, 'events/message_detail.html', context)


def pledge_messages(request, pledge_id):
    pledge = get_object_or_404(Pledges, id=pledge_id)
    messages_list = pledge.messages.all().order_by('-created_at')
    
    context = {
        'pledge': pledge,
        'messages': messages_list,
    }
    return render(request, 'events/pledge_messages.html', context)


# API Views (for future use)
def api_pledges(request):
    pledges = Pledges.objects.all()
    data = []
    for pledge in pledges:
        data.append({
            'id': pledge.id,
            'name': pledge.name,
            'event_id': pledge.event_id,
            'pledge': str(pledge.pledge),
            'amount_paid': str(pledge.amount_paid),
            'status': pledge.status,
        })
    return JsonResponse({'pledges': data})


def api_transactions(request):
    transactions = Transactions.objects.all()
    data = []
    for transaction in transactions:
        data.append({
            'id': transaction.id,
            'pledge_id': transaction.pledge.id,
            'amount': str(transaction.amount),
            'method': transaction.method,
            'transaction_id': transaction.transaction_id,
        })
    return JsonResponse({'transactions': data})


def api_messages(request):
    messages_list = Messages.objects.all()
    data = []
    for message in messages_list:
        data.append({
            'id': message.id,
            'pledge_id': message.pledge.id,
            'method': message.method,
            'status': message.status,
            'created_at': message.created_at.isoformat(),
        })
    return JsonResponse({'messages': data})


# Additional Utility Views
def pledge_status_update(request, pledge_id):
    """AJAX view to update pledge status"""
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        pledge = get_object_or_404(Pledges, id=pledge_id)
        new_status = request.POST.get('status')
        
        if new_status in dict(Pledges.STATUS_CHOICES):
            pledge.status = new_status
            pledge.save()
            return JsonResponse({
                'success': True,
                'message': f'Status updated to {pledge.get_status_display()}'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Invalid status'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})


def pledge_whatsapp_status_update(request, pledge_id):
    """AJAX view to update WhatsApp status"""
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        pledge = get_object_or_404(Pledges, id=pledge_id)
        new_status = request.POST.get('whatsapp_status')
        
        if new_status in dict(Pledges.WHATSAPP_STATUS_CHOICES):
            pledge.whatsapp_status = new_status
            pledge.save()
            return JsonResponse({
                'success': True,
                'message': f'WhatsApp status updated to {pledge.get_whatsapp_status_display()}'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Invalid WhatsApp status'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})


def dashboard_stats(request):
    """API endpoint for dashboard statistics"""
    stats = {
        'total_pledges': Pledges.objects.count(),
        'total_amount_pledged': float(Pledges.objects.aggregate(Sum('pledge'))['pledge__sum'] or 0),
        'total_amount_paid': float(Pledges.objects.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0),
        'pending_pledges': Pledges.objects.filter(status__in=['new', 'pending', 'partial']).count(),
        'completed_pledges': Pledges.objects.filter(status='completed').count(),
        'cancelled_pledges': Pledges.objects.filter(status='cancelled').count(),
        'total_transactions': Transactions.objects.count(),
        'total_messages': Messages.objects.count(),
    }
    
    # Calculate completion percentage
    if stats['total_amount_pledged'] > 0:
        stats['completion_percentage'] = round(
            (stats['total_amount_paid'] / stats['total_amount_pledged']) * 100, 2
        )
    else:
        stats['completion_percentage'] = 0
    
    return JsonResponse(stats)


def export_pledges_csv(request):
    """Export pledges data to CSV"""
    import csv
    from django.http import HttpResponse
    from datetime import datetime
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="pledges_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Event ID', 'Name', 'Mobile Number', 'Pledge Amount', 
        'Amount Paid', 'Balance', 'Status', 'WhatsApp Status', 
        'Created At', 'Updated At'
    ])
    
    for pledge in Pledges.objects.all():
        balance = pledge.pledge - pledge.amount_paid
        writer.writerow([
            pledge.id,
            pledge.event_id,
            pledge.name,
            pledge.mobile_number,
            pledge.pledge,
            pledge.amount_paid,
            balance,
            pledge.get_status_display(),
            pledge.get_whatsapp_status_display(),
            pledge.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            pledge.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
        ])
    
    return response


def bulk_reminder_send(request):
    """View to send bulk reminders with automatic processing"""
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'auto_process':
            # Process pledges according to the specified logic
            new_pledges = Pledges.objects.filter(status='new')
            pending_pledges = Pledges.objects.filter(status='pending')
            
            created_messages = []
            message_ids = []
            completed_pledges = []
            processed_new_pledges = []
            
            # Process NEW pledges - send message using new template
            try:
                new_template = MessageTemplate.objects.filter(type='new_pledge', is_active=True).first()
                if new_template and new_pledges.exists():
                    for pledge in new_pledges:
                        # Determine sending method based on WhatsApp status
                        send_method = 'whatsapp' if pledge.whatsapp_status else 'sms'
                        
                        message = Messages.objects.create(
                            pledge=pledge,
                            message=new_template.get_formatted_message(pledge),
                            method=send_method,
                            status='queued'
                        )
                        created_messages.append(message)
                        message_ids.append(message.id)
                        
                        # Change status from 'new' to 'pending'
                        pledge.status = 'pending'
                        pledge.save()
                        processed_new_pledges.append(pledge)
            except Exception as e:
                messages.error(request, f'Error processing new pledges: {str(e)}')
            
            # Process PENDING pledges (excluding the ones we just changed from 'new' to 'pending')
            processed_new_ids = [p.id for p in processed_new_pledges]
            pending_pledges_to_process = pending_pledges.exclude(id__in=processed_new_ids)
            
            for pledge in pending_pledges_to_process:
                # Determine sending method based on WhatsApp status
                send_method = 'whatsapp' if pledge.whatsapp_status else 'sms'
                
                if pledge.balance() == 0:
                    # If balance is zero, send completed message and mark as completed
                    try:
                        completed_template = MessageTemplate.objects.filter(type='pledge_completed', is_active=True).first()
                        if completed_template:
                            message = Messages.objects.create(
                                pledge=pledge,
                                message=completed_template.get_formatted_message(pledge),
                                method=send_method,
                                status='queued'
                            )
                            created_messages.append(message)
                            message_ids.append(message.id)
                    except Exception as e:
                        messages.error(request, f'Error processing completed message for {pledge.name}: {str(e)}')
                    
                    # Mark as completed
                    pledge.status = 'completed'
                    pledge.save()
                    completed_pledges.append(pledge)
                else:
                    # Send reminder message using reminder template
                    try:
                        reminder_template = MessageTemplate.objects.filter(type='reminder', is_active=True).first()
                        if reminder_template:
                            message = Messages.objects.create(
                                pledge=pledge,
                                message=reminder_template.get_formatted_message(pledge),
                                method=send_method,
                                status='queued'
                            )
                            created_messages.append(message)
                            message_ids.append(message.id)
                    except Exception as e:
                        messages.error(request, f'Error processing reminder for {pledge.name}: {str(e)}')
            
            # Start background processing for messages
            if message_ids:
                send_bulk_messages_background(message_ids)
            
            # Prepare success message
            success_parts = []
            if len(created_messages) > 0:
                success_parts.append(f'{len(created_messages)} messages queued for sending')
            if len(completed_pledges) > 0:
                success_parts.append(f'{len(completed_pledges)} pledges marked as completed')
            if len(processed_new_pledges) > 0:
                success_parts.append(f'{len(processed_new_pledges)} new pledges updated to pending status')
            
            if success_parts:
                messages.success(request, '. '.join(success_parts) + '.')
            else:
                messages.info(request, 'No pledges found that need processing.')
                
            return redirect('events:message_list')
        
        # Original manual processing logic (if needed)
        pledge_ids = request.POST.getlist('pledge_ids')
        message_text = request.POST.get('message')
        method = 'sms'  # Default method for reminders
        
        if pledge_ids and message_text:
            created_messages = []
            message_ids = []
            
            for pledge_id in pledge_ids:
                try:
                    pledge = Pledges.objects.get(id=pledge_id)
                    message = Messages.objects.create(
                        pledge=pledge,
                        message=message_text,
                        method=method,
                        status='queued'
                    )
                    created_messages.append(message)
                    message_ids.append(message.id)
                except Pledges.DoesNotExist:
                    continue
            
            if message_ids:
                send_bulk_messages_background(message_ids)
                messages.success(request, f'Queued {len(created_messages)} reminders for sending.')
            else:
                messages.warning(request, 'No valid reminders were created.')
                
            return redirect('events:message_list')
        else:
            messages.error(request, 'Please fill in all required fields.')
    
    # Get statistics for display
    new_count = Pledges.objects.filter(status='new').count()
    pending_count = Pledges.objects.filter(status='pending').count()
    pending_zero_balance = Pledges.objects.filter(status='pending', amount_paid__gte=F('pledge')).count()
    pending_with_balance = pending_count - pending_zero_balance
    
    # Get sample messages for display
    new_template = MessageTemplate.objects.filter(type='new_pledge', is_active=True).first()
    reminder_template = MessageTemplate.objects.filter(type='reminder', is_active=True).first()
    completed_template = MessageTemplate.objects.filter(type='pledge_completed', is_active=True).first()
    
    new_sample_message = new_template.preview() if new_template else "Welcome! Thank you for your pledge of {pledge_amount}. We appreciate your commitment to {event_id}."
    reminder_sample_message = reminder_template.preview() if reminder_template else "Hello {name}, this is a reminder about your pending pledge balance of {balance} for {event_id}. Please complete your payment when convenient."
    completed_sample_message = completed_template.preview() if completed_template else "Congratulations {name}! Your pledge of {pledge_amount} for {event_id} has been completed. Thank you for your commitment!"
    
    context = {
        'new_count': new_count,
        'pending_count': pending_count,
        'pending_zero_balance': pending_zero_balance,
        'pending_with_balance': pending_with_balance,
        'new_sample_message': new_sample_message,
        'reminder_sample_message': reminder_sample_message,
        'completed_sample_message': completed_sample_message,
    }
    return render(request, 'events/bulk_reminder.html', context)


def message_queue_status(request):
    """API endpoint to check message queue status"""
    status_counts = Messages.objects.values('status').annotate(count=Count('id'))
    
    # Convert to dictionary for easier handling
    status_dict = {item['status']: item['count'] for item in status_counts}
    
    # Ensure all statuses are represented
    all_statuses = ['queued', 'pending', 'sent', 'delivered', 'failed', 'read']
    for status in all_statuses:
        if status not in status_dict:
            status_dict[status] = 0
    
    # Get recent activity (last 24 hours)
    from datetime import timedelta
    from django.utils import timezone
    
    recent_messages = Messages.objects.filter(
        created_at__gte=timezone.now() - timedelta(hours=24)
    ).count()
    
    return JsonResponse({
        'status': 'success',
        'queue_status': status_dict,
        'total_messages': sum(status_dict.values()),
        'recent_activity_24h': recent_messages,
        'last_updated': timezone.now().isoformat()
    })


# Message Template Views
def template_list(request):
    """View to list all message templates"""
    templates = MessageTemplate.objects.all().order_by('event_id', 'type', 'name')
    
    # Filter by event_id
    event_filter = request.GET.get('event_id')
    if event_filter:
        templates = templates.filter(event_id__icontains=event_filter)
    
    # Filter by type
    type_filter = request.GET.get('type')
    if type_filter:
        templates = templates.filter(type=type_filter)
    
    # Filter by active status
    active_filter = request.GET.get('active')
    if active_filter:
        is_active = active_filter.lower() == 'true'
        templates = templates.filter(is_active=is_active)
    
    context = {
        'templates': templates,
        'template_types': MessageTemplate.TEMPLATE_TYPES,
        'current_filters': {
            'event_id': event_filter or '',
            'type': type_filter or '',
            'active': active_filter or '',
        }
    }
    return render(request, 'events/template_list.html', context)


def template_create(request):
    """View to create a new message template"""
    if request.method == 'POST':
        form = MessageTemplateForm(request.POST)
        if form.is_valid():
            template = form.save(commit=False)
            # Set default event_id since it's no longer in the form
            template.event_id = 'DEFAULT'
            # Auto-generate name based on type only (since no event_id)
            template.name = f"{template.get_type_display()}"
            # Set as active by default
            template.is_active = True
            template.save()
            messages.success(request, f'Template "{template.name}" created successfully!')
            return redirect('events:template_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = MessageTemplateForm()
    
    context = {
        'form': form,
        'title': 'Create Message Template',
        'action': 'Create'
    }
    return render(request, 'events/template_form.html', context)


def template_edit(request, template_id):
    """View to edit an existing message template"""
    template = get_object_or_404(MessageTemplate, id=template_id)
    
    if request.method == 'POST':
        form = MessageTemplateForm(request.POST, instance=template)
        if form.is_valid():
            template = form.save(commit=False)
            # Keep existing event_id if it exists, otherwise set default
            if not template.event_id:
                template.event_id = 'DEFAULT'
            # Auto-generate name based on type only (since no event_id in form)
            template.name = f"{template.get_type_display()}"
            # Preserve existing is_active status (don't change it)
            template.save()
            messages.success(request, f'Template "{template.name}" updated successfully!')
            return redirect('events:template_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = MessageTemplateForm(instance=template)
    
    context = {
        'form': form,
        'template': template,
        'title': f'Edit Template: {template.name}',
        'action': 'Update'
    }
    return render(request, 'events/template_form.html', context)


def template_detail(request, template_id):
    """View to show template details and preview"""
    template = get_object_or_404(MessageTemplate, id=template_id)
    
    # Get a sample pledge for preview
    sample_pledge = Pledges.objects.filter(event_id=template.event_id).first()
    if not sample_pledge:
        sample_pledge = Pledges.objects.first()
    
    preview_message = template.preview(sample_pledge)
    
    context = {
        'template': template,
        'preview_message': preview_message,
        'sample_pledge': sample_pledge,
    }
    return render(request, 'events/template_detail.html', context)


def template_delete(request, template_id):
    """View to delete a message template"""
    template = get_object_or_404(MessageTemplate, id=template_id)
    
    if request.method == 'POST':
        template_name = template.name
        template.delete()
        messages.success(request, f'Template "{template_name}" deleted successfully!')
        return redirect('events:template_list')
    
    context = {
        'template': template,
    }
    return render(request, 'events/template_confirm_delete.html', context)


def template_toggle_active(request, template_id):
    """AJAX view to toggle template active status"""
    if request.method == 'POST':
        template = get_object_or_404(MessageTemplate, id=template_id)
        template.is_active = not template.is_active
        template.save()
        
        return JsonResponse({
            'success': True,
            'is_active': template.is_active,
            'message': f'Template "{template.name}" {"activated" if template.is_active else "deactivated"}.'
        })
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})


def api_templates(request):
    """API endpoint to get templates for a specific event and type"""
    event_id = request.GET.get('event_id')
    template_type = request.GET.get('type')
    
    templates = MessageTemplate.objects.filter(is_active=True)
    
    if event_id:
        templates = templates.filter(event_id=event_id)
    
    if template_type:
        templates = templates.filter(type=template_type)
    
    data = []
    for template in templates:
        data.append({
            'id': template.id,
            'name': template.name,
            'message': template.message,
            'type': template.type,
            'event_id': template.event_id,
        })
    
    return JsonResponse({'templates': data})
