# 导入核心依赖
import os
from django import forms
from django.forms import ClearableFileInput
from django.utils.translation import gettext_lazy as _
from trade.models import Transport


# 自定义文件上传组件（替换默认中文提示为英文）
class EnglishClearableFileInput(ClearableFileInput):
    """Custom clearable file input with English labels (replace default Chinese)"""
    clear_checkbox_label = _('Clear')
    initial_text = _('Current Image')
    input_text = _('Choose File')
    template_with_clear = '<br> %(clear_checkbox_label)s %(clear)s'

    # 自定义模板（可选，保持格式统一）
    template_with_initial = (
        '%(initial_text)s: %(initial)s %(clear_template)s<br>%(input_text)s: %(input)s'
    )


# 物流运输新增/编辑表单（适配多语言，支持数据校验）
class TransportAddForm(forms.ModelForm):
    """Transport Form (with image size/format validation)"""

    # 价格字段专属配置（非负校验+格式限制）
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

    # Meta类（必须缩进，作为TransportAddForm的内部类）
    class Meta:
        model = Transport
        # 映射的模型字段（与前端表单对应）
        fields = ['name', 'type', 'price', 'time', 'company', 'description', 'image']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter transport name (max 50 chars)'),
                'maxlength': '50'
            }),
            'type': forms.Select(attrs={
                'class': 'form-control'
            }),  # 前端自定义下拉选项，此处仅配置样式
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

    # 图片字段校验（大小+格式）
    def clean_image(self):
        """Validate image size (<=2MB) and format (jpg/jpeg/png)"""
        image = self.cleaned_data.get('image')
        if image:
            # 大小校验（2MB = 2*1024*1024 bytes）
            if image.size > 2 * 1024 * 1024:
                raise forms.ValidationError(_('Image size cannot exceed 2MB'))
            # 格式校验
            allowed_formats = ['jpg', 'jpeg', 'png']
            file_ext = os.path.splitext(image.name)[1].lower().lstrip('.')
            if file_ext not in allowed_formats:
                raise forms.ValidationError(
                    _('Only JPG/JPEG/PNG formats are allowed')
                )
        return image

    # 表单初始化（适配编辑/新增场景）
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 编辑场景：初始化描述字段值
        if self.initial.get('description'):
            self.fields['description'].initial = self.initial['description']
        # 新增场景/无价格：默认价格为0.00
        if not self.initial.get('price'):
            self.fields['price'].initial = 0.00