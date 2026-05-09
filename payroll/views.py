# payroll/views.py

from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django.http import HttpResponse

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from openpyxl import Workbook

from employees.models import Employee
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
    EmployeeSalaryOverride
)

from .serializers import (
    SalaryComponentSerializer,
    CompanySalaryStructureSerializer,
    PositionSalarySerializer,
    PositionSalaryComponentSerializer,
    EmployeeSalaryOverrideSerializer,
    PayrollRunListSerializer,
    PayrollRunDetailSerializer,
    PayrollInputSerializer,
    PayslipListSerializer,
    PayslipDetailSerializer,
    AttendanceSerializer,
    HolidaySerializer,
    EmployeeSalaryOverrideSerializer
)


from attendance.services import AttendanceService

# your payroll engine
from .utils import PayrollService


# ==========================================================
# BASE MIXIN
# ==========================================================

class CompanyScopedMixin:
    permission_classes = [IsAuthenticated]

    def company_id(self):
        return self.request.user.company_id


# ==========================================================
# SALARY COMPONENTS
# ==========================================================

class SalaryComponentViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = SalaryComponentSerializer

    def get_queryset(self):
        return SalaryComponent.objects.filter(
            company_id=self.company_id()
        ).order_by("name")

    def perform_create(self, serializer):
        serializer.save(company_id=self.company_id())


# ==========================================================
# COMPANY SALARY STRUCTURE
# ==========================================================

class CompanySalaryStructureViewSet(
    CompanyScopedMixin,
    viewsets.ModelViewSet
):
    serializer_class = CompanySalaryStructureSerializer

    def get_queryset(self):
        return CompanySalaryStructure.objects.filter(
            company_id=self.company_id()
        ).select_related("component")


# ==========================================================
# POSITION SALARY
# ==========================================================

class PositionSalaryViewSet(
    CompanyScopedMixin,
    viewsets.ModelViewSet
):
    serializer_class = PositionSalarySerializer

    def get_queryset(self):
        return PositionSalary.objects.filter(
            company_id=self.company_id()
        ).select_related(
            "position"
        ).prefetch_related(
            "components__component"
        )

    def perform_create(self, serializer):
        serializer.save(company_id=self.company_id())


# ==========================================================
# POSITION COMPONENTS
# ==========================================================

class PositionSalaryComponentViewSet(
    CompanyScopedMixin,
    viewsets.ModelViewSet
):
    serializer_class = PositionSalaryComponentSerializer

    def get_queryset(self):
        return PositionSalaryComponent.objects.filter(
            position_salary__company_id=self.company_id()
        ).select_related(
            "position_salary",
            "component"
        )


# ==========================================================
# EMPLOYEE OVERRIDES
# ==========================================================

class EmployeeSalaryOverrideViewSet(
    CompanyScopedMixin,
    viewsets.ModelViewSet
):
    serializer_class = EmployeeSalaryOverrideSerializer

    def get_queryset(self):
        return EmployeeSalaryOverride.objects.filter(
            employee__company_id=self.company_id()
        ).select_related(
            "employee",
            "component"
        )


# ==========================================================
# ATTENDANCE
# ==========================================================

class AttendanceViewSet(
    CompanyScopedMixin,
    viewsets.ModelViewSet
):
    serializer_class = AttendanceSerializer

    def get_queryset(self):
        return Attendance.objects.filter(
            employee__company_id=self.company_id()
        ).select_related("employee")


# ==========================================================
# HOLIDAYS
# ==========================================================

class HolidayViewSet(
    CompanyScopedMixin,
    viewsets.ModelViewSet
):
    serializer_class = HolidaySerializer

    def get_queryset(self):
        return Holiday.objects.filter(
            company_id=self.company_id()
        )


# ==========================================================
# PAYROLL INPUTS
# ==========================================================

class PayrollInputViewSet(
    CompanyScopedMixin,
    viewsets.ModelViewSet
):
    serializer_class = PayrollInputSerializer

    def get_queryset(self):
        return PayrollInput.objects.filter(
            payroll__company_id=self.company_id()
        ).select_related(
            "employee",
            "component",
            "payroll"
        )


# ==========================================================
# PAYROLL RUN
# ==========================================================

