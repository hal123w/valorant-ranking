from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import Clip, Report
from .x_url import extract_tweet_id, normalize_status_url


class EmailAuthenticationForm(AuthenticationForm):
    """Login with email (stored as username)."""

    username = forms.EmailField(
        label='メールアドレス',
        widget=forms.EmailInput(attrs={
            'class': 'input',
            'placeholder': 'you@example.com',
            'autocomplete': 'email',
        }),
    )
    password = forms.CharField(
        label='パスワード',
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'input',
            'placeholder': 'パスワード',
            'autocomplete': 'current-password',
        }),
    )


class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        label='メールアドレス',
        widget=forms.EmailInput(attrs={
            'class': 'input',
            'placeholder': 'you@example.com',
            'autocomplete': 'email',
        }),
    )

    class Meta:
        model = User
        fields = ('email',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({
            'class': 'input',
            'placeholder': 'パスワード',
            'autocomplete': 'new-password',
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'input',
            'placeholder': 'パスワード（確認）',
            'autocomplete': 'new-password',
        })
        self.fields['password1'].label = 'パスワード'
        self.fields['password2'].label = 'パスワード（確認）'

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(username__iexact=email).exists():
            raise ValidationError('このメールアドレスは既に登録されています。')
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('このメールアドレスは既に登録されています。')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        email = self.cleaned_data['email']
        user.username = email
        user.email = email
        if commit:
            user.save()
        return user


class ClipSubmitForm(forms.Form):
    url = forms.URLField(
        label='Xの投稿URL',
        widget=forms.URLInput(attrs={
            'class': 'input',
            'placeholder': 'https://x.com/username/status/1234567890',
        }),
    )
    is_valorant = forms.BooleanField(
        label='この投稿は Valorant のプレイ映像です（目視運用・同意必須）',
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'checkbox'}),
    )

    def clean_url(self):
        raw = self.cleaned_data['url']
        tweet_id = extract_tweet_id(raw)
        normalized = normalize_status_url(raw)
        if (
            Clip.objects.filter(tweet_id=tweet_id).exists()
            or Clip.objects.filter(url=normalized).exists()
        ):
            raise ValidationError('この投稿は既に登録されています。')
        self._tweet_id = tweet_id
        return normalized

    def clean(self):
        cleaned = super().clean()
        tweet_id = getattr(self, '_tweet_id', None)
        if tweet_id:
            cleaned['tweet_id'] = tweet_id
        return cleaned


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ('reason', 'detail')
        labels = {
            'reason': '理由',
            'detail': '詳細（任意）',
        }
        widgets = {
            'reason': forms.Select(attrs={'class': 'input'}),
            'detail': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': '補足があれば入力',
                'maxlength': 300,
            }),
        }
