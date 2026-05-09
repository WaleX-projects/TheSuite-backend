from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from ai_init.views import ai_chat
from employees.views import EmployeeViewSet,DepartmentViewSet,PositionViewSet,BulkEmployeeCreateView
from appsettings.views import CompanySettingsView


from attendance.views import  ShiftViewSet, EmployeeShiftViewSet,register, recognize,AttendanceViewSet,HolidayViewSet
from leave.views import LeaveTypeViewSet, LeaveRequestViewSet
from notifications.views import NotificationViewSet

router = DefaultRouter()

# 👥 Employees
router.register("employees", EmployeeViewSet, basename="employee")
router.register("department",DepartmentViewSet,basename="department")
router.register("position",PositionViewSet,basename="position")


# ⏱️ Attendance
router.register("attendance", AttendanceViewSet, basename="attendance")
router.register("shifts", ShiftViewSet, basename="shift")
router.register("employee-shifts", EmployeeShiftViewSet, basename="employee-shift")
router.register(r'holidays', HolidayViewSet, basename='holidays')

# 🧾 Leave

router.register(r"leave-types", LeaveTypeViewSet,basename="leave-types")
router.register(r"leave", LeaveRequestViewSet,basename="leaves")



# 💳 Subscriptions
#router.register("plans", PlanViewSet, basename="plan")
#router.register("subscriptions", SubscriptionViewSet, basename="subscription")

# 🔔 Notifications
router.register("notifications", NotificationViewSet, basename="notification")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    
    path("api/accounts/", include("accounts.urls")),
    path("api/companies/", include("companies.urls")),
    path('api/register/', register,name="registration"),
    path('api/recognize/', recognize,name="recognition"),
    path('api/accounts/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # 💰 Payroll
    path('api/', include('payroll.urls')),
    path('api/', include('subscriptions.urls')),
    # urls.py
    #ai_chat URL
    path('api/chat/',ai_chat,name="chat-ai"),
    #bulk onboarding of employees 
path('api/bulk/', BulkEmployeeCreateView.as_view(), name='bulk-employee-upload'),# In your main urls.py or settings/urls.py

    path('api/settings/', CompanySettingsView.as_view(), name='company-settings'),


 ]