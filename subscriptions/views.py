from django.utils import timezone
from datetime import timedelta

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, ValidationError

from .models import Subscription, Plan
from .serializers import (
    SubscriptionSerializer,
    CreateSubscriptionSerializer,
    PlanSerializer
)
import pendo_track


# ================= GET CURRENT SUBSCRIPTION =================
class SubscriptionDetailView(generics.RetrieveAPIView):
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        company = self.request.user.company
        sub = getattr(company, "subscription", None)

        if not sub:
            raise NotFound("No subscription found")

        return sub


# ================= CREATE SUBSCRIPTION =================
class CreateSubscriptionView(generics.CreateAPIView):
    serializer_class = CreateSubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        subscription = serializer.save()
        user = self.request.user
        pendo_track.track(
            "subscription_created",
            visitor_id=str(user.id),
            account_id=str(user.company_id) if hasattr(user, "company_id") and user.company_id else "system",
            properties={
                "plan_id": str(subscription.plan_id) if subscription.plan_id else "",
                "plan_name": str(subscription.plan.name) if hasattr(subscription, "plan") and subscription.plan else "",
                "company_id": str(user.company_id) if hasattr(user, "company_id") and user.company_id else "",
                "status": str(subscription.status) if hasattr(subscription, "status") else "",
                "has_trial": bool(getattr(subscription, "trial_end", None)),
            },
        )


# ================= UPGRADE SUBSCRIPTION =================
class UpgradeSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        company = request.user.company
        plan_id = request.data.get("plan_id")

        if not plan_id:
            raise ValidationError({"plan_id": "This field is required"})

        try:
            plan = Plan.objects.get(id=plan_id, is_active=True)
        except Plan.DoesNotExist:
            raise NotFound("Plan not found")

        now = timezone.now()

        # Get or create subscription
        sub, created = Subscription.objects.get_or_create(
            company=company,
            defaults={
                "plan": plan,
                "status": "trialing" if plan.trial_days > 0 else "active",
                "trial_end": now + timedelta(days=plan.trial_days) if plan.trial_days > 0 else None,
                "end_date": now + timedelta(days=plan.duration_days),
            }
        )

        previous_plan_id = None
        if not created:
            previous_plan_id = str(sub.plan_id)
            sub.plan = plan
            sub.status = "active"
            sub.trial_end = None
            sub.end_date = now + timedelta(days=plan.duration_days)
            sub.save()

        pendo_track.track(
            "subscription_upgraded",
            visitor_id=str(request.user.id),
            account_id=str(company.id) if company else "system",
            properties={
                "previous_plan_id": previous_plan_id or "",
                "new_plan_id": str(plan.id),
                "new_plan_name": plan.name if hasattr(plan, "name") else "",
                "company_id": str(company.id) if company else "",
                "is_new_subscription": created,
                "subscription_status": sub.status,
                "duration_days": plan.duration_days if hasattr(plan, "duration_days") else 0,
                "trial_days": plan.trial_days if hasattr(plan, "trial_days") else 0,
            },
        )

        return Response({
            "message": "Subscription updated successfully",
            "subscription": SubscriptionSerializer(sub).data
        })


# ================= LIST PLANS =================
class PublicPlanListView(generics.ListAPIView):
    serializer_class = PlanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Plan.objects.filter(is_active=True).order_by("base_price")