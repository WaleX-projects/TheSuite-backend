from rest_framework.exceptions import PermissionDenied, NotFound
from django.utils import timezone


# ================= GET ACTIVE SUBSCRIPTION =================
def get_active_subscription(company):
    sub = getattr(company, "subscription", None)

    if not sub:
        raise NotFound({
            "code": "NO_SUBSCRIPTION",
            "message": "No subscription found"
        })

    now = timezone.now()

    # Trial
    if sub.status == "trialing":
        if sub.trial_end and now <= sub.trial_end:
            return sub

        raise PermissionDenied({
            "code": "TRIAL_EXPIRED",
            "message": "Your trial has expired"
        })

    # Active subscription
    if sub.status == "active":
        if sub.end_date and now <= sub.end_date:
            return sub

        raise PermissionDenied({
            "code": "SUBSCRIPTION_EXPIRED",
            "message": "Your subscription has expired"
        })

    raise PermissionDenied({
        "code": "SUBSCRIPTION_INACTIVE",
        "message": "Subscription is not active"
    })


# ================= FEATURE ACCESS =================
def require_feature(company, feature_name: str):
    sub = get_active_subscription(company)
    plan = sub.plan

    if not getattr(plan, f"has_{feature_name}", False):
        raise PermissionDenied({
            "code": "FEATURE_NOT_AVAILABLE",
            "message": f"{feature_name.capitalize()} is not available on your plan"
        })

    return True


# ================= EMPLOYEE LIMIT =================
def check_employee_limit(company):
    sub = get_active_subscription(company)
    plan = sub.plan

    if plan.max_employees is not None:
        current_count = company.employee_set.count()

        if current_count >= plan.max_employees:
            raise PermissionDenied({
                "code": "EMPLOYEE_LIMIT",
                "message": "Employee limit reached. Please upgrade your plan."
            })

    return True