from django.contrib import admin
from .models import Company,WorkLocation,AttendanceSettings

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'created_at')
    search_fields = ('name', 'email')
    
    
admin.site.register(WorkLocation)
admin.site.register(AttendanceSettings)   