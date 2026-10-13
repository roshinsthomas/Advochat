from django.urls import path
from .views import HealthCheckView, SearchView, ChatView
from .auth_views import ( 
                         CurrentUserView,
                         LoginView,
                         RefreshView,
                         RegisterView,)
from .history_views import (
    ConversationDetailView,
    ConversationListCreateView,
)

app_name = 'chatbot'
 
urlpatterns = [
    path("health/", HealthCheckView.as_view(), name = 'health'),
    path("search/",SearchView.as_view(), name = "search"),
    path("chat/", ChatView.as_view(), name = "chat"),
    
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/refresh/", RefreshView.as_view(), name="token-refresh"),
    path("auth/me/", CurrentUserView.as_view(), name="current-user"),
    path("conversations/",ConversationListCreateView.as_view(),name="conversation-list"),
    path("conversations/<uuid:pk>/",ConversationDetailView.as_view(),name="conversation-detail"),
]