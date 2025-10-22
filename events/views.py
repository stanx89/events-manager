from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from django.core.paginator import Paginator
from django.db import transaction
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from .models import Pledges, Transactions, Messages, MessageTemplate, RegistrationRequest, Event, EventUser
from .forms import PledgeForm, TransactionForm, MessageForm, PledgeSearchForm, TransactionSearchForm, MessageTemplateForm
from django.db.models import Sum, Q, Count, F
from .tasks import send_bulk_messages_background, send_message_background


def get_base_context(request):
    """
    Get base context for all views including events and selected event
    """
    context = {}
    if request.user.is_authenticated:
        # Get user's events
        events = Event.objects.filter(created_by=request.user, is_active=True).order_by('-date', 'name')
        context['events'] = events
        
        # Get selected event
        selected_event_id = request.session.get('selected_event_id')
        selected_event = None
        
        if selected_event_id:
            try:
                selected_event = Event.objects.get(id=selected_event_id, created_by=request.user, is_active=True)
            except Event.DoesNotExist:
                # Clear invalid event from session
                request.session.pop('selected_event_id', None)
        
        # If no selected event and user has events, select the first one
        if not selected_event and events.exists():
            selected_event = events.first()
            request.session['selected_event_id'] = selected_event.id
        
        context['selected_event'] = selected_event
    
    return context


# Home page - requires login
@login_required
def index(request):
    # Redirect to dashboard view to maintain consistent event-based filtering
    return redirect('events:dashboard')


# Pledge Views - all require login
@login_required
def pledge_list(request):
    # Get base context (events and selected event)
    context = get_base_context(request)
    selected_event = context.get('selected_event')
    user_events = context.get('events')
    user_event_names = [event.name for event in user_events] if user_events else []
    
    # Filter pledges by selected event or all user events
    if selected_event:
        pledges = Pledges.objects.filter(event_id=selected_event.name).order_by('-created_at')
    else:
        pledges = Pledges.objects.filter(event_id__in=user_event_names).order_by('-created_at')
    
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
    
    context.update({
        'page_obj': page_obj,
    })
    return render(request, 'events/pledge_list.html', context)


@login_required
def pledge_create(request):
    is_modal = request.GET.get('modal') == '1'
    selected_event_id = request.GET.get('event_id')
    
    # Get the selected event for pre-population - only user's own events
    selected_event = None
    if selected_event_id:
        try:
            selected_event = Event.objects.get(id=selected_event_id, created_by=request.user, is_active=True)
        except Event.DoesNotExist:
            pass
    
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
                    'is_modal': True,
                    'selected_event': selected_event
                }
                html = render(request, 'events/pledge_modal_form.html', context).content.decode('utf-8')
                return JsonResponse({
                    'success': False,
                    'html': html
                })
            else:
                messages.error(request, 'Please correct the errors below.')
    else:
        # Pre-populate form with selected event
        initial_data = {}
        if selected_event:
            initial_data['event_id'] = selected_event.name
        
        form = PledgeForm(initial=initial_data)
    
    context = {
        'form': form,
        'title': 'Create New Pledge',
        'submit_text': 'Create Pledge',
        'is_modal': is_modal,
        'selected_event': selected_event
    }
    
    template = 'events/pledge_modal_form.html' if is_modal else 'events/pledge_form.html'
    return render(request, template, context)


@login_required
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


@login_required
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


@login_required
def pledge_delete(request, pledge_id):
    pledge = get_object_or_404(Pledges, id=pledge_id)
    if request.method == 'POST':
        pledge.delete()
        messages.success(request, f'Pledge for {pledge.name} has been deleted.')
        return redirect('events:pledge_list')
    
    context = {'pledge': pledge}
    return render(request, 'events/pledge_confirm_delete.html', context)


# Transaction Views
@login_required
def transaction_list(request):
    # Get base context (events and selected event)
    context = get_base_context(request)
    selected_event = context.get('selected_event')
    user_events = context.get('events')
    user_event_names = [event.name for event in user_events] if user_events else []
    
    # Filter transactions by selected event or all user events
    if selected_event:
        transactions = Transactions.objects.select_related('pledge').filter(pledge__event_id=selected_event.name).order_by('-created_at')
    else:
        transactions = Transactions.objects.select_related('pledge').filter(pledge__event_id__in=user_event_names).order_by('-created_at')
    
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
    
    # Get pledges for the transaction modal selector (filtered by user's events)
    if selected_event:
        all_pledges = Pledges.objects.filter(event_id=selected_event.name).order_by('name')
    else:
        all_pledges = Pledges.objects.filter(event_id__in=user_event_names).order_by('name')
    
    context.update({
        'page_obj': page_obj,
        'search_form': search_form,
        'all_pledges': all_pledges,
        'total_amount': total_amount,
    })
    return render(request, 'events/transaction_list.html', context)


