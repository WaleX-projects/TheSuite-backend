from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .services.ai_agent import run_agent
import pendo_track


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ai_chat(request):
    message = request.data.get("message")

    if not message:
        return Response({"error": "Message is required"}, status=400)

    reply = run_agent(request.user, message)

    pendo_track.track(
        "ai_chat_message_sent",
        visitor_id=str(request.user.id),
        account_id=str(request.user.company_id) if hasattr(request.user, "company_id") and request.user.company_id else "system",
        properties={
            "message_length": len(message),
            "reply_length": len(reply) if reply else 0,
            "had_error": reply is None,
            "company_id": str(request.user.company_id) if hasattr(request.user, "company_id") and request.user.company_id else "",
        },
    )

    return Response({
        "reply": reply
    })