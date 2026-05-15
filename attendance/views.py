import uuid
import logging
from datetime import date

# Django Imports
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.timezone import now
from django.db.models import Count, Q

# Django Filters
from django_filters.rest_framework import DjangoFilterBackend

# DRF Imports
from rest_framework import viewsets, filters, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, AllowAny

# Local App Imports (Attendance/Payroll)
from .models import Attendance, Shift, EmployeeShift, Holiday
from .serializers import AttendanceSerializer, ShiftSerializer, EmployeeShiftSerializer, HolidaySerializer
from .utils import model, read_image, collection, client, is_live, calculate_haversine_distance

# External App Imports
from employees.models import Employee
from companies.models import Company, WorkLocation
from subscriptions.utils import require_feature

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
            print(queryset)
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
    
            






logger = logging.getLogger(__name__)
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
import uuid


# =========================================================
# REGISTER FACE
# =========================================================
@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    try:
        employee_id = request.data.get("employee_id")
        file = request.FILES.get("image")
        print("requested data", request.data)
        if not employee_id or not file:
            return Response({
                "success": False,
                "status": "failed",
                "message": "employee_id and file required",
                "data": None
            }, status=400)

        # Validate UUID
        try:
            employee_uuid = uuid.UUID(str(employee_id))
        except ValueError:
            return Response({
                "success": False,
                "status": "failed",
                "message": "Invalid employee_id",
                "data": None
            }, status=400)

        # Fetch employee
        try:
            employee = Employee.objects.get(id=employee_uuid)
        except Employee.DoesNotExist:
            return Response({
                "success": False,
                "status": "failed",
                "message": "Employee not found",
                "data": None
            }, status=404)

        # Process image
        try:
            img = read_image(file)

            # if not is_live(img):
            #     return Response({
            #         "success": False,
            #         "status": "failed",
            #         "message": "Spoof detected",
            #         "data": None
            #     }, status=403)

        except Exception:
            return Response({
                "success": False,
                "status": "failed",
                "message": "Invalid image",
                "data": None
            }, status=400)

        faces = model.get(img)

        if len(faces) != 1:
            return Response({
                "success": False,
                "status": "failed",
                "message": "Exactly one face required",
                "data": None
            }, status=400)

        embedding = faces[0].embedding.tolist()

        # Duplicate check
        try:
            results = collection.query(
                query_embeddings=[embedding],
                n_results=1
            )

            if results.get("distances") and results["distances"][0]:
                if results["distances"][0][0] < 0.4:
                    return Response({
                        "success": False,
                        "status": "failed",
                        "message": "Face already registered",
                        "data": None
                    }, status=409)

        except Exception as e:
            logger.warning(f"Chroma query failed: {str(e)}")

        # Save face
        collection.add(
            ids=[str(employee_uuid)],
            embeddings=[embedding],
            metadatas=[{"employee_id": str(employee_uuid)}]
        )

        employee.face_verified = True
        employee.save()

        return Response({
            "success": True,
            "status": "success",
            "message": "Face registered",
            "data": {
                "employee_id": str(employee_uuid)
            }
        }, status=201)

    except Exception as e:
        logger.exception(e)

        return Response({
            "success": False,
            "status": "failed",
            "message": "Internal server error",
            "data": {
                "error": str(e)
            }
        }, status=500)


# =========================================================
# LOCATION VERIFICATION
# =========================================================
class VerifyLocationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):

        company_id = request.data.get("company_id")
        user_lat = request.data.get("latitude")
        user_lon = request.data.get("longitude")

        if not all([company_id, user_lat, user_lon]):
            return Response({
                "success": False,
                "status": "failed",
                "message": "Missing required fields",
                "data": None
            }, status=status.HTTP_400_BAD_REQUEST)

        # Fetch company
        company = get_object_or_404(Company, company_id=company_id)

        try:
            location = company.work_location
            check_if_enable = company.attendance_settings

        except WorkLocation.DoesNotExist:
            return Response({
                "success": False,
                "status": "failed",
                "message": "Work location not configured for this company",
                "data": None
            }, status=status.HTTP_404_NOT_FOUND)

        # Geofencing disabled
        if not check_if_enable.geo_fencing_enabled:
            return Response({
                "success": True,
                "status": "success",
                "message": "Location verification disabled",
                "data": None
            }, status=status.HTTP_200_OK)

        # Calculate distance
        distance = calculate_haversine_distance(
            float(user_lat),
            float(user_lon),
            float(location.latitude),
            float(location.longitude)
        )

        # Check range
        is_within_range = distance <= location.radius_meters

        if is_within_range:
            return Response({
                "success": True,
                "status": "success",
                "message": "Inside work perimeter",
                "data": {
                    "distance": round(distance, 2)
                }
            }, status=status.HTTP_200_OK)

        return Response({
            "success": False,
            "status": "failed",
            "message": "Outside work perimeter",
            "data": {
                "distance": round(distance, 2),
                "radius_limit": location.radius_meters
            }
        }, status=status.HTTP_403_FORBIDDEN)


