from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta

from .models import Subscription, Plan

class SubscriptionSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source="plan.name", read_only=True)
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = [
            "id",
            "company",
            "plan",
            "plan_name",
            "status",
            #"current_period_end",
            "trial_end",
            "is_active",
        ]
        read_only_fields = ["status"]

    def get_is_active(self, obj):
        return obj.is_active()
        
        
        
class CreateSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ["company", "plan"]

    def create(self, validated_data):
        plan = validated_data["plan"]
        now = timezone.now()

        # check if plan has trial logic
        if hasattr(plan, "trial_days") and plan.trial_days > 0:
            subscription = Subscription.objects.create(
                **validated_data,
                status="trialing",
                trial_end=now + timedelta(days=plan.trial_days),
                current_period_end=now + timedelta(days=plan.trial_days),
            )
        else:
            subscription = Subscription.objects.create(
                **validated_data,
                status="active",
                current_period_end=now + timedelta(days=plan.duration_days),
            )

        return subscription   
        

class PlanSerializer(serializers.ModelSerializer):
    features = serializers.SerializerMethodField()

    class Meta:
        model = Plan
        fields = [
            "id",
            "name",
            "slug",
            "base_price",
            "price_per_employee",
            "max_employees",
            "description",
            "is_popular",
            "features",
        ]

    def get_features(self, obj):
        return {
            "attendance": obj.has_attendance,
            "leave": obj.has_leave,
            "payroll": obj.has_payroll,
        }       