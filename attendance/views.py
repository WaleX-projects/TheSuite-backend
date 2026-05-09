from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Attendance, Shift, EmployeeShift, Holiday
from .serializers import AttendanceSerializer, ShiftSerializer, EmployeeShiftSerializer,HolidaySerializer
from .utils import model, read_image, collection,client,is_live

from rest_framework.decorators import api_view,permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from employees.models import Employee 

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters

from datetime import date
from django.db.models import Count, Q
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from subscriptions.utils import require_feature
# Inside your method:

    # ... inside your ViewSet ..

class AttendanceViewSet(viewsets.ModelViewSet):
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter]

    search_fields = [
        "employee__first_name",
        "employee__last_name"
    ]

    filterset_fields = ["status"]

    def get_queryset(self):
        user = self.request.user
        #check of subscription has this feature
        require_feature(user.company, "attendance")
        
        today = timezone.now().date() 
        queryset = Attendance.objects.all().order_by("-date")

        # ================= ROLE BASED ACCESS =================
        if user.role in ["company_admin", "hr"]:
            queryset = queryset.filter(employee__company=user.company,date=today)
        else:
            queryset = queryset.filter(employee__user=user)

        # ================= EMPLOYEE FILTER =================
        employee_id = self.request.query_params.get("employee_id")
        if employee_id:
            employee_id = employee_id.strip("/")
            queryset = queryset.filter(employee_id=employee_id)

        # ================= DATE FILTER =================
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")

        if start_date:
            queryset = queryset.filter(date__gte=start_date)

        if end_date:
            queryset = queryset.filter(date__lte=end_date)

        return queryset
        
  
    @action(methods=["GET"], detail=False)
    def dashboard(self, request):
        user = self.request.user
        today = date.today()
        #check of subscription has this feature
        require_feature(user.company, "attendance")
        # 1. Scope: Only get data for the user's company
        company_employees = Employee.objects.filter(company=user.company)
        total_employee_count = company_employees.count()
        
        # 2. Get today's attendance records for this company
        today_attendance = Attendance.objects.filter(
            employee__company=user.company, 
            date=today
        )
        
        # 3. Calculate metrics
        present_count = today_attendance.filter(status="present").count()
        late_count = today_attendance.filter(status="late").count()
        
        # Absent = Total employees minus anyone who checked in today
        # (Assuming any status like 'present' or 'late' counts as 'not absent')
        checked_in_ids = today_attendance.values_list('employee_id', flat=True)
        absent_count = total_employee_count - len(checked_in_ids)
        
        # 4. Attendance Rate
        attendance_rate = 0
        if total_employee_count > 0:
            attendance_rate = (present_count + late_count) / total_employee_count * 100
    
        data = {
            "attendance_count_currentday": present_count + late_count,
            "total_employee_count": total_employee_count,
            "attendance_rate": round(attendance_rate, 2),
            "late_count": late_count,
            "absent_today_count": absent_count
        }
        
        return Response(data)
    
            
        
        
class ShiftViewSet(viewsets.ModelViewSet):
    serializer_class = ShiftSerializer
    permission_classes = [IsAuthenticated]
    queryset = Shift.objects.all()

class EmployeeShiftViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeShiftSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return EmployeeShift.objects.filter(employee__company=self.request.user.company)
        




import uuid
import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from employees.models import Employee
from .models import Attendance
from .utils import model, read_image, collection

logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    try:
        employee_id = request.data.get("employee_id")
       
        file = request.FILES.get("file")

        if not employee_id or not file:
            return Response({"success": False, "message": "employee_id and file required"}, status=400)

        # -------- validate employee UUID --------
        try:
            employee_uuid = uuid.UUID(str(employee_id))
        except ValueError:
            return Response({"success": False, "message": "Invalid employee_id"}, status=400)

        
        # -------- fetch employee --------
        try:
            employee = Employee.objects.get(id=employee_uuid)
        except Employee.DoesNotExist:
            return Response(
                {"success": False, "message": "Employee not found"},
                status=404
            )
        # -------- image --------
  
        try:
            img = read_image(file)
            if not is_live(img):
               return Response({"message": "Spoof detected"}, status=403)
        
            
        except Exception:
            return Response({"success": False, "message": "Invalid image"}, status=400)

        faces = model.get(img)

        if len(faces) != 1:
            return Response({"success": False, "message": "Exactly one face required"}, status=400)

        embedding = faces[0].embedding.tolist()

        # -------- duplicate check --------
        try:
            results = collection.query(
                query_embeddings=[embedding],
                n_results=1
            )

            if results.get("distances") and results["distances"][0]:
                if results["distances"][0][0] < 0.4:
                    return Response({"success": False, "message": "Face already registered"}, status=409)

        except Exception as e:
            logger.warning(f"Chroma query failed: {str(e)}")

        # -------- save --------
        collection.add(
            ids=[str(employee_uuid)],
            embeddings=[embedding],
            metadatas=[{"employee_id": str(employee_uuid)}]
        )
        employee.face_verified = True
        employee.save()
        return Response({"success": True, "message": "Face registered"}, status=201)

    except Exception as e:
        logger.exception(e)
        return Response({"success": False, "error": str(e)}, status=500)  
        
        
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status


import uuid
import logging
from django.utils.timezone import now
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from employees.models import Employee
from .models import Attendance
from .utils import model, read_image, collection,is_live

