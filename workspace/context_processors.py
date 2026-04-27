# workspace/context_processors.py
from .models import ChatMessage

def unread_notifications(request):
    """
    Globally injects the unread message count into EVERY template in the project.
    """
    if request.user.is_authenticated:
        try:
            unread_count = ChatMessage.objects.filter(
                receiver=request.user, 
                is_read=False
            ).count()
            return {'unread_msg_count': unread_count}
        except Exception:
            return {'unread_msg_count': 0}
    return {'unread_msg_count': 0}