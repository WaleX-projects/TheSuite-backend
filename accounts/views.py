import logging
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

from .serializers import RegisterSerializer, UserSerializer, PendoVisitorSerializer, PendoAccountSerializer
from .utils import generate_verification_token, confirm_verification_token

User = get_user_model()
logger = logging.getLogger(__name__)


def _build_pendo_metadata(user):
    """Build Pendo visitor and account metadata for the given user."""
    visitor_data = PendoVisitorSerializer(user).data

    account_data = None
    if user.company:
        company = user.company
        sub = getattr(company, 'subscription', None)
        plan = sub.plan if sub else None
        account_data = PendoAccountSerializer({
            'id': str(company.pk),
            'companyId': company.company_id,
            'name': company.name,
            'country': company.country,
            'timezone': company.timezone,
            'createdAt': company.created_at,
            'subscriptionStatus': sub.status if sub else None,
            'subscriptionPlanName': plan.name if plan else None,
            'subscriptionPlanSlug': plan.slug if plan else None,
            'subscriptionStartDate': sub.start_date if sub else None,
            'subscriptionEndDate': sub.end_date if sub else None,
            'subscriptionTrialEnd': sub.trial_end if sub else None,
            'planHasAttendance': plan.has_attendance if plan else None,
            'planHasLeave': plan.has_leave if plan else None,
            'planHasPayroll': plan.has_payroll if plan else None,
            'planMaxEmployees': plan.max_employees if plan else None,
        }).data

    result = {'visitor': visitor_data}
    if account_data:
        result['account'] = account_data
    return result