logger = logging.getLogger(__name__)

# attendance/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils.timezone import now
import uuid
import logging

logger = logging.getLogger(__name__)

@api_view(["POST"])
@permission_classes([AllowAny]) 
def recognize(request):
    try:
        file = request.FILES.get("file")
        '''
        # location data
        latitude = request.data.get("latitude")
        
        longitude = request.data.get("longitude")
        if not all([file,latitude, longitude]):
            print('error:image required')
            return Response({"success": False, "message": "Image and/or location data is not available"}, status=400)
        '''    
        # -------- Process Image & Get Embedding --------
        
        
        
        #
        try:
            img = read_image(file)
           # Anti-spoof check
            #if not is_live(img):
                
                #return Response({"message": "Spoof detected"}, status=403)
        
        # STEP 2: Face recognition (InsightFace)
        
        except Exception:
            print('error:Invalid image')
            print(Exception)
            return Response({"success": False, "message": "Invalid image"}, status=400)

        faces = model.get(img)
        if len(faces) != 1:
            print('error:')
            return Response({"success": False, "message": "Please, just one face"}, status=400)

        embedding = faces[0].embedding.tolist()

        # -------- Search in Vector DB (Chroma) --------
        try:
            results = collection.query(
                query_embeddings=[embedding],
                n_results=1
            )
        except Exception as e:
            logger.exception(e)
            return Response({"success": False, "message": "Face database error"}, status=500)

        if not results.get("ids") or not results["ids"][0]:
            return Response({"success": False, "message": "No registered faces found"}, status=200) #issues with the status

        employee_id = results["ids"][0][0]
        distance = results["distances"][0][0]

        THRESHOLD = 0.6
        if distance > THRESHOLD:
            return Response({
                "success": False,
                "message": "Face not recognized",
                "distance": round(distance, 4)
            }, status=200)

        # -------- Get Employee --------
        try:
            employee_uuid = uuid.UUID(str(employee_id))
        except ValueError:
            return Response({"success": False, "message": "Invalid employee ID"}, status=500)

        employee = Employee.objects.filter(
            id=employee_uuid, 
            status="active"
        ).first()

        if not employee:
            return Response({"success": False, "message": "Employee not found or inactive"}, status=404)

        # Get company from employee
        company = employee.company   # Assuming Employee has company = ForeignKey(Company)

        # -------- Subscription Check (Important for SaaS) --------
        """
        subscription = getattr(company, 'subscription', None)
        if not subscription or not subscription.is_active:
            return Response({
                "success": False,
                "message": "Your subscription is inactive. Please upgrade your plan."
            }, status=403)
            """

        # -------- Smart Toggle Attendance Logic --------
        today = now().date()
        current_time = now().time()

        # Use get_or_create properly
        attendance, created = Attendance.objects.get_or_create(
            employee=employee,
            date=today,
            defaults={
                      # Required when creating
                'clock_in': current_time,
                'status': Attendance.StatusChoices.PRESENT,
            }
        )

        action = ""
        if created:
            # First recognition today → Check In
            action = "check_in"
            message = "Checked in successfully"
        else:
            if not attendance.clock_out:
                # Second recognition → Check Out
                attendance.clock_out = current_time
                attendance.save()
                action = "check_out"
                message = "Checked out successfully"
            else:
                # Already completed
                action = "already_completed"
                message = "Attendance already completed for today"

        return Response({
            "success": True,
            "status": "verified",
            "action": action,
            "message": message,
            "name": employee.first_name,
            "distance": round(distance, 4),
            "clock_in": str(attendance.clock_in) if attendance.clock_in else None,
            "clock_out": str(attendance.clock_out) if attendance.clock_out else None,
        }, status=200)

    except Exception as e:
        logger.exception(e)
        print()
        return Response({
            "success": False,
            "message": "Internal server error",
            "error": str(e)
        }, status=500)


from django.db.models import Q
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from .models import Holiday
from .serializers import HolidaySerializer


class HolidayViewSet(viewsets.ModelViewSet):
    serializer_class = HolidaySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Super Admin sees all holidays
        if user.role == "super_admin":
            return Holiday.objects.all().order_by("-date")

        # Company users see global + company holidays
        return Holiday.objects.filter(
            Q(is_global=True) | Q(company=user.company)
        ).order_by("-date")

    def perform_create(self, serializer):
        user = self.request.user
        is_global = serializer.validated_data.get("is_global", False)

        # Only super admin can create global holidays
        if is_global and user.role != "super_admin":
            raise PermissionDenied(
                "Only super admin can create global holidays"
            )

        if is_global:
            serializer.save(company=None, is_global=True)
        else:
            serializer.save(company=user.company, is_global=False)

    def perform_update(self, serializer):
        instance = self.get_object()
        user = self.request.user

        # Only super admin can edit global holidays
        if instance.is_global and user.role != "super_admin":
            raise PermissionDenied(
                "You cannot edit global holidays"
            )

        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user

        # Only super admin can delete global holidays
        if instance.is_global and user.role != "super_admin":
            raise PermissionDenied(
                "You cannot delete global holidays"
            )

        instance.delete()

@api_view(["GET"])
def attendance_view(request):
    employee = Employee.objects.all().count()
    
    today_attendance = Attendance.objects.all().count()
            