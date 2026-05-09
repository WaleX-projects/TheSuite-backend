import uuid
from django.db import models
from employees.models import Employee, Position
from companies.models import Company


# =========================
# 💰 SALARY COMPONENT (MASTER)
# =========================
class SalaryComponent(models.Model):
    COMPONENT_TYPE = (
        ("allowance", "Allowance"),
        ("deduction", "Deduction"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="salary_components"
    )

    name = models.CharField(max_length=255)
    component_type = models.CharField(max_length=20, choices=COMPONENT_TYPE,default="allowance")

    is_percentage = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.component_type})"


# =========================
# 🏢 COMPANY DEFAULT STRUCTURE
# =========================
class CompanySalaryStructure(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="salary_structures"
    )

    component = models.ForeignKey(
        SalaryComponent,
        on_delete=models.CASCADE
    )

    default_value = models.DecimalField(max_digits=10, decimal_places=2)

    is_mandatory = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.company.name} - {self.component.name}"


# =========================
# 🧑‍💼 POSITION SALARY
# =========================
class PositionSalary(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="position_salaries"
    )

    position = models.OneToOneField(
        Position,
        on_delete=models.CASCADE,
        related_name="salary"
    )

    basic_salary = models.DecimalField(max_digits=12, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.position.title} - {self.basic_salary}"


# =========================
# 📊 POSITION COMPONENTS
# =========================
class PositionSalaryComponent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    position_salary = models.ForeignKey(
        PositionSalary,
        on_delete=models.CASCADE,
        related_name="components"
    )

    component = models.ForeignKey(
        SalaryComponent,
        on_delete=models.CASCADE
    )

    value = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.position_salary.position.title} - {self.component.name}"


# =========================
# 👤 EMPLOYEE OVERRIDES
# =========================
class EmployeeSalaryOverride(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="salary_overrides"
    )

    component = models.ForeignKey(
        SalaryComponent,
        on_delete=models.CASCADE
    )

    value = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.employee} - {self.component.name}"


# =========================
# 📆 PAYROLL RUN
# =========================
class PayrollRun(models.Model):
    STATUS = (
        ("draft", "Draft"),
        ("paid", "Paid"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="payrolls"
    )

    month = models.IntegerField()
    year = models.IntegerField()

    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="draft"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("company", "month", "year")

    def can_edit(self):
        return self.status == "draft"
        
    
    def mark_paid(self):
        if self.status != "draft":
            raise Exception("Only drafted payroll can be paid")
        self.status = "paid"
        self.save()

    def __str__(self):
        return f"{self.company.name} - {self.month}/{self.year}"


# =========================
# 🧾 PAYROLL INPUT (VARIABLE DATA)
# =========================
class PayrollInput(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    payroll = models.ForeignKey(
        PayrollRun,
        on_delete=models.CASCADE,
        related_name="inputs"
    )

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE
    )

    component = models.ForeignKey(
        SalaryComponent,
        on_delete=models.CASCADE
    )

    value = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.employee} - {self.component.name}"


# =========================
# 🧾 PAYSLIP (SNAPSHOT)
# =========================
class Payslip(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    payroll = models.ForeignKey(
        PayrollRun,
        on_delete=models.CASCADE,
        related_name="payslips"
    )

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="payslips"
    )

    basic_salary = models.DecimalField(max_digits=12, decimal_places=2)

    total_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    net_salary = models.DecimalField(max_digits=12, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee} - {self.payroll.month}/{self.payroll.year}"


# =========================
# 🧾 PAYSLIP ITEMS (BREAKDOWN)
# =========================
class PayslipItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    payslip = models.ForeignKey(
        Payslip,
        on_delete=models.CASCADE,
        related_name="items"
    )

    component = models.ForeignKey(
        SalaryComponent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    name = models.CharField(max_length=255)

    component_type = models.CharField(max_length=20)

    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.name} - {self.amount}"
        
        
"""   
# =========================
# 🇳🇬 TAX CONFIG
# =========================
class TaxBracket(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)

    min_income = models.DecimalField(max_digits=12, decimal_places=2)
    max_income = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    rate = models.DecimalField(max_digits=5, decimal_places=2)  # %

    def __str__(self):
        return f"{self.rate}% ({self.min_income} - {self.max_income})"      
        
        
        
# =========================
# 🏦 STATUTORY SETTINGS
# =========================
class StatutorySetting(models.Model):
    company = models.OneToOneField(Company, on_delete=models.CASCADE)

    pension_employee_percent = models.DecimalField(max_digits=5, decimal_places=2, default=8)
    pension_employer_percent = models.DecimalField(max_digits=5, decimal_places=2, default=10)

    nhf_percent = models.DecimalField(max_digits=5, decimal_places=2, default=2.5)

    def __str__(self):
        return self.company.name          

# =========================
# 💳 EMPLOYEE LOANS
# =========================
class EmployeeLoan(models.Model):
    STATUS = (
        ("ongoing", "Ongoing"),
        ("completed", "Completed"),
    )

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)

    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    monthly_deduction = models.DecimalField(max_digits=10, decimal_places=2)

    balance = models.DecimalField(max_digits=12, decimal_places=2)

    status = models.CharField(max_length=20, choices=STATUS, default="ongoing")

    def __str__(self):
        return f"{self.employee} Loan"
        
        
"""