@login_required
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


@login_required
def transaction_detail(request, transaction_id):
    transaction = get_object_or_404(Transactions, id=transaction_id)
    context = {'transaction': transaction}
    return render(request, 'events/transaction_detail.html', context)


@login_required
def pledge_transactions(request, pledge_id):
    pledge = get_object_or_404(Pledges, id=pledge_id)
    transactions = pledge.transactions.all().order_by('-created_at')
    
    context = {
        'pledge': pledge,
        'transactions': transactions,
    }
    return render(request, 'events/pledge_transactions.html', context)


# Message Views
@login_required
def message_list(request):
    # Get base context (events and selected event)
    context = get_base_context(request)
    selected_event = context.get('selected_event')
    user_events = context.get('events')
    user_event_names = [event.name for event in user_events] if user_events else []
    
    # Filter messages by selected event or all user events
    if selected_event:
        messages_list = Messages.objects.select_related('pledge').filter(pledge__event_id=selected_event.name).order_by('-created_at')
    else:
        messages_list = Messages.objects.select_related('pledge').filter(pledge__event_id__in=user_event_names).order_by('-created_at')
    
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
    
    context.update({
        'page_obj': page_obj,
    })
    return render(request, 'events/message_list.html', context)


@login_required
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


@login_required
def message_detail(request, message_id):
    message = get_object_or_404(Messages, id=message_id)
    context = {'message': message}
    return render(request, 'events/message_detail.html', context)


@login_required
def pledge_messages(request, pledge_id):
    pledge = get_object_or_404(Pledges, id=pledge_id)
    messages_list = pledge.messages.all().order_by('-created_at')
    
    context = {
        'pledge': pledge,
        'messages': messages_list,
    }
    return render(request, 'events/pledge_messages.html', context)


# API Views (for future use)
@login_required
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


@login_required
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


@login_required
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
@login_required
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


@login_required
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


@login_required
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


@login_required
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


@login_required
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


@login_required
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
@login_required
def template_list(request):
    """View to list all message templates"""
    # Get base context (events and selected event)
    context = get_base_context(request)
    
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
    
    context.update({
        'templates': templates,
        'template_types': MessageTemplate.TEMPLATE_TYPES,
        'current_filters': {
            'event_id': event_filter or '',
            'type': type_filter or '',
            'active': active_filter or '',
        }
    })
    return render(request, 'events/template_list.html', context)


@login_required
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


@login_required
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


@login_required
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


@login_required
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


@login_required
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


@login_required
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


