from django.contrib.auth import authenticate, logout
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken

from ..models import User, UserProfile
from ..nickname_utils import (
    build_unique_nickname,
    get_nickname_duplicate_error,
    get_nickname_policy_error,
    get_nickname_validation_error,
)
from ..services.auth_service import deactivate_user_and_purge_personal_data, issue_user_tokens
from .serializers import serialize_user


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip()
        password = request.data.get("password", "")
        nickname = request.data.get("nickname", "").strip()

        if not email or not password:
            return Response({"detail": "email and password are required."}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=email).exists():
            return Response({"detail": "이미 사용 중인 이메일입니다."}, status=status.HTTP_400_BAD_REQUEST)

        if nickname:
            nickname_error = get_nickname_validation_error(nickname)
            if nickname_error:
                return Response({"detail": nickname_error}, status=status.HTTP_400_BAD_REQUEST)
            profile_nickname = nickname
        else:
            profile_nickname = build_unique_nickname(email.split("@")[0])

        try:
            with transaction.atomic():
                user = User.objects.create_user(email=email, password=password)
                UserProfile.objects.create(user=user, nickname=profile_nickname)
        except IntegrityError:
            return Response({"detail": "이미 사용 중인 닉네임입니다."}, status=status.HTTP_400_BAD_REQUEST)

        tokens = issue_user_tokens(user)
        return Response(
            {
                **tokens,
                "user": serialize_user(user),
            },
            status=status.HTTP_201_CREATED,
        )


class AuthLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip()
        password = request.data.get("password", "")

        if not email or not password:
            return Response({"detail": "email and password are required."}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(request, username=email, password=password)
        if user is None:
            return Response({"detail": "이메일 또는 비밀번호가 올바르지 않습니다."}, status=status.HTTP_401_UNAUTHORIZED)

        tokens = issue_user_tokens(user)
        return Response(
            {
                **tokens,
                "user": serialize_user(user),
            }
        )


class AuthLogoutView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"detail": "refresh is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            return Response({"detail": "유효하지 않은 refresh token 입니다."}, status=status.HTTP_400_BAD_REQUEST)

        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AuthWithdrawView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def delete(self, request):
        refresh_token = request.data.get("refresh")
        user = request.user

        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception:
                return Response({"detail": "유효하지 않은 refresh token 입니다."}, status=status.HTTP_400_BAD_REQUEST)

        deactivate_user_and_purge_personal_data(user)

        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class NicknameAvailabilityView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [AllowAny]

    def get(self, request):
        nickname = request.query_params.get("nickname", "").strip()
        if not nickname:
            return Response({"detail": "nickname is required."}, status=status.HTTP_400_BAD_REQUEST)

        exclude_user = request.user if request.user.is_authenticated else None
        policy_error = get_nickname_policy_error(nickname)
        duplicate_error = None if policy_error else get_nickname_duplicate_error(nickname, exclude_user=exclude_user)
        detail = policy_error or duplicate_error or "사용 가능한 닉네임입니다."

        return Response(
            {
                "nickname": nickname,
                "valid": policy_error is None,
                "available": policy_error is None and duplicate_error is None,
                "detail": detail,
            }
        )
