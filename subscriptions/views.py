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

        if not created:
            sub.plan = plan
            sub.status = "active"
            sub.trial_end = None
            sub.end_date = now + timedelta(days=plan.duration_days)
            sub.save()

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