class PayrollRunViewSet(
    CompanyScopedMixin,
    viewsets.ModelViewSet
):

    def get_queryset(self):
        return PayrollRun.objects.filter(
            company_id=self.company_id()
        ).prefetch_related(
            "inputs__employee",
            "inputs__component",
            "payslips__employee",
            "payslips__items"
        ).order_by("-year", "-month")

    def get_serializer_class(self):
        if self.action in ["list"]:
            return PayrollRunListSerializer
        return PayrollRunDetailSerializer

    def perform_create(self, serializer):
        serializer.save(company_id=self.company_id())
        
    @action(detail=False, methods=["post"])    
    def run(self,request):
        month = self.request.data.get('month')
        year = self.request.data.get('year')
        company = self.company_id()
        try:
            AttendanceService.run_attendance(company,month,year)
            PayrollService.run_payroll(company,month,year)
            print("month",month,"year:",year)
            #payroll.process()

            return Response({
                "message": "Payroll processed successfully"
            })

        except Exception as e:
            print("Error located here",str(e))
            return Response({
                "error": str(e)
            }, status=400)
            
    
    # --------------------------------------------------
    # PROCESS PAYROLL
    # --------------------------------------------------
    """
    @action(detail=, methods=["post"])
    def process(self, request, pk=None):
        

        try:
            # PayrollService.run_payroll(payroll)
            payroll.process()

            return Response({
                "message": "Payroll processed successfully"
            })

        except Exception as e:
            return Response({
                "error": str(e)
            }, status=400)
    """
    # --------------------------------------------------
    # MARK PAID
    # --------------------------------------------------
    @action(detail=True, methods=["post"])
    def mark_paid(self, request, pk=None):
        payroll = self.get_object()

        try:
            payroll.mark_paid()

            return Response({
                "message": "Payroll marked as paid"
            })

        except Exception as e:
            print(e)
            return Response({
                "error": str(e)
            }, status=400)

    # --------------------------------------------------
    # PREVIEW TOTALS
    # --------------------------------------------------
    @action(detail=True, methods=["get"])
    def summary(self, request, pk=None):
        payroll = self.get_object()

        totals = payroll.payslips.aggregate(
            total_basic=Sum("basic_salary"),
            total_allowance=Sum("total_allowance"),
            total_deduction=Sum("total_deduction"),
            total_net=Sum("net_salary"),
        )

        return Response(totals)

    # --------------------------------------------------
    # EXPORT EXCEL
    # --------------------------------------------------
    @action(detail=True, methods=["get"])
    def export_excel(self, request, pk=None):
        payroll = self.get_object()
        print("payroll data for export_excel",payroll)
        wb = Workbook()
        ws = wb.active
        ws.title = "Payroll"

        ws.append([
            "Employee",
            "Basic Salary",
            "Allowance",
            "Deduction",
            "Net Salary",
        ])

        for slip in payroll.payslips.all():
            ws.append([
                str(slip.employee),
                slip.basic_salary,
                slip.total_allowance,
                slip.total_deduction,
                slip.net_salary,
            ])

        response = HttpResponse(
            content_type=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            )
        )

        response[
            "Content-Disposition"
        ] = f'attachment; filename="payroll_{payroll.month}_{payroll.year}.xlsx"'

        wb.save(response)
        return response


# ==========================================================
# PAYSLIPS
# ==========================================================

class PayslipViewSet(
    CompanyScopedMixin,
    viewsets.ReadOnlyModelViewSet
):

    def get_queryset(self):
        return Payslip.objects.filter(
            payroll__company_id=self.company_id()
        ).select_related(
            "employee",
            "payroll"
        ).prefetch_related(
            "items"
        ).order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PayslipDetailSerializer
        return PayslipListSerializer


# ==========================================================
# EMPLOYEE PAYSLIPS
# ==========================================================

@api_view(["GET"])
def employee_payslips(request, employee_id):
    employee = get_object_or_404(
        Employee,
        id=employee_id,
        company_id=request.user.company_id
    )

    payslips = Payslip.objects.filter(
        employee=employee
    ).select_related(
        "payroll"
    ).prefetch_related(
        "items"
    ).order_by("-created_at")

    serializer = PayslipListSerializer(
        payslips,
        many=True
    )

    return Response(serializer.data)
    
# apps/payroll/views/salary_views.py  (or wherever you keep payroll views)

  # Adjust import path
# ==========================================================
# Employee salary Override VIEW
# ==========================================================


class EmployeeSalaryOverrideViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = EmployeeSalaryOverrideSerializer
    queryset = EmployeeSalaryOverride.objects.all()

    def get_queryset(self):
        return EmployeeSalaryOverride.objects.filter(
            employee__company_id=self.company_id()
        ).select_related('employee', 'component').order_by('-id')

    def perform_create(self, serializer):
        serializer.save()
        # No need to manually set company as it's linked via employee

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['company_id'] = self.company_id()
        return context    
    
    
# payroll/views.py
# ADD THIS TO YOUR EXISTING views.py

from django.db.models import Sum, Count, Q
from rest_framework.views import APIView


# ==========================================================
# DASHBOARD VIEW
# ==========================================================

class PayrollDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company_id = request.user.company_id

        # --------------------------------------------------
        # COUNTS
        # --------------------------------------------------
        employee_count = Employee.objects.filter(
            company_id=company_id
        ).count()

        active_payrolls = PayrollRun.objects.filter(
            company_id=company_id
        ).exclude(status="paid").count()

        processed_payrolls = PayrollRun.objects.filter(
            company_id=company_id,
            status="processed"
        ).count()

        # --------------------------------------------------
        # TOTAL PAYROLL COST
        # --------------------------------------------------
        payroll_total = Payslip.objects.filter(
            payroll__company_id=company_id
        ).aggregate(
            total=Sum("net_salary")
        )["total"] or 0

        # --------------------------------------------------
        # LATEST PAYROLL
        # --------------------------------------------------
        latest = PayrollRun.objects.filter(
            company_id=company_id
        ).order_by("-year", "-month").first()

        latest_data = None

        if latest:
            latest_data = {
                "id": latest.id,
                "month": latest.month,
                "year": latest.year,
                "status": latest.status,
                "payslips": latest.payslips.count()
            }

        # --------------------------------------------------
        # ATTENDANCE TODAY
        # --------------------------------------------------
        from django.utils.timezone import now

        today = now().date()

        attendance_today = Attendance.objects.filter(
            employee__company_id=company_id,
            date=today
        ).count()

        # --------------------------------------------------
        # RESPONSE
        # --------------------------------------------------
        return Response({
            "employees": employee_count,
            "active_payrolls": active_payrolls,
            "processed_payrolls": processed_payrolls,
            "attendance_today": attendance_today,
            "total_payroll_paid": payroll_total,
            "latest_payroll": latest_data
        })    