# ============================
# REGISTER / SIGNUP change 5his for just test
# ============================
class RegisterView(APIView):
    """
    Register a new user and send email verification.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        if not serializer.is_valid():
            logger.warning("Registration failed: %s", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Create user as inactive until email is verified
            user = serializer.save(is_active=False, is_verified=False)

            # Generate verification token
            token = generate_verification_token(user.email)
            frontend_url = getattr(settings, 'FRONTEND_URL', 'https://thesuit.netlify.app')
            verify_url = f"{frontend_url}/verify-account/{token}"

            # Prepare email context
            context = {
                'user': user,
                'verify_url': verify_url,
                'frontend_url': frontend_url,
            }

            # Render HTML email template
            html_message = render_to_string('emails/welcome_verify.html', context)

            # Plain text version
            plain_message = (
                f"Welcome to TheSuite!\n\n"
                f"Hi {user.first_name or user.email},\n\n"
                f"Thank you for joining TheSuite. Please click the link below to verify your email:\n\n"
                f"{verify_url}\n\n"
                f"This link expires in 24 hours.\n\n"
                f"Best regards,\nTheSuite Team"
            )

            send_mail(
                subject="Welcome to TheSuite – Verify Your Email",
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )

            logger.info("New user registered: %s", user.email)

            return Response(
                {
                    "message": "Account created successfully. Please check your email to verify your account."
                },
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            logger.error("Registration error: %s", str(e), exc_info=True)
            return Response(
                {"error": "Something went wrong. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================
# EMAIL VERIFICATION
# ============================
class VerifyEmailView(APIView):
    """
    Verify user email using token from email link.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, token):
        email = confirm_verification_token(token)
        if not email:
            return Response({"error": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        if user.is_verified:
            return Response({"message": "Email already verified"}, status=status.HTTP_200_OK)

        # Activate the user
        user.is_verified = True
        user.is_active = True
        user.save()

        return Response(
            {"message": "Email verified successfully. You can now login."},
            status=status.HTTP_200_OK
        )


# ============================
# LOGIN (JWT)
# ============================
class LoginView(APIView):
    """
    Login user and return JWT tokens.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response({"error": "Email and password are required"}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email=email).first()

        if user is None or not user.check_password(password):
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_verified:
            return Response({"error": "Please verify your email before logging in"}, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user)

        return Response({
            "message": f"Login successful. Welcome {user.first_name or user.email}!",
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "pendo": _build_pendo_metadata(user),
        }, status=status.HTTP_200_OK)


# ============================
# PROFILE
# ============================
class ProfileView(APIView):
    """
    Get current user's profile.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ============================
# PASSWORD RESET REQUEST
# ============================
class PasswordResetRequestView(APIView):
    """
    Send password reset email.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email=email).first()
        if not user:
            # Don't reveal if email exists (security best practice)
            return Response({"message": "If an account with this email exists, a reset link has been sent."}, 
                          status=status.HTTP_200_OK)

        token = generate_verification_token(user.email)
        reset_url = f"{getattr(settings, 'FRONTEND_URL', 'https://thesuit.netlify.app')}/reset-password/{token}"

        context = {
            'user': user,
            'reset_url': reset_url,
        }

        html_message = render_to_string('emails/password_reset.html', context)

        plain_message = (
            f"Password Reset Request\n\n"
            f"Hi {user.first_name or user.email},\n\n"
            f"Click the link below to reset your password:\n{reset_url}\n\n"
            f"This link expires in 24 hours.\n\n"
            f"If you didn't request this, please ignore this email."
        )

        send_mail(
            subject="Reset Your TheSuite Password",
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )

        return Response({"message": "Password reset email sent"}, status=status.HTTP_200_OK)


# ============================
# PASSWORD RESET CONFIRM
# ============================
class PasswordResetView(APIView):
    """
    Reset password using token.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, token):
        email = confirm_verification_token(token)
        if not email:
            return Response({"error": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST)

        password = request.data.get("password")
        if not password:
            return Response({"error": "Password is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        user.set_password(password)
        user.save()

        return Response({"message": "Password reset successful"}, status=status.HTTP_200_OK)


# ============================
# PENDO METADATA
# ============================
class PendoMetadataView(APIView):
    """
    Return Pendo visitor and account metadata for the authenticated user.
    The frontend calls this endpoint on page load to supply data to pendo.identify().
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(_build_pendo_metadata(request.user), status=status.HTTP_200_OK)


'''from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from rest_framework_simplejwt.tokens import RefreshToken
from accounts.utils import generate_verification_token, confirm_verification_token
from accounts.serializers import UserSerializer,RegisterSerializer
#from companies.models import Company 
User = get_user_model()

# -----------------------------
# REGISTER / SIGNUP
# -----------------------------
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.core.mail import send_mail


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        print("Incoming data:", request.data)

        serializer = RegisterSerializer(data=request.data)

        if not serializer.is_valid():
            print("Serializer errors:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = serializer.save()

            frontend_url = "https://thesuit.netlify.app"
            #generate token base on user's id and email
            token = generate_verification_token(user.email)
            
            verify_url = f"{frontend_url}/verify-account/{token}"
            send_mail(
                "Verify Your Email",
                f"Click this link to verify your account: {verify_url}",
                "noreply@Thesuite.com",
                [user.email],
            )

            return Response(
                {"message": "User created. Check your email to verify."},
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            print("ERROR:", str(e))
            return Response(
                {"error": "Something went wrong", "details": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
# -----------------------------
# EMAIL VERIFICATION
# -----------------------------
class VerifyEmailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, token):
        email = confirm_verification_token(token)
        if not email:
            return Response({"error": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.get(email=email)
        if user.is_verified:
            return Response({"message": "Email already verified"}, status=status.HTTP_200_OK)

        user.is_verified = True
        user.save()
        return Response({"message": "Email verified successfully"}, status=status.HTTP_200_OK)


# -----------------------------
# LOGIN (JWT)
# -----------------------------
class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        user = User.objects.filter(email=email).first()
        if user is None or not user.check_password(password):
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_verified:
            return Response({"error": "Email not verified"}, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user)
        return Response({
            "message":f"login successfully, welcome {user.first_name}",
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }, status=status.HTTP_200_OK)


# -----------------------------
# PROFILE VIEW
# -----------------------------
class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


# -----------------------------
# PASSWORD RESET REQUEST
# -----------------------------
class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")
        user = User.objects.filter(email=email).first()
        if not user:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        token = generate_verification_token(user.email)
        reset_path = f"/api/accounts/reset-password/{token}/"
        reset_url = request.build_absolute_uri(reset_path)

        send_mail(
    "Password Reset",
    f"Click this link to reset your password: {reset_url}",
    "noreply@hrsaas.com",
    [user.email]
        )

        return Response({"message": "Password reset email sent"}, status=status.HTTP_200_OK)


# -----------------------------
# PASSWORD RESET
# -----------------------------
class PasswordResetView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, token):
        email = confirm_verification_token(token)
        if not email:
            return Response({"error": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST)

        password = request.data.get("password")
        user = User.objects.get(email=email)
        user.set_password(password)
        user.save()

        return Response({"message": "Password reset successful"}, status=status.HTTP_200_OK)
        
        
'''        
