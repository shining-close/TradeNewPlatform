# Import core dependencies
import os
from django import forms
from django.forms import ClearableFileInput
from django.utils.translation import gettext_lazy as _
from trade.models import Transport

# Custom file upload component (replace default Chinese prompts with English)
class EnglishClearableFileInput(ClearableFileInput):
    """Custom clearable file input with English labels (replace default Chinese)"""
    clear_checkbox_label = _('Clear')
    initial_text = _('Current Image')
    input_text = _('Choose File')
    template_with_clear = '<br> %(clear_checkbox_label)s %(clear)s'
    # Custom template (optional, keep format consistent)
    template_with_initial = (
        '%(initial_text)s: %(initial)s %(clear_template)s<br>%(input_text)s: %(input)s'
    )

# Logistics add/edit form (adapt to multi-language, support data validation)
class TransportAddForm(forms.ModelForm):
    """Transport Form (with image size/format validation)"""
    # Exclusive configuration for price field (non-negative validation + format restriction)
    price = forms.DecimalField(
        label=_('Price'),
        max_digits=10,
        decimal_places=2,
        min_value=0,
        error_messages={
            'min_value': _('Price cannot be negative'),
            'required': _('Price is required')
        },
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter price (e.g. 99.99)'),
            'step': '0.01'
        })
    )

    # Meta class (must be indented, as an inner class of TransportAddForm)
    class Meta:
        model = Transport
        # Mapped model fields (corresponding to front-end form)
        fields = ['name', 'type', 'price', 'time', 'company', 'description', 'image']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter transport name (max 50 chars)'),
                'maxlength': '50'
            }),
            'type': forms.Select(attrs={
                'class': 'form-control'
            }),  # Custom drop-down options in front-end, only style configured here
            'time': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter transport time (e.g. 3-5 days)')
            }),
            'company': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter company name (max 100 chars)'),
                'maxlength': '100'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': _('Enter description (max 500 chars)'),
                'maxlength': '500',
                'rows': 4
            }),
            'image': EnglishClearableFileInput(attrs={
                'class': 'form-control-file'
            })
        }

    # Image field validation (size + format)
    def clean_image(self):
        """Validate image size (<=2MB) and format (jpg/jpeg/png)"""
        image = self.cleaned_data.get('image')
        if image:
            # Size validation (2MB = 2*1024*1024 bytes)
            if image.size > 2 * 1024 * 1024:
                raise forms.ValidationError(_('Image size cannot exceed 2MB'))
            # Format validation
            allowed_formats = ['jpg', 'jpeg', 'png']
            file_ext = os.path.splitext(image.name)[1].lower().lstrip('.')
            if file_ext not in allowed_formats:
                raise forms.ValidationError(
                    _('Only JPG/JPEG/PNG formats are allowed')
                )
        return image

    # Form initialization (adapt to edit/add scenarios)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Edit scenario: Initialize description field value
        if self.initial.get('description'):
            self.fields['description'].initial = self.initial['description']
        # Add scenario / no price set: Default price to 0.00
        if not self.initial.get('price'):
            self.fields['price'].initial = 0.00