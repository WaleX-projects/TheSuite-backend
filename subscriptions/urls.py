from django.urls import path

from .views import (
    SubscriptionDetailView,
    CreateSubscriptionView,
    UpgradeSubscriptionView,
    PublicPlanListView,
)

urlpatterns = [
    # 📦 Subscription
    path("subscription/", SubscriptionDetailView.as_view(), name="subscription-detail"),
    path("subscription/create/", CreateSubscriptionView.as_view(), name="subscription-create"),
    path("subscription/upgrade/", UpgradeSubscriptionView.as_view(), name="subscription-upgrade"),

    # 💰 Plans (pricing page)
    path("plans/", PublicPlanListView.as_view(), name="plans-list"),
]