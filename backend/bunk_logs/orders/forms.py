from django import forms
from .models import Item, ItemCategory, Order, OrderType

class CsvImportForm(forms.Form):
    """Form for importing CSV files"""
    csv_file = forms.FileField(
        label='CSV File',
        help_text='Please upload a CSV file with the required fields.'
    )


class ItemCategoryImportForm(CsvImportForm):
    """Form for importing Item Categories"""
    
    def clean_csv_file(self):
        csv_file = self.cleaned_data['csv_file']
        
        # Check file extension
        if not csv_file.name.endswith('.csv'):
            raise forms.ValidationError('File must be a CSV file with .csv extension.')
        
        # You could add more validations here, like checking file size
        if csv_file.size > 5 * 1024 * 1024:  # 5MB limit
            raise forms.ValidationError('File too large. Size should not exceed 5MB.')
            
        return csv_file


class ItemImportForm(CsvImportForm):
    """Form for importing Items"""
    
    def clean_csv_file(self):
        csv_file = self.cleaned_data['csv_file']
        
        # Check file extension
        if not csv_file.name.endswith('.csv'):
            raise forms.ValidationError('File must be a CSV file with .csv extension.')
        
        # You could add more validations here
        if csv_file.size > 10 * 1024 * 1024:  # 10MB limit
            raise forms.ValidationError('File too large. Size should not exceed 10MB.')
            
        return csv_file


class OrderImportForm(CsvImportForm):
    """Form for importing Orders"""
    order_type = forms.ModelChoiceField(
        queryset=OrderType.objects.all(),
        required=True,
        help_text='All imported orders will be assigned to this Order Type'
    )
    
    def clean_csv_file(self):
        csv_file = self.cleaned_data['csv_file']
        
        # Check file extension
        if not csv_file.name.endswith(('.csv', '.xlsx')):
            raise forms.ValidationError('File must be a CSV or Excel file (.csv or .xlsx).')
        
        # Add more validations as needed
        if csv_file.size > 15 * 1024 * 1024:  # 15MB limit
            raise forms.ValidationError('File too large. Size should not exceed 15MB.')
            
        return csv_file
