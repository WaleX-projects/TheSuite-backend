from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.decorators import api_view

from django.utils import timezone
from django.db.models import Sum

from .models import Company, CompanySettings
from .serializers import CompanySerializer, CompanySettingsSerializer

from appsettings.models import CompanySettings
from employees.models import Employee
from payroll.models import PayrollRun, Payslip
from leave.models import LeaveRequest  # if you have it

class CompanyListView(generics.ListAPIView):
    serializer_class = CompanySerializer
    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return Company.objects.all()
        return Company.objects.filter(id=self.request.user.company_id)
        
        
        


@api_view(["GET"])
def dashboard_stats(request):
    user = request.user
    company_id = user.company_id
    today = timezone.localdate()
    current_year = today.year
    current_month = today.month
    # Employees
    total_employees = Employee.objects.filter(
        company_id=company_id,
        status="active"
    ).count()

    # Payroll runs
    total_payroll = Payslip.objects.filter(
        payroll__company_id=company_id,
        payroll__month=current_month,
        payroll__year=current_year,
        payroll__status="draft"
    ).aggregate(total=Sum("net_salary"))["total"] or 0

    # Leaves (SAFE)
    active_leaves = 0
    if 'LeaveRequest' in globals():
        active_leaves = LeaveRequest.objects.filter(
            employee__company_id=company_id,
            status="approved"
        ).count()
    if user.role == 'super_admin':
        active_companies = Company.objects.all().count()
        
        return Response({
            "totalEmployees": total_employees,
            "activeLeaves": active_leaves,
            "totalPayroll": total_payroll,
            "activeCompanies": active_companies,
        })
    return Response({
        "totalEmployees": total_employees,
        "activeLeaves": active_leaves,
        "totalPayroll": total_payroll,
    })
    
    
    



# views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .models import CompanySettings
from .serializers import CompanySettingsSerializer


class CompanySettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get_company_settings(self, request):
        """
        Assumes user has a company relation:
        request.user.company
        """

        company = request.user.company

        settings, created = CompanySettings.objects.get_or_create(
            organization=company,
            defaults={
                "date_format": "YYYY-MM-DD",
                "working_days": [
                    "Monday",
                    "Tuesday",
                    "Wednesday",
                    "Thursday",
                    "Friday",
                ]
            }
        )

        return settings

    def get(self, request):
        settings = self.get_company_settings(request)

        serializer = CompanySettingsSerializer(settings)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        settings = self.get_company_settings(request)

        serializer = CompanySettingsSerializer(
            settings,
            data=request.data,
            partial=False
        )

        if serializer.is_valid():
            serializer.save()

            return Response(
                serializer.data,
                status=status.HTTP_200_OK
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    def patch(self, request):
        settings = self.get_company_settings(request)

        serializer = CompanySettingsSerializer(
            settings,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()

            return Response(
                serializer.data,
                status=status.HTTP_200_OK
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
        
        
# views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .models import AttendanceSettings
from .serializers import AttendanceSettingsSerializer


class AttendanceSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request):
        company = request.user.company

        settings, created = AttendanceSettings.objects.get_or_create(
            organization=company
        )

        return settings

    # GET ATTENDANCE SETTINGS
    def get(self, request):
        settings = self.get_object(request)

        serializer = AttendanceSettingsSerializer(settings)

        return Response(serializer.data)

    # UPDATE ATTENDANCE SETTINGS
    def patch(self, request):
        settings = self.get_object(request)

        serializer = AttendanceSettingsSerializer(
            settings,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()

            return Response(serializer.data)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        ) 
        
# views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .models import PayrollSettings
from .serializers import PayrollSettingsSerializer


class PayrollSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request):
        company = request.user.company

        settings, created = PayrollSettings.objects.get_or_create(
            organization=company
        )

        return settings

    # GET PAYROLL SETTINGS
    def get(self, request):
        settings = self.get_object(request)

        serializer = PayrollSettingsSerializer(settings)

        return Response(serializer.data)

    # UPDATE PAYROLL SETTINGS
    def patch(self, request):
        settings = self.get_object(request)

        serializer = PayrollSettingsSerializer(
            settings,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()

            return Response(serializer.data)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        ) 
        
# views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .models import LeaveSettings
from .serializers import LeaveSettingsSerializer


class LeaveSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request):
        company = request.user.company

        settings, created = LeaveSettings.objects.get_or_create(
            organization=company
        )

        return settings

    # GET LEAVE SETTINGS
    def get(self, request):
        settings = self.get_object(request)

        serializer = LeaveSettingsSerializer(settings)

        return Response(serializer.data)

    # UPDATE LEAVE SETTINGS
    def patch(self, request):
        settings = self.get_object(request)

        serializer = LeaveSettingsSerializer(
            settings,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()

            return Response(serializer.data)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )  
        
# views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .models import SystemSettings
from .serializers import SystemSettingsSerializer


class SystemSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request):
        company = request.user.company

        settings, created = SystemSettings.objects.get_or_create(
            organization=company
        )

        return settings

    # GET SYSTEM SETTINGS
    def get(self, request):
        settings = self.get_object(request)

        serializer = SystemSettingsSerializer(settings)

        return Response(serializer.data)

    # UPDATE SYSTEM SETTINGS
    def patch(self, request):
        settings = self.get_object(request)

        serializer = SystemSettingsSerializer(
            settings,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()

            return Response(serializer.data)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        ) 
        
# views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .models import WorkLocation
from .serializers import WorkLocationSerializer


class WorkLocationView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request):
        company = request.user.company

        location, created = WorkLocation.objects.get_or_create(
            organization=company
        )

        return location

    # GET
    def get(self, request):
        location = self.get_object(request)

        serializer = WorkLocationSerializer(location)

        return Response(serializer.data)

    # UPDATE
    def patch(self, request):
        location = self.get_object(request)

        serializer = WorkLocationSerializer(
            location,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )                                   