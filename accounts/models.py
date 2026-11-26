"""User model with a role field (FR1, FR2)."""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Campus user. The role decides which screens the user can reach."""

    STUDENT = 'student'
    STAFF = 'staff'
    MANAGER = 'manager'
    ADMIN = 'admin'
    ROLES = [
        (STUDENT, 'Student'),
        (STAFF, 'Cafeteria Staff'),
        (MANAGER, 'Cafeteria Owner'),
        (ADMIN, 'Administrator'),
    ]

    email = models.EmailField('email address', unique=True)
    student_id = models.CharField(max_length=20, blank=True)
    role = models.CharField(max_length=10, choices=ROLES, default=STUDENT)

    def save(self, *args, **kwargs):
        """Superusers created from the command line are always administrators."""
        if self.is_superuser:
            self.role = self.ADMIN
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'

    @property
    def is_student(self):
        """True for a normal customer."""
        return self.role == self.STUDENT

    @property
    def is_kitchen(self):
        """True for anyone who can work the order queue."""
        return self.role in (self.STAFF, self.MANAGER, self.ADMIN)

    @property
    def is_owner(self):
        """True for the owner or administrator, who manage menu and reports."""
        return self.role in (self.MANAGER, self.ADMIN)
