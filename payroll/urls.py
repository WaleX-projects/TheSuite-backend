from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    PositionSalaryViewSet,
    SalaryComponentViewSet,
    PayrollRunViewSet,
    employee_payslips,
    PayslipViewSet,
    EmployeeSalaryOverrideViewSet
    
)

router = DefaultRouter()


router.register("positions", PositionSalaryViewSet, basename="postion")
router.register("salary-components", SalaryComponentViewSet,basename="components")
router.register("payrolls", PayrollRunViewSet,basename="payroll")

router.register(r'employee-salary-overrides', EmployeeSalaryOverrideViewSet, basename='employee-salary-override')

urlpatterns = [
    path("", include(router.urls)),
        path(
    "employees/payslips/", 
    PayslipViewSet.as_view({'get': 'list'}), 
    name='payslips-list'
),

    path("employees/<str:employee_id>/payslips/", employee_payslips),
]