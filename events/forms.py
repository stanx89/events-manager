from django import forms
from .models import Pledges, Transactions, Messages, MessageTemplate
import uuid


class PledgeForm(forms.ModelForm):
    class Meta:
        model = Pledges
        fields = ['event_id', 'name', 'mobile_number', 'pledge', 'amount_paid', 'whatsapp_status']
        
        widgets = {
            'event_id': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            }),
            'name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            }),
            'mobile_number': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            }),
            'pledge': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'amount_paid': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'whatsapp_status': forms.Select(choices=[(False, 'No'), (True, 'Yes')], attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
            }),
        }
        
        labels = {
            'event_id': 'Event ID',
            'name': 'Full Name',
            'mobile_number': 'Mobile Number',
            'pledge': 'Pledge Amount',
            'amount_paid': 'Amount Paid',
            'whatsapp_status': 'Is WhatsApp Number?',
        }


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transactions
        fields = ['amount', 'method', 'transaction_id']
        
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
                'step': '0.01',
                'min': '0',
            }),
            'method': forms.Select(attrs={
                'class': 'mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
                'onchange': 'handlePaymentMethodChange(this.value)'
            }),
            'transaction_id': forms.TextInput(attrs={
                'class': 'mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
            }),
        }
        
        labels = {
            'amount': 'Amount',
            'method': 'Payment Method',
            'transaction_id': 'Transaction ID',
        }

    def __init__(self, *args, **kwargs):
        self.pledge_id = kwargs.pop('pledge_id', None)
        super().__init__(*args, **kwargs)
        
        # If no pledge_id is provided, add pledge as a regular dropdown field
        if self.pledge_id:
            # Add pledge as a hidden field when pledge_id is provided
            try:
                pledge_obj = Pledges.objects.get(id=self.pledge_id)
                self.fields['pledge'] = forms.ModelChoiceField(
                    queryset=Pledges.objects.filter(id=self.pledge_id),
                    widget=forms.HiddenInput(),
                    initial=pledge_obj,
                    required=True
                )
            except Pledges.DoesNotExist:
                # If pledge doesn't exist, fall back to dropdown
                self.pledge_id = None
        
        if not self.pledge_id:
            # Add pledge as a dropdown field when no pledge_id is provided
            self.fields['pledge'] = forms.ModelChoiceField(
                queryset=Pledges.objects.all(),
                widget=forms.Select(attrs={
                    'class': 'mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
                }),
                empty_label="Select a pledge"
            )
            # Move pledge field to the beginning
            field_order = ['pledge'] + [field for field in self.fields.keys() if field != 'pledge']
            self.fields = {field: self.fields[field] for field in field_order}

    def clean(self):
        cleaned_data = super().clean()
        method = cleaned_data.get('method')
        transaction_id = cleaned_data.get('transaction_id')
        pledge = cleaned_data.get('pledge')
        
        # Ensure pledge is set
        if not pledge and not self.pledge_id:
            raise forms.ValidationError({
                'pledge': 'Please select a pledge for this transaction.'
            })
        
        # If payment method is cash, transaction_id should be provided by frontend
        if method == 'cash':
            if not transaction_id or not transaction_id.startswith('CASH-'):
                # Fallback: generate UUID if not provided by frontend
                cleaned_data['transaction_id'] = f"CASH-{str(uuid.uuid4())[:8].upper()}"
        elif not transaction_id:
            # For non-cash payments, transaction_id is required
            raise forms.ValidationError({
                'transaction_id': 'Transaction ID is required for this payment method.'
            })
        
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Force set pledge from cleaned_data or pledge_id
        pledge = self.cleaned_data.get('pledge')
        
        if pledge:
            instance.pledge = pledge
        elif self.pledge_id:
            try:
                pledge_obj = Pledges.objects.get(id=self.pledge_id)
                instance.pledge = pledge_obj
            except Pledges.DoesNotExist:
                raise forms.ValidationError("Selected pledge does not exist.")
        else:
            raise forms.ValidationError("Pledge is required.")
        
        if commit:
            instance.save()
        
        return instance


class MessageForm(forms.ModelForm):
    class Meta:
        model = Messages
        fields = ['pledge', 'message', 'method', 'status']
        
        widgets = {
            'pledge': forms.Select(attrs={
                'class': 'mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'message': forms.Textarea(attrs={
                'class': 'mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
                'rows': 4,
            }),
            'method': forms.Select(attrs={
                'class': 'mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'status': forms.Select(attrs={
                'class': 'mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
        }
        
        labels = {
            'pledge': 'Pledge',
            'message': 'Message',
            'method': 'Communication Method',
            'status': 'Status',
        }

    def __init__(self, *args, **kwargs):
        pledge_id = kwargs.pop('pledge_id', None)
        super().__init__(*args, **kwargs)
        
        # If pledge_id is provided, filter the pledge field
        if pledge_id:
            self.fields['pledge'].queryset = Pledges.objects.filter(id=pledge_id)
            self.fields['pledge'].initial = pledge_id


class PledgeSearchForm(forms.Form):
    search = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full px-4 py-3 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all duration-200 bg-white hover:border-gray-400',
            'placeholder': 'Search by name, event ID, or mobile number...'
        })
    )
    
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + Pledges.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full px-4 py-3 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all duration-200 bg-white hover:border-gray-400 appearance-none'
        })
    )
    
    whatsapp_status = forms.ChoiceField(
        choices=[('True', 'Yes'), ('False', 'No')],
        required=False,
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
        })
    )


class TransactionSearchForm(forms.Form):
    search = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by transaction ID...'
        })
    )
    
    method = forms.ChoiceField(
        choices=[('', 'All Payment Methods')] + Transactions.PAYMENT_METHODS,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )


class MessageTemplateForm(forms.ModelForm):
    class Meta:
        model = MessageTemplate
        fields = ['type', 'message']
        
        widgets = {
            'type': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
            }),
            'message': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'rows': 4,
            }),
        }
        
        labels = {
            'type': 'Template Type',
            'message': 'Message Template',
        }
        
        help_texts = {
            'type': 'The category/type of this message template',
            'message': 'Use placeholders like {name}, {pledge_amount}, {balance} etc. for dynamic content',
        }