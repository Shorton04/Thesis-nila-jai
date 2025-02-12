# accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordResetForm
from django.contrib.auth import get_user_model
from .models import UserProfile
from django.core.exceptions import ValidationError
import re
from .models import CustomUser
User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(max_length=15, required=True)
    company_name = forms.CharField(max_length=255, required=True)
    position = forms.CharField(max_length=100, required=True)
    business_type = forms.CharField(max_length=50, required=True)

    class Meta:
        model = User
        fields = ('email', 'phone_number', 'company_name', 'position', 'business_type', 'password1', 'password2')


    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        # Remove any non-digit characters
        phone_number = re.sub(r'\D', '', phone_number)

        if len(phone_number) < 10:
            raise ValidationError("Phone number must have at least 10 digits.")

        return phone_number

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("This email address is already in use.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.username = self.cleaned_data['email']  # Set username to email
        user.phone_number = self.cleaned_data['phone_number']
        user.company_name = self.cleaned_data['company_name']
        user.position = self.cleaned_data['position']
        user.business_type = self.cleaned_data['business_type']

        if commit:
            user.save()
            # Create user profile
            UserProfile.objects.create(user=user)
        return user


class CustomUserChangeForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ('company_name', 'position', 'business_type', 'phone_number')
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'mt-1 focus:ring-indigo-500 focus:border-indigo-500 block w-full shadow-sm sm:text-sm border-gray-300 rounded-md'}),
            'position': forms.TextInput(attrs={'class': 'mt-1 focus:ring-indigo-500 focus:border-indigo-500 block w-full shadow-sm sm:text-sm border-gray-300 rounded-md'}),
            'business_type': forms.TextInput(attrs={'class': 'mt-1 focus:ring-indigo-500 focus:border-indigo-500 block w-full shadow-sm sm:text-sm border-gray-300 rounded-md'}),
            'phone_number': forms.TextInput(attrs={'class': 'mt-1 focus:ring-indigo-500 focus:border-indigo-500 block w-full shadow-sm sm:text-sm border-gray-300 rounded-md'}),
        }

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('profile_picture', 'address', 'city', 'state', 'postal_code', 'country')
        widgets = {
            'address': forms.TextInput(attrs={'class': 'mt-1 focus:ring-indigo-500 focus:border-indigo-500 block w-full shadow-sm sm:text-sm border-gray-300 rounded-md'}),
            'city': forms.TextInput(attrs={'class': 'mt-1 focus:ring-indigo-500 focus:border-indigo-500 block w-full shadow-sm sm:text-sm border-gray-300 rounded-md'}),
            'state': forms.TextInput(attrs={'class': 'mt-1 focus:ring-indigo-500 focus:border-indigo-500 block w-full shadow-sm sm:text-sm border-gray-300 rounded-md'}),
            'postal_code': forms.TextInput(attrs={'class': 'mt-1 focus:ring-indigo-500 focus:border-indigo-500 block w-full shadow-sm sm:text-sm border-gray-300 rounded-md'}),
            'country': forms.TextInput(attrs={'class': 'mt-1 focus:ring-indigo-500 focus:border-indigo-500 block w-full shadow-sm sm:text-sm border-gray-300 rounded-md'}),
        }

    def clean_profile_picture(self):
        profile_picture = self.cleaned_data.get('profile_picture')
        if profile_picture:
            if profile_picture.size > 5 * 1024 * 1024:  # 5MB
                raise ValidationError("Image file size must be less than 5MB.")
            if not profile_picture.content_type.startswith('image'):
                raise ValidationError("File must be an image.")
        return profile_picture


class PasswordChangeRequestForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not User.objects.filter(email=email).exists():
            raise ValidationError("No user found with this email address.")
        return email


class SetPasswordForm(forms.Form):
    password1 = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        min_length=8
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 and password2:
            if password1 != password2:
                raise ValidationError("Passwords don't match")

            # Password validation
            if len(password1) < 8:
                raise ValidationError("Password must be at least 8 characters long.")
            if not re.search(r'[A-Z]', password1):
                raise ValidationError("Password must contain at least one uppercase letter.")
            if not re.search(r'[a-z]', password1):
                raise ValidationError("Password must contain at least one lowercase letter.")
            if not re.search(r'\d', password1):
                raise ValidationError("Password must contain at least one number.")
            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password1):
                raise ValidationError("Password must contain at least one special character.")

        return cleaned_data


class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password'
        })
    )
    remember_me = forms.BooleanField(required=False)

class AdminUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('email', 'first_name', 'last_name', 'phone_number',
                 'company_name', 'position', 'business_type', 'is_active',
                 'is_email_verified')
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'position': forms.TextInput(attrs={'class': 'form-control'}),
            'business_type': forms.TextInput(attrs={'class': 'form-control'}),
        }

class AdminUserEditForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ('email', 'first_name', 'last_name', 'phone_number',
                 'company_name', 'position', 'business_type', 'is_active',
                 'is_email_verified')
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'position': forms.TextInput(attrs={'class': 'form-control'}),
            'business_type': forms.TextInput(attrs={'class': 'form-control'}),
        }

