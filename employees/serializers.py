

from rest_framework import serializers
from .models import Employee, Position, Department
from companies.models import IDCounter
from payroll.models import PositionSalary,SalaryComponent,PositionSalaryComponent
from payroll.serializers import (PositionSalarySerializer,
        PositionSalaryComponentSerializer,
        SalaryComponentSerializer)

        
class DepartmentSerializer(serializers.ModelSerializer):
    # This matches the name we used in .annotate() in the view
    total_positions = serializers.IntegerField(read_only=True)

    class Meta:
        model = Department
        fields = ["id", "name", "company", "total_positions"]
        read_only_fields = ("id", "company")


class ComponentInputSerializer(serializers.Serializer):
    name = serializers.CharField()
    value = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    
    
    
    
    
    
class PositionSerializer(serializers.ModelSerializer):
    # WRITE
    components = ComponentInputSerializer(many=True, write_only=True)

    # READ
    components_display = serializers.SerializerMethodField()

    # WRITE
    basic_salary = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        write_only=True
    )

    # READ
    basic_salary_display = serializers.DecimalField(
        source="salary.basic_salary",
        max_digits=12,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = Position
        fields = [
            "id",
            "title",
            "department",
            "is_single_role",

            "components",           # write
            "components_display",   # read

            "basic_salary",         # write
            "basic_salary_display"  # read
        ]

    def get_components_display(self, obj):
        try:
            
            salary = obj.salary
        except PositionSalary.DoesNotExist:
            return []
        

        return PositionSalaryComponentSerializer(
            salary.components.all(),
            many=True
        ).data
    def create(self, validated_data):
        components_data = validated_data.pop("components", [])
        basic_salary = validated_data.pop("basic_salary")

        # Create Position
        position = Position.objects.create(**validated_data)
        company = position.department.company

        # Create PositionSalary
        position_salary = PositionSalary.objects.create(
            position=position,
            company=company,
            basic_salary=basic_salary,
        )

        # Create components
        for comp in components_data:
            component, _ = SalaryComponent.objects.get_or_create(
                company=company,
                name=comp["name"]
            )

            PositionSalaryComponent.objects.create(
                position_salary=position_salary,
                component=component,
                value=comp["value"]   # ✅ value should be here (IMPORTANT)
            )

        return position
    

    
            
    
    def update(self, instance, validated_data):
        components_data = validated_data.pop("components", [])
        basic_salary = validated_data.pop("basic_salary", None)

        # Update Position fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        company = instance.department.company

        # Get or create salary
        position_salary, _ = PositionSalary.objects.get_or_create(
            position=instance,
            company=company,
            basic_salary=basic_salary,
        )

        # Update basic salary
        if basic_salary is not None:
            position_salary.basic_salary = basic_salary
            position_salary.save()

        # ❌ Remove old components (important)
        position_salary.components.all().delete()

        # ✅ Recreate components
        for comp in components_data:
            component, _ = SalaryComponent.objects.get_or_create(
                company=company,
                name=comp["name"]
            )

            PositionSalaryComponent.objects.create(
                position_salary=position_salary,
                component=component,
                value=comp["value"]
            )

        return instance        

class EmployeeSerializer(serializers.ModelSerializer):
    #  Write (input)
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(),
        write_only=True
    )
    position = serializers.PrimaryKeyRelatedField(
        queryset=Position.objects.all(),
        write_only=True
    )

    # 💳 BANK (write-only input)
    bank_account_number = serializers.CharField(write_only=True)
    bank_code = serializers.CharField()
    #  Read (output)
    department_detail = serializers.CharField(source="department.name", read_only=True)
    position_detail = serializers.CharField(source="position.title", read_only=True)
    department_id = serializers.CharField(source="department.id", read_only=True)
    position_id = serializers.CharField(source="position.id", read_only=True)
    
    company_detail = serializers.CharField(source="company.name", read_only=True)
    face_verified = serializers.BooleanField(read_only=True) 
    masked_account_number = serializers.SerializerMethodField()
    

    def get_masked_account_number(self, obj):
        if obj.bank_account_number:
            return obj.bank_account_number
        return None

    class Meta:
        model = Employee
        fields = [
            "id",
            "company",
            "company_detail",
            "first_name",
            "last_name",
            "email",
            "phone",
            "hire_date",
            "status",
            "face_verified",
            "date_of_birth",
            "address",
            

            # write-only inputs
            "department",
            "position",
            "bank_account_number",
            "bank_code",

            # read-only outputs
            "department_detail",
            "position_detail",
           "department_id",
           "position_id",

            # 💳 bank outputsq
            "bank_name",
            "bank_account_type",
            "currency",
            "masked_account_number",
            
            "bank_account_name",
            
        ]
        read_only_fields = ["id", "company"]
        



