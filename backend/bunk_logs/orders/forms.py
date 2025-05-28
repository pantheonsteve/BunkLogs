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
            
        # Try to read the CSV file to validate format
        import csv
        import io
        try:
            csv_file_io = io.StringIO(csv_file.read().decode('utf-8'))
            reader = csv.reader(csv_file_io)
            header = next(reader)  # Read header row
            
            # Check if the required columns are in the header
            required_fields = ['item_name', 'item_description', 'item_category_id', 'available']
            for field in required_fields:
                if field not in header:
                    raise forms.ValidationError(f'CSV file must contain a {field} column')
                    
            # Reset the file pointer so it can be read again later
            csv_file.seek(0)
            return csv_file
        except Exception as e:
            raise forms.ValidationError(f'Invalid CSV file: {str(e)}')


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
        if not csv_file.name.endswith('.csv'):
            raise forms.ValidationError('File must be a CSV file with .csv extension.')
        
        # Add more validations as needed
        if csv_file.size > 15 * 1024 * 1024:  # 15MB limit
            raise forms.ValidationError('File too large. Size should not exceed 15MB.')
            
        # Try to read the CSV file to validate format
        import csv
        import io
        try:
            csv_file_io = io.StringIO(csv_file.read().decode('utf-8'))
            reader = csv.reader(csv_file_io)
            header = next(reader)  # Read header row
            
            # Check if the required columns are in the header
            required_fields = ['user_id', 'order_bunk_id']
            for field in required_fields:
                if field not in header:
                    raise forms.ValidationError(f'CSV file must contain a {field} column')
                    
            # Reset the file pointer so it can be read again later
            csv_file.seek(0)
            return csv_file
        except Exception as e:
            raise forms.ValidationError(f'Invalid CSV file: {str(e)}')
