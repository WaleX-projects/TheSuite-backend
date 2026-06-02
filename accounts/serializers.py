from rest_framework import serializers
from .models import User
from companies.models import Company
from companies.serializers import CompanySerializer

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name","role"]


class PendoVisitorSerializer(serializers.ModelSerializer):
    """Serializes user data for Pendo visitor metadata."""
    id = serializers.CharField(source='pk')
    full_name = serializers.SerializerMethodField()
    firstName = serializers.CharField(source='first_name')
    lastName = serializers.CharField(source='last_name')
    companyId = serializers.CharField(source='company_id', allow_null=True)
    isActive = serializers.BooleanField(source='is_active')
    isStaff = serializers.BooleanField(source='is_staff')
    isVerified = serializers.BooleanField(source='is_verified')
    createdAt = serializers.DateTimeField(source='created_at')

    class Meta:
        model = User
        fields = [
            'id', 'email', 'full_name', 'firstName', 'lastName',
            'role', 'phone', 'companyId', 'isActive', 'isStaff',
            'isVerified', 'createdAt',
        ]

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()


class PendoAccountSerializer(serializers.Serializer):
    """Serializes company + subscription data for Pendo account metadata."""
    id = serializers.CharField()
    companyId = serializers.CharField()
    name = serializers.CharField()
    country = serializers.CharField()
    timezone = serializers.CharField()
    createdAt = serializers.DateTimeField()
    subscriptionStatus = serializers.CharField(allow_null=True)
    subscriptionPlanName = serializers.CharField(allow_null=True)
    subscriptionPlanSlug = serializers.CharField(allow_null=True)
    subscriptionStartDate = serializers.DateTimeField(allow_null=True)
    subscriptionEndDate = serializers.DateTimeField(allow_null=True)
    subscriptionTrialEnd = serializers.DateTimeField(allow_null=True)
    planHasAttendance = serializers.BooleanField(allow_null=True)
    planHasLeave = serializers.BooleanField(allow_null=True)
    planHasPayroll = serializers.BooleanField(allow_null=True)
    planMaxEmployees = serializers.IntegerField(allow_null=True)



class RegisterSerializer(serializers.ModelSerializer):
    # pass company data while registering 
    company_data = CompanySerializer(write_only=True)
    class Meta:
        model = User
        fields = ["email", "password", "first_name", "last_name", "phone","company_data"]
        extra_kwargs = {
            "password": {"write_only": True}
        }

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value

    def create(self, validated_data):
        company_data = validated_data.pop("company_data")
        company_email = validated_data.get("email")
        company_phone = validated_data.get("phone")
        #1. create the company 
        company,created = Company.objects.get_or_create(
            name=company_data['name'],
            email=company_email,
            phone = company_phone,
            address= company_data['address'],
            country=company_data['country'],
            timezone=company_data['timezone']
        )
        #2. create an admin
        user = User.objects.create_user(**validated_data)
        #3. connect the company and admin
        user.company=company
        user.save()
        return user