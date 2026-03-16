from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        return Response({"message": "TODO"})
