import uuid

from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .services.ai_agent import run_agent

PENDO_AGENT_ID = "M23t24_UsWdjKITadNNBLbx2m1Q"
MODEL_USED = "gemini-2.5-flash"


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ai_chat(request):
    message = request.data.get("message")
    conversation_id = request.data.get("conversationId") or str(uuid.uuid4())

    if not message:
        return Response({"error": "Message is required"}, status=400)

    prompt_message_id = str(uuid.uuid4())
    response_message_id = str(uuid.uuid4())

    reply = run_agent(request.user, message)

    return Response({
        "reply": reply,
        "pendoTracking": {
            "agentId": PENDO_AGENT_ID,
            "conversationId": conversation_id,
            "promptMessageId": prompt_message_id,
            "responseMessageId": response_message_id,
            "modelUsed": MODEL_USED,
        }
    })