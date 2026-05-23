import uuid
from django.db import models,transaction



class IDCounter(models.Model):
    name = models.CharField(max_length=100, unique=True) # e.g., "AutoSheck"
    last_value = models.PositiveIntegerField(default=0)

    def next_id(self):
        with transaction.atomic():
            # select_for_update() locks the row so two people 
            # can't get the same number at once
            counter, created = IDCounter.objects.select_for_update().get_or_create(name=self.name)
            counter.last_value += 1
            counter.save()
            return counter.last_value




class Company(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.CharField(max_length=100, unique=True, editable=False)
    
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    country = models.CharField(max_length=100, default="Nigeria")
    timezone = models.CharField(max_length=50, default="Africa/Lagos")
    created_at = models.DateTimeField(auto_now_add=True)
    
    
    def save(self, *args, **kwargs):
        if not self.company_id:
            # 1. Get the next number for this specific company
            counter = IDCounter()
            counter.name = self.name
            new_number = counter.next_id()
            
            # 2. Format it: AutoSheck-0001
            # :04d ensures the number is at least 4 digits long
            self.company_id = f"{(self.name).upper()}{new_number:04d}"
            
        super().save(*args, **kwargs)
        
        
    def __str__(self):
         return self.name
         
         
         
class CompanySettings(models.Model):
    organization = models.OneToOneField(Company, on_delete=models.CASCADE, related_name="settings")
    date_format = models.CharField(max_length=20, default="YYYY-MM-DD")
    working_days = models.JSONField(default=list)      
    
#note : move this to the attendance app later not here
   # models.py

class AttendanceSettings(models.Model):
    organization = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name="attendance_settings"
    )
    opening_time = models.TimeField(null=True,blank=True)
    closing_time = models.TimeField(null=True,blank=True)
    
    work_hours_per_day = models.PositiveIntegerField(default=8)

    allow_late_arrival = models.BooleanField(default=True)

    late_arrival_grace_minutes = models.PositiveIntegerField(default=15)

    require_face_verification = models.BooleanField(default=False)

    geo_fencing_enabled = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.organization.name} Attendance Settings"
        
# models.py

class PayrollSettings(models.Model):
    organization = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name="payroll_settings"
    )

    payroll_day = models.PositiveIntegerField(default=25)

    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=7.50
    )

    allow_manual_payslip = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.organization.name} Payroll Settings"        

# models.py

class LeaveSettings(models.Model):
    organization = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name="leave_settings"
    )

    default_annual_leave_days = models.PositiveIntegerField(default=21)

    default_sick_leave_days = models.PositiveIntegerField(default=10)

    carry_forward_enabled = models.BooleanField(default=True)

    max_carry_forward_days = models.PositiveIntegerField(default=10)

    leave_approval_required = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.organization.name} Leave Settings"
        
# models.py

class SystemSettings(models.Model):
    organization = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name="system_settings"
    )

    email_notifications_enabled = models.BooleanField(default=True)

    allow_self_registration = models.BooleanField(default=False)

    maintenance_mode = models.BooleanField(default=False)

    session_timeout_minutes = models.PositiveIntegerField(default=60)

    def __str__(self):
        return f"{self.organization.name} System Settings"

# models.py

class WorkLocation(models.Model):
    organization = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name="work_location"
    )

    name = models.CharField(max_length=255, default="Head Office")

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )

    radius_meters = models.PositiveIntegerField(default=100)

    is_enabled = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.organization.name} Work Location"                



