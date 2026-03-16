from django import forms
from django.core.exceptions import ValidationError
from trade.models import Transport
import os

class TransportAddForm(forms.ModelForm):
    """Transport Form (with image size/format validation)"""
    class Meta:
        model = Transport
        fields = ['name', 'type', 'price', 'time', 'company', 'description', 'image']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g.: China-Russia Cross-Border Land Transport Line'
            }),
            'type': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Sea/Air/Land'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Unit: CNY'
            }),
            'time': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g.: 7-10 days'
            }),
            'company': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Logistics Company Name'
            }),
            # Description field: add ID for JS character count statistics
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Introduce logistics routes, service advantages in detail...',
                'id': 'description-input',  # Key: bind JS event
                'maxlength': '500'  # Limit max characters on HTML level
            }),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control-file mt-2'}),
        }

    # ---------------------- Custom Image Validation Rules ----------------------
    def clean_image(self):
        """Validate image size (≤2MB) and format (JPG/PNG)"""
        image = self.cleaned_data.get('image')
        if image:
            # 1. Validate file size (2MB = 2*1024*1024 bytes)
            max_size = 2 * 1024 * 1024  # 2MB
            if image.size > max_size:
                raise ValidationError(
                    f'Image size cannot exceed {max_size / 1024 / 1024}MB! Current size: {image.size / 1024 / 1024:.2f}MB')
            # 2. Validate file format
            allowed_formats = ['jpg', 'jpeg', 'png']
            # Get file extension (lowercase, remove leading dot)
            file_ext = os.path.splitext(image.name)[1].lower().lstrip('.')
            if file_ext not in allowed_formats:
                raise ValidationError(f'Only {", ".join(allowed_formats)} formats are supported! Current format: {file_ext}')
        return image