# =========================================================
# FACE RECOGNITION + ATTENDANCE
# =========================================================
@api_view(["POST"])
@permission_classes([AllowAny])
def recognize(request):

    try:
        file = request.FILES.get("image")

        if not file:
            return Response({
                "success": False,
                "status": "failed",
                "message": "Image is required",
                "data": None
            }, status=400)

        # Process image
        try:
            img = read_image(file)

            # if not is_live(img):
            #     return Response({
            #         "success": False,
            #         "status": "failed",
            #         "message": "Spoof detected",
            #         "data": None
            #     }, status=403)

        except Exception:
            return Response({
                "success": False,
                "status": "failed",
                "message": "Invalid image",
                "data": None
            }, status=400)

        faces = model.get(img)

        if len(faces) != 1:
            return Response({
                "success": False,
                "status": "failed",
                "message": "Please, just one face",
                "data": None
            }, status=400)

        embedding = faces[0].embedding.tolist()

        # Search face DB
        try:
            results = collection.query(
                query_embeddings=[embedding],
                n_results=1
            )

        except Exception as e:
            logger.exception(e)

            return Response({
                "success": False,
                "status": "failed",
                "message": "Face database error",
                "data": {
                    "error": str(e)
                }
            }, status=500)

        # No face found
        if not results.get("ids") or not results["ids"][0]:
            return Response({
                "success": False,
                "status": "failed",
                "message": "No registered faces found",
                "data": None
            }, status=404)

        employee_id = results["ids"][0][0]
        distance = results["distances"][0][0]

        THRESHOLD = 0.6

        # Face mismatch
        if distance > THRESHOLD:
            return Response({
                "success": False,
                "status": "failed",
                "message": "Face not recognized",
                "data": {
                    "distance": round(distance, 4)
                }
            }, status=401)

        # Validate employee UUID
        try:
            employee_uuid = uuid.UUID(str(employee_id))

        except ValueError:
            return Response({
                "success": False,
                "status": "failed",
                "message": "Invalid employee ID",
                "data": None
            }, status=500)

        # Fetch employee
        employee = Employee.objects.filter(
            id=employee_uuid,
            status="active"
        ).first()

        if not employee:
            return Response({
                "success": False,
                "status": "failed",
                "message": "Employee not found or inactive",
                "data": None
            }, status=404)

        company = employee.company

        # Subscription check
        """
        subscription = getattr(company, 'subscription', None)

        if not subscription or not subscription.is_active:
            return Response({
                "success": False,
                "status": "failed",
                "message": "Subscription inactive",
                "data": None
            }, status=403)
        """

        today = now().date()
        current_time = now().time()

        attendance, created = Attendance.objects.get_or_create(
            employee=employee,
            date=today,
            defaults={
                "clock_in": current_time,
                "status": Attendance.StatusChoices.PRESENT,
            }
        )

        # Attendance logic
        if created:
            success= True,
            status = "success"
            action = "check_in"
            message = "Checked in successfully"

        else:
            if not attendance.clock_out:
                attendance.clock_out = current_time
                attendance.save()
                success = True
                status = "success"
                action = "check_out"
                message = "Checked out successfully"

            else:
                success = False
                status = "failed"
                action = "already_completed"
                message = "Attendance already completed for today"

        return Response({
            "success": success,
            "status": status,
            "message": message,
            "data": {
                "action": action,
                "name": employee.first_name,
                "distance": round(distance, 4),
                "clock_in": str(attendance.clock_in) if attendance.clock_in else None,
                "clock_out": str(attendance.clock_out) if attendance.clock_out else None,
            }
        }, status=200)

    except Exception as e:
        logger.exception(e)

        return Response({
            "success": False,
            "status": "failed",
            "message": "Internal server error",
            "data": {
                "error": str(e)
            }
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



class ShiftViewSet(viewsets.ModelViewSet):
    serializer_class = ShiftSerializer
    permission_classes = [IsAuthenticated]
    queryset = Shift.objects.all()

class EmployeeShiftViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeShiftSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return EmployeeShift.objects.filter(employee__company=self.request.user.company)