# Landing Page and Registration Views
def landing_page(request):
    """Landing page with service information and registration form"""
    from .forms import RegistrationForm
    import logging
    import random
    
    logger = logging.getLogger(__name__)
    
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        
        # Validate CAPTCHA
        captcha_answer = request.POST.get('captcha_answer', '')
        captcha_num1 = int(request.POST.get('captcha_num1', 0))
        captcha_num2 = int(request.POST.get('captcha_num2', 0))
        captcha_operation = request.POST.get('captcha_operation', '+')
        
        # Calculate correct answer
        if captcha_operation == '+':
            correct_answer = captcha_num1 + captcha_num2
        elif captcha_operation == '-':
            correct_answer = captcha_num1 - captcha_num2
        else:
            correct_answer = captcha_num1 + captcha_num2
        
        try:
            captcha_answer_int = int(captcha_answer) if captcha_answer else 0
        except ValueError:
            captcha_answer_int = 0
        
        if not captcha_answer or captcha_answer_int != correct_answer:
            messages.error(request, 'Please solve the math problem correctly to verify you are human.')
        elif form.is_valid():
            try:
                # Save the registration request
                registration_request = form.save(commit=False)
                
                # Set a default event date since it's not collected in the form anymore
                from django.utils import timezone
                registration_request.event_date = timezone.now() + timezone.timedelta(days=30)  # Default to 30 days from now
                
                registration_request.save()
                
                logger.info(f"Registration saved for {registration_request.email} (ID: {registration_request.id})")
                
                # Send verification email
                logger.info("🚀 INITIATING REGISTRATION EMAIL PROCESS")
                logger.info(f"   Registration ID: {registration_request.id}")
                logger.info(f"   User: {registration_request.full_name}")
                logger.info(f"   Email: {registration_request.email}")
                logger.info(f"   Event: {registration_request.event_name}")
                
                email_result = send_verification_email(registration_request, request)
                
                if email_result:
                    logger.info("🎉 REGISTRATION PROCESS COMPLETED SUCCESSFULLY")
                else:
                    logger.error("💥 REGISTRATION EMAIL PROCESS FAILED")
                
                messages.success(
                    request, 
                    f'Registration successful! We have sent a verification email to {registration_request.email}. '
                    'Please check your inbox and click the verification link to activate your account.'
                )
                
            except Exception as e:
                logger.error(f"Registration process failed for {registration_request.email}: {str(e)}")
                logger.error(f"Error type: {type(e).__name__}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                
                messages.error(
                    request,
                    f'Registration saved but we had trouble sending the verification email. '
                    f'Please contact support or try registering again.'
                )
                
            return redirect('events:landing_page')
        else:
            # Display form validation errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
            if not form.errors:
                messages.error(request, 'Please correct the errors below.')
            return redirect('events:landing_page')
    else:
        form = RegistrationForm()
    
    # Service statistics for the landing page
    total_events = Event.objects.filter(is_active=True).count()
    total_users = EventUser.objects.filter(is_verified=True).count()
    total_pledges = Pledges.objects.count()
    
    # Generate CAPTCHA
    captcha_num1 = random.randint(1, 10)
    captcha_num2 = random.randint(1, 10)
    operations = ['+', '-']
    captcha_operation = random.choice(operations)
    
    # Make sure subtraction doesn't result in negative numbers
    if captcha_operation == '-' and captcha_num1 < captcha_num2:
        captcha_num1, captcha_num2 = captcha_num2, captcha_num1
    
    if captcha_operation == '+':
        captcha_question = f"{captcha_num1} + {captcha_num2} = ?"
    else:
        captcha_question = f"{captcha_num1} - {captcha_num2} = ?"
    
    context = {
        'form': form,
        'total_events': total_events,
        'total_users': total_users,
        'total_pledges': total_pledges,
        'captcha_num1': captcha_num1,
        'captcha_num2': captcha_num2,
        'captcha_operation': captcha_operation,
        'captcha_question': captcha_question,
    }
    return render(request, 'events/landing_page.html', context)


def verify_email(request, token):
    """Verify email address and create user account"""
    try:
        # Find the registration request
        registration_request = RegistrationRequest.objects.get(
            verification_token=token,
            is_verified=False
        )
        
        # Check if the token has expired
        if registration_request.is_expired():
            messages.error(
                request,
                'Verification link has expired. Please register again.'
            )
            return redirect('events:landing_page')
        
        # Create the user account
        with transaction.atomic():
            # Create EventUser with password and privacy consent
            from django.utils import timezone
            user = EventUser.objects.create_user(
                email=registration_request.email,
                full_name=registration_request.full_name,
                mobile_number=registration_request.mobile_number,
                is_verified=True,
                is_active=True,
            )
            
            # Set the password using the hashed password from registration
            user.password = registration_request.password  # This is already hashed
            user.save()
            
            # Create Event
            event = Event.objects.create(
                name=registration_request.event_name,
                date=registration_request.event_date,
                created_by=user
            )
            
            # Mark registration as verified
            registration_request.is_verified = True
            registration_request.save()
        
        messages.success(
            request,
            f'Email verified successfully! Your account has been created and your event "{event.name}" is now set up. '
            'You have been automatically logged in and can now start managing pledges for your event.'
        )
        
        # Automatically log in the user
        from django.contrib.auth import login
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        
        # Redirect to the main dashboard/index page
        return redirect('events:index')
        
    except RegistrationRequest.DoesNotExist:
        messages.error(
            request,
            'Invalid verification link. Please check the link or register again.'
        )
        return redirect('events:landing_page')


def send_verification_email(registration_request, request=None):
    """Send verification email to the user"""
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    from django.conf import settings
    from django.urls import reverse
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Start of email sending process
    logger.info("=" * 60)
    logger.info("📧 STARTING EMAIL SENDING PROCESS")
    logger.info("=" * 60)
    
    # Log email configuration for debugging
    logger.info(f"📋 Email Configuration:")
    logger.info(f"   Backend: {settings.EMAIL_BACKEND}")
    logger.info(f"   Host: {settings.EMAIL_HOST}")
    logger.info(f"   Port: {settings.EMAIL_PORT}")
    logger.info(f"   User: {settings.EMAIL_HOST_USER}")
    logger.info(f"   From: {settings.DEFAULT_FROM_EMAIL}")
    logger.info(f"   TLS: {getattr(settings, 'EMAIL_USE_TLS', False)}")
    logger.info(f"   SSL: {getattr(settings, 'EMAIL_USE_SSL', False)}")
    logger.info(f"   Timeout: {getattr(settings, 'EMAIL_TIMEOUT', 'Not set')}")
    
    # Log recipient and registration details
    logger.info(f"📤 Email Details:")
    logger.info(f"   To: {registration_request.email}")
    logger.info(f"   User: {registration_request.full_name}")
    logger.info(f"   Event: {registration_request.event_name}")
    logger.info(f"   Token: {registration_request.verification_token}")
    logger.info(f"   Created: {registration_request.created_at}")
    logger.info(f"   Expires: {registration_request.expires_at}")
    
    try:
        logger.info("🔗 Generating verification URL...")
        
        # Generate verification URL
        if request:
            verification_url = request.build_absolute_uri(
                reverse('events:verify_email', kwargs={'token': registration_request.verification_token})
            )
            logger.info(f"   Using request.build_absolute_uri()")
        else:
            # Fallback if request is not available
            from django.contrib.sites.models import Site
            current_site = Site.objects.get_current()
            verification_url = f"http://{current_site.domain}{reverse('events:verify_email', kwargs={'token': registration_request.verification_token})}"
            logger.info(f"   Using fallback with Site: {current_site.domain}")
        
        logger.info(f"   Generated URL: {verification_url}")
        
        # Prepare email content
        subject = 'Nifty Events -   Verify Your Email'
        logger.info(f"📝 Preparing email content...")
        logger.info(f"   Subject: {subject}")
        
        # HTML email template
        logger.info("🎨 Rendering HTML email template...")
        try:
            html_message = render_to_string('events/emails/verification_email.html', {
                'user_name': registration_request.full_name,
                'event_name': registration_request.event_name,
                'event_date': registration_request.event_date,
                'verification_url': verification_url,
                'expires_in_hours': 24,
            })
            logger.info(f"   ✅ HTML template rendered successfully ({len(html_message)} characters)")
        except Exception as e:
            logger.error(f"   ❌ HTML template rendering failed: {str(e)}")
            html_message = None
        
        # Plain text fallback
        plain_message = f"""
        Hi {registration_request.full_name},

        Thank you for registering with our Events Management System!

        Your Event Details:
        - Event Name: {registration_request.event_name}
        - Event Date: {registration_request.event_date.strftime('%B %d, %Y at %I:%M %p')}

        To complete your registration and activate your account, please click the link below:
        {verification_url}

        This link will expire in 24 hours.

        If you did not register for this account, please ignore this email.

        Best regards,
        Events Management Team
        """
        
        # Send email
        logger.info("📨 SENDING EMAIL...")
        logger.info(f"   From: {settings.DEFAULT_FROM_EMAIL}")
        logger.info(f"   To: [{registration_request.email}]")
        logger.info(f"   Subject: {subject}")
        logger.info(f"   Plain text length: {len(plain_message)} characters")
        logger.info(f"   HTML message: {'Yes' if html_message else 'No'}")
        logger.info(f"   Fail silently: False")
        
        # Import time to measure sending duration
        import time
        start_time = time.time()
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[registration_request.email],
            html_message=html_message,
            fail_silently=False
        )
        
        end_time = time.time()
        duration = round(end_time - start_time, 2)
        
        logger.info("=" * 60)
        logger.info("✅ EMAIL SENT SUCCESSFULLY!")
        logger.info("=" * 60)
        logger.info(f"📊 Sending Statistics:")
        logger.info(f"   Duration: {duration} seconds")
        logger.info(f"   Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"   Recipient: {registration_request.email}")
        logger.info(f"   Registration ID: {registration_request.id}")
        logger.info(f"   Token: {registration_request.verification_token}")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error("=" * 60)
        logger.error("❌ EMAIL SENDING FAILED!")
        logger.error("=" * 60)
        logger.error(f"📋 Error Details:")
        logger.error(f"   Recipient: {registration_request.email}")
        logger.error(f"   Registration ID: {registration_request.id}")
        logger.error(f"   Error Type: {type(e).__name__}")
        logger.error(f"   Error Message: {str(e)}")
        
        # Import for detailed error information
        import traceback
        import time
        
        logger.error(f"📊 Error Context:")
        logger.error(f"   Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.error(f"   Email Host: {settings.EMAIL_HOST}")
        logger.error(f"   Email Port: {settings.EMAIL_PORT}")
        logger.error(f"   Email User: {settings.EMAIL_HOST_USER}")
        
        logger.error(f"🔍 Full Traceback:")
        for line in traceback.format_exc().split('\n'):
            if line.strip():
                logger.error(f"   {line}")
        
        logger.error("=" * 60)
        return False


def resend_verification(request):
    """Resend verification email"""
    if request.method == 'POST':
        email = request.POST.get('email')
        
        try:
            registration_request = RegistrationRequest.objects.get(
                email=email,
                is_verified=False
            )
            
            if registration_request.is_expired():
                messages.error(
                    request,
                    'Registration has expired. Please register again.'
                )
                return redirect('events:landing_page')
            
            # Generate new token and resend
            import uuid
            registration_request.verification_token = str(uuid.uuid4())
            registration_request.save()
            
            send_verification_email(registration_request, request)
            
            messages.success(
                request,
                f'Verification email resent to {email}. Please check your inbox.'
            )
            
        except RegistrationRequest.DoesNotExist:
            messages.error(
                request,
                'No pending registration found for this email address.'
            )
    
    return redirect('events:landing_page')


def login_view(request):
    """User login view"""
    from django.contrib.auth import authenticate, login
    from .forms import LoginForm
    
    if request.user.is_authenticated:
        return redirect('events:dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            
            # Authenticate user
            user = authenticate(request, username=email, password=password)
            
            if user is not None:
                if user.is_verified:
                    login(request, user)
                    messages.success(request, f'Welcome back, {user.get_full_name()}!')
                    
                    # Redirect to next page or dashboard
                    next_page = request.GET.get('next')
                    if next_page:
                        return redirect(next_page)
                    else:
                        return redirect('events:dashboard')
                else:
                    messages.error(request, 'Please verify your email address before logging in.')
            else:
                messages.error(request, 'Invalid email or password.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = LoginForm()
    
    context = {
        'form': form,
    }
    return render(request, 'events/login.html', context)


def logout_view(request):
    """User logout view"""
    from django.contrib.auth import logout
    
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('events:landing_page')


@login_required
def dashboard_view(request):
    """User dashboard - requires authentication"""
    
    # Get base context (events and selected event)
    context = get_base_context(request)
    selected_event = context.get('selected_event')
    
    # Dashboard data filtered by selected event (or empty if no events)
    if selected_event:
        total_pledges = Pledges.objects.filter(event_id=selected_event.name).count()
        total_amount_pledged = Pledges.objects.filter(event_id=selected_event.name).aggregate(Sum('pledge'))['pledge__sum'] or 0
        total_amount_paid = Pledges.objects.filter(event_id=selected_event.name).aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
        pending_pledges = Pledges.objects.filter(event_id=selected_event.name, status__in=['new', 'pending', 'partial']).count()
        
        recent_pledges = Pledges.objects.filter(event_id=selected_event.name).order_by('-created_at')[:5]
        recent_transactions = Transactions.objects.filter(pledge__event_id=selected_event.name).order_by('-created_at')[:5]
    else:
        # No events exist - show empty data
        total_pledges = 0
        total_amount_pledged = 0
        total_amount_paid = 0
        pending_pledges = 0
        recent_pledges = []
        recent_transactions = []
    
    context.update({
        'total_pledges': total_pledges,
        'total_amount_pledged': total_amount_pledged,
        'total_amount_paid': total_amount_paid,
        'pending_pledges': pending_pledges,
        'recent_pledges': recent_pledges,
        'recent_transactions': recent_transactions,
    })
    return render(request, 'events/index.html', context)


# Event Management Views
@login_required
def event_list(request):
    """List user's events"""
    context = get_base_context(request)
    return render(request, 'events/event_list.html', context)


@login_required
def event_create(request):
    """Create a new event"""
    from .forms import EventForm
    
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.created_by = request.user
            event.save()
            
            messages.success(request, f'Event "{event.name}" created successfully!')
            return redirect('events:event_detail', event_id=event.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = EventForm()
    
    context = {
        'form': form,
        'title': 'Create New Event',
        'submit_text': 'Create Event'
    }
    return render(request, 'events/event_form.html', context)


@login_required
def event_detail(request, event_id):
    """View event details - only user's own events"""
    event = get_object_or_404(Event, id=event_id, created_by=request.user, is_active=True)
    
    # Get statistics for this event
    total_pledges = Pledges.objects.filter(event_id=event.name).count()
    total_amount_pledged = Pledges.objects.filter(event_id=event.name).aggregate(Sum('pledge'))['pledge__sum'] or 0
    total_amount_paid = Pledges.objects.filter(event_id=event.name).aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
    pending_pledges = Pledges.objects.filter(event_id=event.name, status__in=['new', 'pending', 'partial']).count()
    
    recent_pledges = Pledges.objects.filter(event_id=event.name).order_by('-created_at')[:10]
    
    context = {
        'event': event,
        'total_pledges': total_pledges,
        'total_amount_pledged': total_amount_pledged,
        'total_amount_paid': total_amount_paid,
        'pending_pledges': pending_pledges,
        'recent_pledges': recent_pledges,
    }
    return render(request, 'events/event_detail.html', context)


@login_required
def event_edit(request, event_id):
    """Edit an event - only user's own events"""
    from .forms import EventForm
    
    event = get_object_or_404(Event, id=event_id, created_by=request.user, is_active=True)
    
    if request.method == 'POST':
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            event = form.save()
            messages.success(request, f'Event "{event.name}" updated successfully!')
            return redirect('events:event_detail', event_id=event.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = EventForm(instance=event)
    
    context = {
        'form': form,
        'event': event,
        'title': f'Edit Event: {event.name}',
        'submit_text': 'Update Event'
    }
    return render(request, 'events/event_form.html', context)


@login_required
@require_POST
def set_selected_event(request):
    """
    AJAX view to set the selected event in the session
    """
    try:
        data = json.loads(request.body)
        event_id = data.get('event_id')
        
        if event_id:
            # Verify the event belongs to the user
            try:
                event = Event.objects.get(id=event_id, created_by=request.user, is_active=True)
                request.session['selected_event_id'] = event_id
                return JsonResponse({'success': True})
            except Event.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Event not found'})
        else:
            return JsonResponse({'success': False, 'error': 'No event ID provided'})
            
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def privacy_policy(request):
    """
    Display privacy policy page
    """
    from datetime import date
    context = {
        'current_date': date.today()
    }
    return render(request, 'events/privacy_policy.html', context)


def terms_of_service(request):
    """
    Display terms of service page
    """
    from datetime import date
    context = {
        'current_date': date.today()
    }
    return render(request, 'events/terms_of_service.html', context)


def data_deletion_request(request):
    """
    Handle data deletion requests from users
    """
    import random
    
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        reason = request.POST.get('reason', '').strip()
        confirm_deletion = request.POST.get('confirm_deletion')
        
        # Validate CAPTCHA
        captcha_answer = request.POST.get('captcha_answer', '')
        captcha_num1 = int(request.POST.get('captcha_num1', 0))
        captcha_num2 = int(request.POST.get('captcha_num2', 0))
        captcha_operation = request.POST.get('captcha_operation', '+')
        
        # Calculate correct answer
        if captcha_operation == '+':
            correct_answer = captcha_num1 + captcha_num2
        elif captcha_operation == '-':
            correct_answer = captcha_num1 - captcha_num2
        else:
            correct_answer = captcha_num1 + captcha_num2
        
        # Validate required fields
        if not full_name or not email:
            messages.error(request, 'Full name and email address are required.')
        elif not confirm_deletion:
            messages.error(request, 'You must confirm that you understand this action is permanent.')
        elif not captcha_answer or int(captcha_answer) != correct_answer:
            messages.error(request, 'Please solve the math problem correctly to verify you are human.')
        else:
            # Send email to privacy team
            try:
                from django.core.mail import send_mail
                from django.conf import settings
                from django.utils import timezone
                import logging
                
                logger = logging.getLogger(__name__)
                
                # Email content
                subject = f'Data Deletion Request - {full_name}'
                message_body = f"""
Data Deletion Request Received

User Details:
- Full Name: {full_name}
- Email Address: {email}
- Request Date: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}
- User IP: {request.META.get('REMOTE_ADDR', 'Unknown')}

Reason for Deletion:
{reason if reason else 'No reason provided'}

This request was submitted through the automated data deletion form.
Please process this request within 30 business days as required by our privacy policy.

Note: Verify the user's identity before processing the deletion request.
                """
                
                # Send to privacy team
                privacy_email = getattr(settings, 'PRIVACY_EMAIL', 'events@nifty.co.tz')
                support_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'events@nifty.co.tz')
                
                send_mail(
                    subject=subject,
                    message=message_body,
                    from_email=support_email,
                    recipient_list=[privacy_email, support_email],
                    fail_silently=False,
                )
                
                # Send confirmation email to user
                user_subject = 'Data Deletion Request Received - Events Management System'
                user_message = f"""
Dear {full_name},

We have received your request to delete your personal data from the Events Management System.

Request Details:
- Email: {email}
- Submitted: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}

What happens next:
1. We will verify your identity and process your request within 30 business days
2. You will receive a confirmation email once your data has been permanently deleted
3. After deletion, you will no longer be able to access your account or recover any data

If you have any questions or did not submit this request, please contact us immediately at events@nfity.co.tz

Thank you,
Events Management System Team
                """
                
                send_mail(
                    subject=user_subject,
                    message=user_message,
                    from_email=support_email,
                    recipient_list=[email],
                    fail_silently=False,
                )
                
                logger.info(f"Data deletion request submitted for {email} - {full_name}")
                
                messages.success(
                    request,
                    f'Your data deletion request has been submitted successfully. '
                    f'We have sent a confirmation email to {email}. '
                    f'We will process your request within 30 business days and notify you when complete.'
                )
                
            except Exception as e:
                logger.error(f"Failed to send data deletion request emails: {str(e)}")
                messages.error(
                    request,
                    'There was an error submitting your deletion request. '
                    'Please try again or contact events@nifty.co.tz directly.'
                )
            
            return redirect('events:data_deletion_request')
    
    # Generate CAPTCHA for GET request
    captcha_num1 = random.randint(1, 10)
    captcha_num2 = random.randint(1, 10)
    operations = ['+', '-']
    captcha_operation = random.choice(operations)
    
    # Make sure subtraction doesn't result in negative numbers
    if captcha_operation == '-' and captcha_num1 < captcha_num2:
        captcha_num1, captcha_num2 = captcha_num2, captcha_num1
    
    if captcha_operation == '+':
        captcha_question = f"{captcha_num1} + {captcha_num2} = ?"
    else:
        captcha_question = f"{captcha_num1} - {captcha_num2} = ?"
    
    context = {
        'captcha_num1': captcha_num1,
        'captcha_num2': captcha_num2,
        'captcha_operation': captcha_operation,
        'captcha_question': captcha_question,
    }
    
    return render(request, 'events/data_deletion.html', context)


@login_required
def delete_account(request):
    """
    Allow logged-in users to delete their own account
    """
    import random
    
    if request.method == 'POST':
        password = request.POST.get('password', '').strip()
        confirmation_text = request.POST.get('confirmation_text', '').strip()
        final_confirmation = request.POST.get('final_confirmation')
        
        # Validate CAPTCHA
        captcha_answer = request.POST.get('captcha_answer', '')
        captcha_num1 = int(request.POST.get('captcha_num1', 0))
        captcha_num2 = int(request.POST.get('captcha_num2', 0))
        captcha_operation = request.POST.get('captcha_operation', '+')
        
        # Calculate correct answer
        if captcha_operation == '+':
            correct_answer = captcha_num1 + captcha_num2
        elif captcha_operation == '-':
            correct_answer = captcha_num1 - captcha_num2
        else:
            correct_answer = captcha_num1 + captcha_num2
        
        # Validate inputs
        if not password:
            messages.error(request, 'Password is required to confirm account deletion.')
        elif not confirmation_text or confirmation_text != 'DELETE':
            messages.error(request, 'You must type "DELETE" exactly to confirm deletion.')
        elif not final_confirmation:
            messages.error(request, 'You must check the final confirmation checkbox.')
        elif not captcha_answer or int(captcha_answer) != correct_answer:
            messages.error(request, 'Please solve the math problem correctly to verify you are human.')
        else:
            # Verify password
            from django.contrib.auth import authenticate
            user = authenticate(username=request.user.email, password=password)
            
            if user is None:
                messages.error(request, 'Invalid password. Please try again.')
            else:
                # Perform account deletion
                try:
                    from django.utils import timezone
                    import logging
                    
                    logger = logging.getLogger(__name__)
                    
                    # Log the deletion
                    logger.info(f"Account deletion initiated for user: {request.user.email} ({request.user.full_name})")
                    
                    # Get user data for logging before deletion
                    user_email = request.user.email
                    user_name = request.user.full_name
                    
                    # Count associated data
                    events_count = Event.objects.filter(created_by=request.user).count()
                    pledges_count = Pledges.objects.filter(event__created_by=request.user).count()
                    transactions_count = Transactions.objects.filter(pledge__event__created_by=request.user).count()
                    messages_count = Messages.objects.filter(pledge__event__created_by=request.user).count()
                    
                    # Delete all associated data (Django will handle cascade deletions)
                    with transaction.atomic():
                        # Delete user's events (this will cascade to pledges, transactions, messages)
                        Event.objects.filter(created_by=request.user).delete()
                        
                        # Delete the user account
                        request.user.delete()
                    
                    logger.info(f"Account successfully deleted: {user_email} ({user_name})")
                    logger.info(f"Deleted data - Events: {events_count}, Pledges: {pledges_count}, Transactions: {transactions_count}, Messages: {messages_count}")
                    
                    # Send confirmation email (optional)
                    try:
                        from django.core.mail import send_mail
                        from django.conf import settings
                        
                        send_mail(
                            subject='Account Deletion Confirmation - Events Management System',
                            message=f"""
Dear {user_name},

Your account has been successfully deleted from the Events Management System.

Deletion Details:
- Account: {user_email}
- Deletion Date: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}
- Events Deleted: {events_count}
- Total Data Records Removed: {pledges_count + transactions_count + messages_count}

All your personal data and associated records have been permanently removed from our system.

If you have any questions or believe this deletion was made in error, please contact us immediately.

Thank you for using our service.

Best regards,
Nifty Technologies Team
                            """,
                            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'events@nifty.co.tz'),
                            recipient_list=[user_email],
                            fail_silently=True,  # Don't fail if email can't be sent since account is already deleted
                        )
                    except Exception as email_error:
                        logger.error(f"Failed to send account deletion confirmation email: {str(email_error)}")
                    
                    # Redirect to landing page with success message
                    messages.success(
                        request,
                        f'Your account has been successfully deleted. All your data has been permanently removed. '
                        f'Thank you for using our Events Management System.'
                    )
                    
                    # Logout and redirect
                    from django.contrib.auth import logout
                    logout(request)
                    return redirect('events:landing_page')
                    
                except Exception as e:
                    logger.error(f"Failed to delete account for {request.user.email}: {str(e)}")
                    messages.error(
                        request,
                        'There was an error deleting your account. Please try again or contact support.'
                    )
        
        return redirect('events:delete_account')
    
    # GET request - show the deletion form
    # Count user's data
    events_count = Event.objects.filter(created_by=request.user).count()
    pledges_count = Pledges.objects.filter(event__created_by=request.user).count()
    transactions_count = Transactions.objects.filter(pledge__event__created_by=request.user).count()
    messages_count = Messages.objects.filter(pledge__event__created_by=request.user).count()
    
    # Generate CAPTCHA for the form
    captcha_num1 = random.randint(1, 10)
    captcha_num2 = random.randint(1, 10)
    captcha_operation = random.choice(['+', '-'])
    
    context = {
        'events_count': events_count,
        'pledges_count': pledges_count,
        'transactions_count': transactions_count,
        'messages_count': messages_count,
        'captcha_num1': captcha_num1,
        'captcha_num2': captcha_num2,
        'captcha_operation': captcha_operation,
    }
    
    return render(request, 'events/delete_account.html', context)
