"""Registration form (FR1)."""
from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm

from .models import User

REGISTER_ROLES = [
    (User.STUDENT, 'Student'),
    (User.STAFF, 'Cafeteria Staff'),
    (User.MANAGER, 'Cafeteria Owner (Admin)'),
]


class RegisterForm(UserCreationForm):
    """Create an account. Staff and owners must know the cafeteria access code."""

    role = forms.ChoiceField(label='I am a', choices=REGISTER_ROLES, initial=User.STUDENT)
    access_code = forms.CharField(
        label='Cafeteria access code', required=False,
        help_text='Only for staff and owners. Ask the cafeteria owner for the code.',
    )

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'student_id', 'email',
                  'role', 'access_code')

    def clean_email(self):
        """Reject an email that is already registered."""
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email

    def clean(self):
        """Staff and owner accounts need the correct access code."""
        data = super().clean()
        role = data.get('role')
        if role in (User.STAFF, User.MANAGER):
            if data.get('access_code', '').strip() != settings.STAFF_ACCESS_CODE:
                self.add_error('access_code', 'The access code is wrong. Students do not need one.')
        return data

    def save(self, commit=True):
        """Save the user with the chosen role."""
        user = super().save(commit=False)
        user.role = self.cleaned_data['role']
        if commit:
            user.save()
        return user
