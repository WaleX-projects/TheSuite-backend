# models.py
from django.db import models

from companies.models import Company 
from datetime import timedelta
from django.utils import timezone


    
        
class Plan(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    base_price = models.DecimalField(max_digits=10, decimal_places=2)

    price_per_employee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    max_employees = models.IntegerField(null=True, blank=True)

    # FEATURES
    has_attendance = models.BooleanField(default=True)
    has_leave = models.BooleanField(default=True)
    has_payroll = models.BooleanField(default=False)

    # UI SUPPORT (IMPORTANT FOR FRONTEND)
    description = models.TextField(blank=True)
    is_popular = models.BooleanField(default=False)        
        
    duration_days = models.IntegerField(default=30)  # monthly = 30
    trial_days = models.IntegerField(default=0)

    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
        

class Subscription(models.Model):
    STATUS_CHOICES = [
        ("trialing", "Trialing"),
        ("active", "Active"),
        ("past_due", "Past Due"),
        ("canceled", "Canceled"),
        ("expired", "Expired"),
    ]

    company = models.OneToOneField("companies.Company", on_delete=models.CASCADE,related_name="subscription")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)

    trial_end = models.DateTimeField(null=True, blank=True)

    def is_active(self):
        now = timezone.now()

        if self.status == "trialing" and self.trial_end:
            return now <= self.trial_end

        if self.status == "active" and self.end_date:
            return now <= self.end_date

        return False     
        
        
        
        
class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)

    # Discount types
    discount_percent = models.FloatField(null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Bonus time (THIS is important)
    extra_days = models.IntegerField(default=0)

    max_uses = models.IntegerField(null=True, blank=True)
    used_count = models.IntegerField(default=0)

    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()

    is_active = models.BooleanField(default=True)

    def is_valid(self):
        now = timezone.now()
        return (
            self.is_active and
            self.valid_from <= now <= self.valid_to and
            (self.max_uses is None or self.used_count < self.max_uses)
        )