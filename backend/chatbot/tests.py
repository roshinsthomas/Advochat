from django.urls import reverse
from rest_framework import status
from rest_framework.test import APISimpleTestCase

class HealthCheckAPITest(APISimpleTestCase):
    def test_health_endpoint_returns_ok(self):
        url = reverse("chatbot:health")
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {"status":"OK"})