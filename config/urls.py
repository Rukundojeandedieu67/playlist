from django.urls import include, path
from django.views.generic import RedirectView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({"status": "ok"})


urlpatterns = [
    path("", RedirectView.as_view(url="/api/playlists/", permanent=False)),
    path("api/health/", HealthView.as_view(), name="health"),
    path("api/", include("playlists.urls")),
]
