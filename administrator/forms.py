from django import forms
from django.core.exceptions import ValidationError
from trade.models import Transport
import os


class TransportAddForm(forms.ModelForm):
    """物流表单（含图片大小/格式校验）"""

    class Meta:
        model = Transport
        fields = ['name', 'type', 'price', 'time', 'company', 'description', 'image']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '如：中俄跨境陆运专线'}),
            'type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '海运/空运/陆运'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '单位：元'}),
            'time': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '如：7-10天'}),
            'company': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '物流公司名称'}),
            # 描述字段：添加id用于JS字数统计
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': '详细介绍物流线路、服务优势等...',
                'id': 'description-input',  # 关键：绑定JS事件
                'maxlength': '500'  # HTML层面限制最大字数
            }),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control-file mt-2'}),
        }

    # ---------------------- 自定义图片校验规则 ----------------------
    def clean_image(self):
        """校验图片大小（≤2MB）和格式（JPG/PNG）"""
        image = self.cleaned_data.get('image')
        if image:
            # 1. 校验文件大小（2MB = 2*1024*1024 字节）
            max_size = 2 * 1024 * 1024  # 2MB
            if image.size > max_size:
                raise ValidationError(
                    f'图片大小不能超过 {max_size / 1024 / 1024}MB！当前大小：{image.size / 1024 / 1024:.2f}MB')

            # 2. 校验文件格式
            allowed_formats = ['jpg', 'jpeg', 'png']
            file_ext = os.path.splitext(image.name)[1].lower().lstrip('.')  # 获取后缀（小写）
            if file_ext not in allowed_formats:
                raise ValidationError(f'仅支持 {", ".join(allowed_formats)} 格式！当前格式：{file_ext}')

        return image