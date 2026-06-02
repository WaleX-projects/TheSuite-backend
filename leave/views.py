# views.py

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from rest_framework.decorators import api_view

from .models import (
    LeaveType,
    LeaveBalance,
    LeaveRequest,
    LeaveApprovalLog,
    LeavePolicy
)

from .serializers import (
    LeaveTypeSerializer,
    LeaveBalanceSerializer,
    LeaveRequestSerializer,
    LeaveApprovalLogSerializer,
    LeavePolicySerializer
)
import pendo_track


# ==========================================
# LEAVE TYPE
# ==========================================
class LeaveTypeViewSet(viewsets.ModelViewSet):
    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer


# ==========================================
# LEAVE BALANCE
# ==========================================
class LeaveBalanceViewSet(viewsets.ModelViewSet):
    queryset = LeaveBalance.objects.all()
    serializer_class = LeaveBalanceSerializer


# ==========================================
# LEAVE REQUEST
# ==========================================
class LeaveRequestViewSet(viewsets.ModelViewSet):
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer

    def perform_create(self, serializer):
        leave = serializer.save()
        user = self.request.user
        employee = getattr(leave, "employee", None)
        duration_days = None
        if hasattr(leave, "start_date") and hasattr(leave, "end_date") and leave.start_date and leave.end_date:
            duration_days = (leave.end_date - leave.start_date).days + 1
        pendo_track.track(
            "leave_request_submitted",
            visitor_id=str(user.id),
            account_id=str(user.company_id) if hasattr(user, "company_id") and user.company_id else "system",
            properties={
                "leave_type": str(leave.leave_type) if hasattr(leave, "leave_type") else "",
                "start_date": str(leave.start_date) if hasattr(leave, "start_date") else "",
                "end_date": str(leave.end_date) if hasattr(leave, "end_date") else "",
                "duration_days": duration_days or 0,
                "employee_id": str(employee.id) if employee else "",
                "company_id": str(user.company_id) if hasattr(user, "company_id") and user.company_id else "",
            },
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        leave = self.get_object()

        leave.status = "approved"
        leave.approved_by = request.user
        leave.approved_at = timezone.now()
        leave.save()

        LeaveApprovalLog.objects.create(
            leave_request=leave,
            action="approved",
            action_by=request.user
        )

        employee = getattr(leave, "employee", None)
        duration_days = None
        if hasattr(leave, "start_date") and hasattr(leave, "end_date") and leave.start_date and leave.end_date:
            duration_days = (leave.end_date - leave.start_date).days + 1
        pendo_track.track(
            "leave_request_approved",
            visitor_id=str(request.user.id),
            account_id=str(request.user.company_id) if hasattr(request.user, "company_id") and request.user.company_id else "system",
            properties={
                "leave_request_id": str(leave.id),
                "leave_type": str(leave.leave_type) if hasattr(leave, "leave_type") else "",
                "approved_by": str(request.user.id),
                "employee_id": str(employee.id) if employee else "",
                "duration_days": duration_days or 0,
            },
        )

        return Response({"message": "Leave approved"})


    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        leave = self.get_object()

        leave.status = "rejected"
        leave.rejection_reason = request.data.get("reason", "")
        leave.save()

        LeaveApprovalLog.objects.create(
            leave_request=leave,
            action="rejected",
            action_by=request.user,
            note=leave.rejection_reason
        )

        employee = getattr(leave, "employee", None)
        pendo_track.track(
            "leave_request_rejected",
            visitor_id=str(request.user.id),
            account_id=str(request.user.company_id) if hasattr(request.user, "company_id") and request.user.company_id else "system",
            properties={
                "leave_request_id": str(leave.id),
                "leave_type": str(leave.leave_type) if hasattr(leave, "leave_type") else "",
                "rejected_by": str(request.user.id),
                "employee_id": str(employee.id) if employee else "",
                "has_rejection_reason": bool(leave.rejection_reason),
            },
        )

        return Response({"message": "Leave rejected"})


# ==========================================
# APPROVAL LOG
# ==========================================
class LeaveApprovalLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LeaveApprovalLog.objects.all()
    serializer_class = LeaveApprovalLogSerializer


# ==========================================
# POLICY
# ==========================================
class LeavePolicyViewSet(viewsets.ModelViewSet):
    queryset = LeavePolicy.objects.all()
    serializer_class = LeavePolicySerializer

    def perform_create(self, serializer):
        policy = serializer.save()
        user = self.request.user
        pendo_track.track(
            "leave_policy_created",
            visitor_id=str(user.id),
            account_id=str(user.company_id) if hasattr(user, "company_id") and user.company_id else "system",
            properties={
                "policy_name": str(policy) if policy else "",
                "company_id": str(user.company_id) if hasattr(user, "company_id") and user.company_id else "",
            },
        )
    
    
    
@api_view
def get_employee(self,request):
    employee_id = request.data.emplyee_id
    try:
        employee = Employee.objects.get(employee_id = employee_id )
    except Exception as e:
        return Response({"status":"failed","data":str(e)})
    
    return Response({"status":"successful","data":employee.name})
    