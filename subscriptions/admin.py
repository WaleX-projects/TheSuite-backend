from django.contrib import admin
from .models import Subscription,Plan,Coupon

admin.site.register(Subscription)
admin.site.register(Plan)
admin.site.register(Coupon)