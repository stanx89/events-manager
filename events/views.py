from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.template.loader import render_to_string
from django.core.paginator import Paginator
from django.db import transaction
from django.urls import reverse
from .models import Pledges, Transactions, Messages
from .forms import PledgeForm, TransactionForm, MessageForm, PledgeSearchForm, TransactionSearchForm
from django.db.models import Sum, Q


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
    messages_list = Messages.objects.all().order_by('-created_at')
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
            message = form.save()
            if is_modal and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'Message created successfully and will be sent via {message.get_method_display()}.',
                    'redirect': reverse('events:message_detail', args=[message.id])
                })
            else:
                messages.success(request, f'Message created successfully and will be sent via {message.get_method_display()}.')
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


def bulk_message_send(request):
    """View to send bulk messages"""
    if request.method == 'POST':
        pledge_ids = request.POST.getlist('pledge_ids')
        message_text = request.POST.get('message')
        method = request.POST.get('method')
        
        if pledge_ids and message_text and method:
            created_messages = []
            
            for pledge_id in pledge_ids:
                try:
                    pledge = Pledges.objects.get(id=pledge_id)
                    message = Messages.objects.create(
                        pledge=pledge,
                        message=message_text,
                        method=method,
                        status='pending'
                    )
                    created_messages.append(message)
                except Pledges.DoesNotExist:
                    continue
            
            messages.success(request, f'Created {len(created_messages)} messages for bulk sending.')
            return redirect('events:message_list')
        else:
            messages.error(request, 'Please fill in all required fields.')
    
    pledges = Pledges.objects.filter(status__in=['new', 'pending', 'partial']).order_by('name')
    context = {
        'pledges': pledges,
        'message_methods': Messages.MESSAGE_METHODS,
    }
    return render(request, 'events/bulk_message.html', context)
