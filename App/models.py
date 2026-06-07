from django.db import models
from django.utils import timezone

class WaitlistUser(models.Model):
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255, blank=True)
    will_use_app = models.BooleanField(default=False)
    okay_with_emails = models.BooleanField(default=False)
    would_pay = models.BooleanField(default=False)
    use_case = models.TextField(blank=True)
    additional_info = models.TextField(blank=True)
    submitted_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return self.email
    
    class Meta:
        ordering = ['-submitted_at']