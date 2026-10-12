from django.urls import path
from .views import HealthCheckView, SearchView, ChatView

app_name = 'chatbot'
 
urlpatterns = [
    path("health/", HealthCheckView.as_view(), name = 'health'),
    path("search/",SearchView.as_view(), name = "search"),
    path("chat/", ChatView.as_view(), name = "chat"),
]