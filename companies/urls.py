from django.urls import path
from .views import  CompanyListView, dashboard_stats,CompanySettingsView
# urls.py


from .views import AttendanceSettingsView
# urls.py


from .views import PayrollSettingsView
# urls.py

from .views import LeaveSettingsView
# urls.py

from django.urls import path
from .views import SystemSettingsView

# urls.py

from django.urls import path
from .views import WorkLocationView

urlpatterns = [
    path(
        "work-location/",
        WorkLocationView.as_view(),
        name="work-location"
    ),

    path(
        "system/settings/",
        SystemSettingsView.as_view(),
        name="system-settings"
    ),

    path(
        "leave/settings/",
        LeaveSettingsView.as_view(),
        name="leave-settings"
    ),

    path(
        "payroll/settings/",
        PayrollSettingsView.as_view(),
        name="payroll-settings"
    ),

    path(
        "attendance/settings/",
        AttendanceSettingsView.as_view(),
        name="attendance-settings"
    ),

    path("dashboard/stats/", dashboard_stats),
    path("", CompanyListView.as_view()),
    path("settings/",CompanySettingsView.as_view(),name="settings")
]