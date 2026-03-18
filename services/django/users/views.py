from django.conf import settings
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from .models import SocialAccount, User, UserProfile
from .oauth import OAuthProviderClient, SocialAuthError


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        return Response({"message": "TODO"})


class SocialProviderListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        redirect_uri = request.query_params.get("redirect_uri")
        response_data = []

        for provider in settings.SOCIAL_AUTH_PROVIDERS:
            provider_data = {
                "provider": provider,
                "configured": self._is_provider_configured(provider),
            }
            if redirect_uri and provider_data["configured"]:
                client = OAuthProviderClient(provider)
                provider_data.update(client.build_authorization_url(redirect_uri=redirect_uri))
            response_data.append(provider_data)

        return Response({"providers": response_data})

    def _is_provider_configured(self, provider: str) -> bool:
        provider_config = settings.SOCIAL_AUTH_PROVIDERS.get(provider, {})
        return bool(provider_config.get("client_id") and provider_config.get("client_secret"))


class SocialLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, provider):
        code = request.data.get("code")
        redirect_uri = request.data.get("redirect_uri")
        state = request.data.get("state")

        if not code or not redirect_uri:
            return Response(
                {"detail": "code and redirect_uri are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            profile = OAuthProviderClient(provider).exchange_code(
                code=code,
                redirect_uri=redirect_uri,
                state=state,
            )
            user, is_new_user = self._get_or_create_user(profile)
        except SocialAuthError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "provider": provider,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "is_new_user": is_new_user,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "nickname": user.profile.nickname,
                    "profile_image_url": user.profile.profile_image_url,
                },
            }
        )

    @transaction.atomic
    def _get_or_create_user(self, profile):
        social_account = (
            SocialAccount.objects.select_related("user", "user__profile")
            .filter(provider=profile.provider, provider_user_id=profile.provider_user_id)
            .first()
        )
        if social_account:
            self._sync_profile(social_account.user, profile)
            return social_account.user, False

        user = None
        if profile.email:
            user = User.objects.filter(email=profile.email).first()

        if user is None:
            email = profile.email or self._build_fallback_email(profile.provider, profile.provider_user_id)
            user = User.objects.create_user(email=email)
            UserProfile.objects.create(
                user=user,
                nickname=profile.nickname,
                profile_image_url=profile.profile_image_url,
            )
            is_new_user = True
        else:
            UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    "nickname": profile.nickname,
                    "profile_image_url": profile.profile_image_url,
                },
            )
            is_new_user = False
            self._sync_profile(user, profile)

        SocialAccount.objects.create(
            user=user,
            provider=profile.provider,
            provider_user_id=profile.provider_user_id,
            email=profile.email or user.email,
            extra_data=profile.extra_data,
        )

        return user, is_new_user

    def _sync_profile(self, user, profile):
        profile_defaults = {
            "nickname": profile.nickname,
            "profile_image_url": profile.profile_image_url,
        }
        user_profile, _ = UserProfile.objects.get_or_create(user=user, defaults=profile_defaults)

        dirty_fields = []
        if profile.nickname and user_profile.nickname != profile.nickname:
            user_profile.nickname = profile.nickname
            dirty_fields.append("nickname")
        if profile.profile_image_url and user_profile.profile_image_url != profile.profile_image_url:
            user_profile.profile_image_url = profile.profile_image_url
            dirty_fields.append("profile_image_url")
        if dirty_fields:
            user_profile.save(update_fields=[*dirty_fields, "updated_at"])

    def _build_fallback_email(self, provider: str, provider_user_id: str) -> str:
        return f"{provider}_{provider_user_id}@oauth.local"
