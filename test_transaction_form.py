#!/usr/bin/env python3
"""
Test script to verify transaction form functionality
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'events_project.settings')
django.setup()

from events.forms import TransactionForm
from events.models import Pledges, Transactions

def test_transaction_form():
    """Test the TransactionForm functionality"""
    
    print("=== Testing Transaction Form ===")
    
    # Get a test pledge
    pledge = Pledges.objects.first()
    if not pledge:
        print("ERROR: No pledges found in database!")
        return False
    
    print(f"Using pledge: {pledge.name} (ID: {pledge.id})")
    
    # Test data
    test_data = {
        'amount': '100.00',
        'method': 'cash',
        'transaction_id': 'CASH-TEST-12345'
    }
    
    print(f"Test data: {test_data}")
    
    # Create form with pledge_id
    form = TransactionForm(data=test_data, pledge_id=pledge.id)
    
    print(f"Form fields: {list(form.fields.keys())}")
    print(f"Form is valid: {form.is_valid()}")
    
    if not form.is_valid():
        print(f"Form errors: {form.errors}")
        return False
    
    # Try to save
    try:
        transaction = form.save()
        print(f"✅ SUCCESS: Transaction created with ID: {transaction.id}")
        print(f"   Amount: {transaction.amount}")
        print(f"   Method: {transaction.method}")
        print(f"   Transaction ID: {transaction.transaction_id}")
        print(f"   Pledge: {transaction.pledge}")
        
        # Clean up - delete the test transaction
        transaction.delete()
        print("   Test transaction deleted")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR saving transaction: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_form_without_pledge():
    """Test form without pledge_id (should require pledge selection)"""
    
    print("\n=== Testing Form Without Pledge ID ===")
    
    # Get a test pledge
    pledge = Pledges.objects.first()
    
    test_data = {
        'pledge': str(pledge.id),
        'amount': '50.00',
        'method': 'mpesa',
        'transaction_id': 'MPESA-TEST-67890'
    }
    
    print(f"Test data: {test_data}")
    
    # Create form without pledge_id
    form = TransactionForm(data=test_data)
    
    print(f"Form fields: {list(form.fields.keys())}")
    print(f"Form is valid: {form.is_valid()}")
    
    if not form.is_valid():
        print(f"Form errors: {form.errors}")
        return False
    
    # Try to save
    try:
        transaction = form.save()
        print(f"✅ SUCCESS: Transaction created with ID: {transaction.id}")
        print(f"   Amount: {transaction.amount}")
        print(f"   Method: {transaction.method}")
        print(f"   Transaction ID: {transaction.transaction_id}")
        print(f"   Pledge: {transaction.pledge}")
        
        # Clean up
        transaction.delete()
        print("   Test transaction deleted")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR saving transaction: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success1 = test_transaction_form()
    success2 = test_form_without_pledge()
    
    print(f"\n=== Test Results ===")
    print(f"Form with pledge_id: {'✅ PASS' if success1 else '❌ FAIL'}")
    print(f"Form without pledge_id: {'✅ PASS' if success2 else '❌ FAIL'}")
    
    if success1 and success2:
        print("\n🎉 All tests passed! The transaction form should work correctly.")
    else:
        print("\n⚠️ Some tests failed. Check the errors above.")