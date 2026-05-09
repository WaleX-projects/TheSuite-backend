import uuid
from django.db import models
from companies.models import Company,IDCounter
from accounts.models import User


class Department(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)


class Position(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    is_single_role = models.BooleanField(default=False)
    department = models.ForeignKey(Department, on_delete=models.CASCADE,related_name="positions" )


class Employee(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee_id = models.CharField(max_length=100, unique=True, editable=False)

    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True)
    #image = models.ImageField(upload_to="image")
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    face_verified = models.BooleanField(default=False)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True)
    # =========================
    # 💳 BANK DETAILS
    # =========================
    
    position = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True,related_name="employee")
    bank_name = models.CharField(
        max_length=150,
        blank=True,
        null=True
    )

    bank_account_name = models.CharField(
        max_length=150,
        blank=True,
        null=True
    )

    bank_account_number = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )
    bank_code = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    ACCOUNT_TYPE_CHOICES = [
        ("savings", "Savings"),
        ("current", "Current"),
    ]

    bank_account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_TYPE_CHOICES,
        default="savings",
        blank=True
    )

    CURRENCY_CHOICES = [
        ("NGN", "Naira"),
        ("USD", "Dollar"),
        ("EUR", "Euro"),
    ]

    currency = models.CharField(
        max_length=10,
        choices=CURRENCY_CHOICES,
        default="NGN"
    )
    hire_date = models.DateField()
    
    status = models.CharField(max_length=20, default="active")
    date_deactivate = models.DateField(null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    
    # Address can be a simple CharField or a TextField if it's long
    address = models.TextField(null=True, blank=True)
    def save(self, *args, **kwargs):
        if not self.employee_id:
            # 1. Get the next number for this specific company
            counter = IDCounter()
            counter.name = self.company
            new_number = counter.next_id()
            
            # 2. Format it: AutoSheck-EMP-0001
            # :04d ensures the number is at least 4 digits long
            self.employee_id = f"{(self.company.name).upper()}-EMP-{new_number:04d}"
            
        super().save(*args, **kwargs)
    
    @property
    def masked_account_number(self):
        if self.bank_account_number:
            return "****" + self.bank_account_number[-4:]
        return "****0000"
        
    def get_current_salary(self):
        """Helper to get the most recent salary record."""
        latest = self.salary_history.order_by('-effective_date').first()
        return latest.amount if latest else Decimal('0.00')

    
    

class EmployeeDocument(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    file = models.FileField(upload_to="documents/")
    document_type = models.CharField(max_length=100)