# serializers.py

from rest_framework import serializers

from companies.models import Company
from employees.models import Employee, Position
from attendance.models import Attendance, Holiday

from .models import (
    SalaryComponent,
    CompanySalaryStructure,
    PositionSalary,
    PositionSalaryComponent,
    EmployeeSalaryOverride,
    PayrollRun,
    PayrollInput,
    Payslip,
    PayslipItem,
)


# =====================================================
# 🔹 COMMON / LIGHT SERIALIZERS
# =====================================================

class CompanyMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ["id", "name"]


class PositionMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = ["id", "title"]


class EmployeeMiniSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = ["id", "full_name"]

    def get_full_name(self, obj):
        first = getattr(obj, "first_name", "") or ""
        last = getattr(obj, "last_name", "") or ""
        return f"{first} {last}".strip()


# =====================================================
# 💰 SALARY COMPONENT
# =====================================================

class SalaryComponentSerializer(serializers.ModelSerializer):
    company_detail = CompanyMiniSerializer(source="company", read_only=True)

    class Meta:
        model = SalaryComponent
        fields = [
            "id",
            "company",
            "company_detail",
            "name",
            "component_type",
            "is_percentage",
            "is_active",
        ]


# =====================================================
# 🏢 COMPANY SALARY STRUCTURE
# =====================================================

class CompanySalaryStructureSerializer(serializers.ModelSerializer):
    component_detail = SalaryComponentSerializer(source="component", read_only=True)

    class Meta:
        model = CompanySalaryStructure
        fields = [
            "id",
            "company",
            "component",
            "component_detail",
            "default_value",
            "is_mandatory",
        ]


# =====================================================
# 📊 POSITION COMPONENTS
# =====================================================

class PositionSalaryComponentSerializer(serializers.ModelSerializer):
    component_detail = SalaryComponentSerializer(source="component", read_only=True)

    class Meta:
        model = PositionSalaryComponent
        fields = [
            "id",
            "component",
            "component_detail",
            "value",
        ]


# =====================================================
# 🧑‍💼 POSITION SALARY
# =====================================================

class PositionSalarySerializer(serializers.ModelSerializer):
    company_detail = CompanyMiniSerializer(source="company", read_only=True)
    position_detail = PositionMiniSerializer(source="position", read_only=True)
    components = PositionSalaryComponentSerializer(many=True, read_only=True)

    class Meta:
        model = PositionSalary
        fields = [
            "id",
            "company",
            "company_detail",
            "position",
            "position_detail",
            "basic_salary",
            "components",
            "created_at",
        ]


# =====================================================
# 👤 EMPLOYEE OVERRIDE
# =====================================================

class EmployeeSalaryOverrideSerializer(serializers.ModelSerializer):
    employee_detail = EmployeeMiniSerializer(source="employee", read_only=True)
    component_detail = SalaryComponentSerializer(source="component", read_only=True)

    class Meta:
        model = EmployeeSalaryOverride
        fields = [
            "id",
            "employee",
            "employee_detail",
            "component",
            "component_detail",
            "value",
        ]


# =====================================================
# 📆 PAYROLL INPUT
# =====================================================

class PayrollInputSerializer(serializers.ModelSerializer):
    employee_detail = EmployeeMiniSerializer(source="employee", read_only=True)
    component_detail = SalaryComponentSerializer(source="component", read_only=True)

    class Meta:
        model = PayrollInput
        fields = [
            "id",
            "payroll",
            "employee",
            "employee_detail",
            "component",
            "component_detail",
            "value",
        ]


# =====================================================
# 🧾 PAYSLIP ITEM
# =====================================================

class PayslipItemSerializer(serializers.ModelSerializer):
    component_detail = SalaryComponentSerializer(source="component", read_only=True)

    class Meta:
        model = PayslipItem
        fields = [
            "id",
            "payslip",
            "component",
            "component_detail",
            "name",
            "component_type",
            "amount",
        ]


# =====================================================
# 🧾 PAYSLIP (LIST)
# =====================================================

class PayslipListSerializer(serializers.ModelSerializer):
    employee_detail = EmployeeMiniSerializer(source="employee", read_only=True)
    items = PayslipItemSerializer(many=True, read_only=True)
    
    payroll_month = serializers.IntegerField(source="payroll.month", read_only=True)
    payroll_year = serializers.IntegerField(source="payroll.year", read_only=True)
    payroll_status = serializers.CharField(source="payroll.status", read_only=True)
    
    class Meta:
        model = Payslip
        fields = [
            "id",
            "employee",
            "employee_detail",
            "payroll",
            "payroll_month",
            "payroll_year",
            "payroll_status",
            "basic_salary",
            "total_allowance",
            "total_deduction",
            "net_salary",
             "items",
            "created_at",
        ]
    

# =====================================================
# 🧾 PAYSLIP (DETAIL)
# =====================================================

class PayslipDetailSerializer(serializers.ModelSerializer):
    employee_detail = EmployeeMiniSerializer(source="employee", read_only=True)
    items = PayslipItemSerializer(many=True, read_only=True)

    payroll_month = serializers.IntegerField(source="payroll.month", read_only=True)
    payroll_year = serializers.IntegerField(source="payroll.year", read_only=True)
    payroll_status = serializers.CharField(source="payroll.status", read_only=True)

    class Meta:
        model = Payslip
        fields = [
            "id",
            "employee",
            "employee_detail",
            "payroll",
            "payroll_month",
            "payroll_year",
            "payroll_status",
            "basic_salary",
            "total_allowance",
            "total_deduction",
            "net_salary",
            "items",
            "created_at",
        ]


# =====================================================
# 📆 PAYROLL RUN (LIST)
# =====================================================

class PayrollRunListSerializer(serializers.ModelSerializer):
    company_detail = CompanyMiniSerializer(source="company", read_only=True)
    payslip_count = serializers.IntegerField(source="payslips.count", read_only=True)
    
    class Meta:
        model = PayrollRun
        fields = [
            "id",
            "company",
            "company_detail",
           
            "month",
            "year",
            "status",
            "payslip_count",
            "created_at",
        ]
    def get_total_employee_paid(self,obj):
        company = obj.company
        return Employee.objects.filter(company=company).count()

# =====================================================
# 📆 PAYROLL RUN (DETAIL)
# =====================================================

class PayrollRunDetailSerializer(serializers.ModelSerializer):
    company_detail = CompanyMiniSerializer(source="company", read_only=True)
    payslips = PayslipListSerializer(many=True, read_only=True)
    inputs = PayrollInputSerializer(many=True, read_only=True)

    total_net_salary = serializers.SerializerMethodField()

    class Meta:
        model = PayrollRun
        fields = [
            "id",
            "company",
            "company_detail",
            "month",
            "year",
            "status",
            "inputs",
            "payslips",
            "total_net_salary",
            "created_at",
        ]

    def get_total_net_salary(self, obj):
        return sum([p.net_salary for p in obj.payslips.all()])


# =====================================================
# 🕒 ATTENDANCE
# =====================================================

class AttendanceSerializer(serializers.ModelSerializer):
    employee_detail = EmployeeMiniSerializer(source="employee", read_only=True)

    class Meta:
        model = Attendance
        fields = "__all__"


# =====================================================
# 🎉 HOLIDAY
# =====================================================

class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = "__all__"
        
        
        
        
        
        