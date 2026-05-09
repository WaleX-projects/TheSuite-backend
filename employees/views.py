from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from .models import Employee,Department, Position
from .serializers import EmployeeSerializer,DepartmentSerializer,PositionSerializer
from accounts.permissions import IsAdminOrHR
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from subscriptions.utils import check_employee_limit

# views.py
import requests
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated,AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
import requests
from django.conf import settings


from django.db.models import Count, Sum, DecimalField
from django.db.models.functions import Coalesce
from rest_framework import viewsets

class PositionViewSet(viewsets.ModelViewSet):
    serializer_class = PositionSerializer
    
    def get_queryset(self):
        user = self.request.user
        queryset = Position.objects.filter(company=self.request.user.company)
        queryset = queryset.annotate(
            total_employees=Count('employee', distinct=True),
            total_salary_cost=Coalesce(
                Sum('salary__basic_salary'), # Ensure this matches your model field
                0, 
                output_field=DecimalField()
            )
        ).prefetch_related('salary').order_by("title") # Added prefetch here!
        
        department_id = self.request.query_params.get("department_id")
        if department_id:
            queryset = queryset.filter(department_id=department_id)
                
        
        return queryset


    def perform_create(self,serializer):
        user = self.request.user
        serializer.save(company= user.company)
        
        
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        print("🔥 BACKEND RESPONSE DATA:")
        print(serializer.data)

        return Response(serializer.data)     
        




class DepartmentViewSet(viewsets.ModelViewSet):
    serializer_class = DepartmentSerializer
    permission_class = [IsAuthenticated, IsAdminOrHR]

    def get_queryset(self):
        # We filter first, then count the related positions
        # Using 'position' based on your previous error log
        return Department.objects.filter(
            company=self.request.user.company
        ).annotate(
            total_positions=Count('positions') 
        )

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

        


class EmployeeViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated, IsAdminOrHR]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    # 🔥 FILTERS
    filterset_fields = ["department", "position", "status"]

    # 🔍 SEARCH
    search_fields = ["first_name", "last_name", "email"]

    # 🔄 ORDERING
    ordering_fields = ["created_at", "first_name"]
    
    def get_queryset(self):
        user = self.request.user
        print("user.company", user.company)

        if user.is_superuser or getattr(user, "role", "") == "super_user":
            return Employee.objects.all()

        if not user.company:
            return Employee.objects.none()

        return Employee.objects.filter(company=user.company)

    def perform_create(self, serializer):
        
        user = self.request.user
        company = user.company
        
        check_employee_limit(company)
        
        
        if not user.company and not user.is_superuser:
            raise PermissionDenied("No company assigned")

        serializer.save(company=user.company)
        
        
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        if not serializer.is_valid():
            print("Validation Errors:", serializer.errors) # This will tell you EXACTLY what's wrong
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        self.perform_update(serializer)
        return Response(serializer.data)
    
            
    @action(detail=True, methods=["post"], url_path="activate")
    def activate(self, request, pk=None):
        try:
            employee = self.get_object()
            if employee.status == "active":
                return Response({"message": "Employee is already active"}, status=status.HTTP_200_OK)
            
            employee.status = "active"
            employee.save()
    
            return Response(
                {"message": "Employee activated successfully"},
                status=status.HTTP_200_OK
            )
        except Exception as e:

            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    
    @action(detail=True, methods=["post"], url_path="deactivate")
    def deactivate(self, request, pk=None):
        try:
            employee = self.get_object()
            if employee.status != "active":
                return Response({"message": "Employee is already inactive"}, status=status.HTTP_200_OK)
            
            employee.status = "deactivated"   # or "inactive" if you prefer
            employee.save()
    
            return Response(
                {"message": "Employee deactivated successfully"},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            print("error", str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)    
        """"@action(detail=True, methods=["patch"], url_path="activate")
    def activate(self, request, pk=None):
        try:
            employee = self.get_object()  # 🔥 best practice
            print(employee.status)
            employee.status = "active"
            print(employee.status)
            employee.save()
    
            return Response(
                {"message": "Employee activated successfully"},
                status=status.HTTP_200_OK
            )
    
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )   
     
        
    @action(detail=True, methods=["patch"], url_path="deactivate")
    def deactivate(self, request, pk=None):
        print(request.data)
        try:
            employee = self.get_object()  # 🔥 best practice
            print(employee.status)
            employee.status = "deactivated"
            print(employee.status)
            employee.save()
    
            return Response(
                {"message": "Employee deactivated successfully"},
                status=status.HTTP_200_OK
            )
    
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        """
    @action(detail=False, methods=["get"], url_path="resolve-account")
    def resolve_account(self, request):
        bank_code = request.query_params.get("bank_code")
        account_number = request.query_params.get("account_number")
    
        if not bank_code or not account_number:
            return Response(
                {"detail": "bank_code and account_number are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
        try:
            url = "https://api.paystack.co/bank/resolve"
    
            headers = {
                "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"
            }
    
            params = {
                "account_number": account_number,
                "bank_code": bank_code
            }
    
            r = requests.get(url, headers=headers, params=params, timeout=10)
    
            # 🔥 DO NOT use raise_for_status
            data = r.json()
            print("PAYSTACK RESPONSE:", data)
    
            if r.status_code != 200:
                return Response(
                    {"detail": data.get("message", "Paystack error")},
                    status=status.HTTP_400_BAD_REQUEST
                )
    
            if not data.get("status"):
                return Response(
                    {"detail": data.get("message")},
                    status=status.HTTP_400_BAD_REQUEST
                )
    
            return Response({
                "account_name": data["data"]["account_name"]
            })
    
        except requests.Timeout:
            return Response(
                {"detail": "Request timeout from Paystack"},
                status=status.HTTP_504_GATEWAY_TIMEOUT
            )
    
        except Exception as e:
            print("ERROR:", str(e))
            return Response(
                {"detail": "Something went wrong"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )







from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser,JSONParser

from .serializers import BulkEmployeeUploadSerializer


class BulkEmployeeCreateView(APIView):
    parser_classes = (MultiPartParser, FormParser,JSONParser)
    def post(self, request, *args, **kwargs):
        print("=== BULK UPLOAD REQUEST RECEIVED ===")
        print("Files:", request.FILES)
        print("Data:", request.data)
    
        serializer = BulkEmployeeUploadSerializer(
            data=request.data,
            context={'request': request}
        )
    
        if serializer.is_valid():
            print("Serializer is valid")
            try:
                result = serializer.save()
                print("Bulk upload successful:", result)
                return Response(result, status=201)
            except Exception as e:
                print("🔥 ERROR DURING SAVE:", str(e))
                return Response({"error": str(e)}, status=400)
        else:
            print("Serializer errors:", serializer.errors)
            return Response(serializer.errors, status=400)