import pandas as pd
from decimal import Decimal

from rest_framework import serializers
from django.db import transaction
from django.utils.dateparse import parse_date
from subscriptions.utils import get_active_subscription


class BulkEmployeeUploadSerializer(serializers.Serializer):
    file = serializers.FileField(required=True)

    def validate_file(self, file):
        if not file.name.lower().endswith((".xlsx", ".xls", ".csv")):
            raise serializers.ValidationError(
                "Only Excel (.xlsx, .xls) or CSV files are allowed."
            )
        return file

    def create(self, validated_data):
        file = validated_data["file"]

        request = self.context.get("request")
        if not request or not request.user:
            raise serializers.ValidationError("Request context is required")

        company = request.user.company

        # =========================
        # READ FILE
        # =========================
        # =========================
        # READ FILE FIRST
        # =========================
        try:
            if file.name.lower().endswith(".csv"):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
        except Exception as e:
            raise serializers.ValidationError(f"Failed to read file: {str(e)}")
        
        
        # =========================
        # SUBSCRIPTION LIMIT CHECK
        # =========================
        company = request.user.company
        existing_count = Employee.objects.filter(company=company).count()
        incoming_count = len(df)
        
        plan = get_active_subscription(company).plan
        
        if plan.max_employees is not None:
            if existing_count + incoming_count > plan.max_employees:
                raise serializers.ValidationError({
                    "code": "EMPLOYEE_LIMIT",
                    "message": (
                        f"This upload will exceed your plan limit. "
                        f"You have {existing_count}/{plan.max_employees} employees "
                        f"and are trying to add {incoming_count} more."
                    )
                })
        employees_to_create = []
        position_salaries_to_create = []
        position_components_to_create = []
        errors = []

        # =========================
        # PRELOAD DATA
        # =========================
        departments = {
            d.name.lower(): d
            for d in Department.objects.filter(company=company)
        }

        positions = {
            p.title.lower(): p
            for p in Position.objects.filter(company=company)
        }

        salary_components = {
            sc.name.lower(): sc
            for sc in SalaryComponent.objects.filter(company=company)
        }

        existing_emails = set(
            Employee.objects.filter(company=company)
            .values_list("email", flat=True)
        )

        # =========================
        # PROCESS
        # =========================
        with transaction.atomic():
            counter_obj, _ = IDCounter.objects.select_for_update().get_or_create(
                name=company.name
            )
            current_val = counter_obj.last_value

            for index, row in df.iterrows():
                row_num = index + 2

                try:
                    # -------------------------
                    # DEPARTMENT
                    # -------------------------
                    dept_name = str(
                        row.get("department") or row.get("Department") or ""
                    ).strip().lower()

                    if not dept_name:
                        raise ValueError("Department is required")

                    department = departments.get(dept_name)
                    if not department:
                        department = Department.objects.create(
                            company=company,
                            name=dept_name.title()
                        )
                        departments[dept_name] = department

                    # -------------------------
                    # POSITION
                    # -------------------------
                    pos_name = str(
                        row.get("position") or row.get("Position") or ""
                    ).strip().lower()

                    if not pos_name:
                        raise ValueError("Position is required")

                    position = positions.get(pos_name)
                    if not position:
                        position = Position.objects.create(
                            company=company,
                            title=pos_name.title(),
                            department=department
                        )
                        positions[pos_name] = position

                    # -------------------------
                    # BASIC SALARY
                    # -------------------------
                    basic_salary_val = row.get("basic_salary") or row.get("Basic Salary")
                    if not basic_salary_val:
                        raise ValueError("basic_salary is required")

                    basic_salary = Decimal(str(basic_salary_val))

                    position_salary, created = PositionSalary.objects.get_or_create(
                        company=company,
                        position=position,
                        defaults={"basic_salary": basic_salary}
                    )

                    # -------------------------
                    # COMPONENTS (OPTIONAL COLUMNS)
                    # Example columns:
                    # allowance_housing, deduction_tax
                    # -------------------------
                    for col in row.index:
                        col_lower = str(col).lower()

                        if col_lower.startswith("allowance_") or col_lower.startswith("deduction_"):
                            value = row.get(col)

                            if value in [None, "", 0]:
                                continue

                            component_type = (
                                "allowance" if col_lower.startswith("allowance_") else "deduction"
                            )

                            comp_name = col_lower.split("_", 1)[1]

                            component = salary_components.get(comp_name)

                            if not component:
                                component = SalaryComponent.objects.create(
                                    company=company,
                                    name=comp_name.title(),
                                    component_type=component_type
                                )
                                salary_components[comp_name] = component

                            position_components_to_create.append(
                                PositionSalaryComponent(
                                    position_salary=position_salary,
                                    component=component,
                                    value=Decimal(str(value))
                                )
                            )

                    # -------------------------
                    # EMPLOYEE
                    # -------------------------
                    hire_date_str = row.get("hire_date") or row.get("Hire Date")
                    hire_date = parse_date(str(hire_date_str)) if hire_date_str else None

                    if not hire_date:
                        raise ValueError("Valid hire_date is required")

                    first_name = str(
                        row.get("first_name") or row.get("First Name") or ""
                    ).strip()

                    last_name = str(
                        row.get("last_name") or row.get("Last Name") or ""
                    ).strip()

                    email = str(
                        row.get("email") or row.get("Email") or ""
                    ).strip().lower()

                    if not first_name or not last_name or not email:
                        raise ValueError("Missing required employee fields")

                    if email in existing_emails:
                        raise ValueError("Email already exists")

                    current_val += 1
                    custom_id = f"{company.name.upper()}-EMP-{current_val:04d}"

                    employee = Employee(
                        employee_id=custom_id,
                        company=company,
                        first_name=first_name,
                        last_name=last_name,
                        email=email,
                        phone=str(row.get("phone") or "").strip(),
                        hire_date=hire_date,
                        department=department,
                        position=position,
                        status=str(row.get("status", "active")).strip().lower(),

                        bank_name=str(row.get("bank_name") or "").strip() or None,
                        bank_account_name=str(row.get("bank_account_name") or "").strip() or None,
                        bank_account_number=str(row.get("bank_account_number") or "").strip() or None,
                        bank_code=str(row.get("bank_code") or "").strip() or None,
                        bank_account_type=str(row.get("bank_account_type", "savings")).strip().lower(),
                        currency=str(row.get("currency", "NGN")).strip().upper(),
                    )

                    employees_to_create.append(employee)
                    existing_emails.add(email)

                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")

            # =========================
            # SAVE COUNTER
            # =========================
            counter_obj.last_value = current_val
            counter_obj.save()

            # =========================
            # ERRORS
            # =========================
            if errors:
                raise serializers.ValidationError({
                    "message": "Some rows failed",
                    "errors": errors[:20]
                })

            # =========================
            # BULK INSERTS
            # =========================
            if employees_to_create:
                Employee.objects.bulk_create(employees_to_create, batch_size=500)

            if position_components_to_create:
                PositionSalaryComponent.objects.bulk_create(
                    position_components_to_create,
                    batch_size=500
                )

        return {
            "message": "Upload successful",
            "employees_created": len(employees_to_create),
        }