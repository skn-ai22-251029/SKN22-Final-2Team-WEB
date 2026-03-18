from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from users.models import SocialAccount, User, UserProfile
from users.oauth import SocialUserProfile


TEST_SOCIAL_PROVIDERS = {
    "google": {
        "client_id": "google-client-id",
        "client_secret": "google-client-secret",
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://openidconnect.googleapis.com/v1/userinfo",
    },
    "naver": {
        "client_id": "naver-client-id",
        "client_secret": "naver-client-secret",
        "authorize_url": "https://nid.naver.com/oauth2.0/authorize",
        "token_url": "https://nid.naver.com/oauth2.0/token",
        "userinfo_url": "https://openapi.naver.com/v1/nid/me",
    },
    "kakao": {
        "client_id": "kakao-client-id",
        "client_secret": "kakao-client-secret",
        "authorize_url": "https://kauth.kakao.com/oauth/authorize",
        "token_url": "https://kauth.kakao.com/oauth/token",
        "userinfo_url": "https://kapi.kakao.com/v2/user/me",
    },
}


@override_settings(SOCIAL_AUTH_PROVIDERS=TEST_SOCIAL_PROVIDERS)
class SocialLoginViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("users.views.OAuthProviderClient.exchange_code")
    def test_social_login_creates_user_and_tokens(self, exchange_code_mock):
        exchange_code_mock.return_value = SocialUserProfile(
            provider="google",
            provider_user_id="google-user-1",
            email="user@example.com",
            nickname="TailTalk User",
            profile_image_url="https://example.com/avatar.png",
            extra_data={"sub": "google-user-1"},
        )

        response = self.client.post(
            "/api/auth/social/google/",
            {
                "code": "oauth-code",
                "redirect_uri": "http://localhost:3000/auth/google/callback",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["email"], "user@example.com")
        self.assertTrue(response.data["is_new_user"])
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertTrue(User.objects.filter(email="user@example.com").exists())
        self.assertTrue(
            SocialAccount.objects.filter(provider="google", provider_user_id="google-user-1").exists()
        )

    @patch("users.views.OAuthProviderClient.exchange_code")
    def test_social_login_links_existing_user_by_email(self, exchange_code_mock):
        user = User.objects.create_user(email="existing@example.com")
        UserProfile.objects.create(user=user, nickname="Existing User")

        exchange_code_mock.return_value = SocialUserProfile(
            provider="kakao",
            provider_user_id="kakao-user-1",
            email="existing@example.com",
            nickname="Updated User",
            profile_image_url="https://example.com/new-avatar.png",
            extra_data={"id": "kakao-user-1"},
        )

        response = self.client.post(
            "/api/auth/social/kakao/",
            {
                "code": "oauth-code",
                "redirect_uri": "http://localhost:3000/auth/kakao/callback",
            },
            format="json",
        )

        user.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["is_new_user"])
        self.assertEqual(user.profile.nickname, "Updated User")
        self.assertEqual(user.profile.profile_image_url, "https://example.com/new-avatar.png")
        self.assertEqual(SocialAccount.objects.count(), 1)

    def test_provider_list_returns_authorization_urls_for_configured_providers(self):
        response = self.client.get("/api/auth/providers/?redirect_uri=http://localhost:3000/auth/callback")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["providers"]), 3)
        for provider in response.data["providers"]:
            self.assertTrue(provider["configured"])
            self.assertIn("authorization_url", provider)
            self.assertIn("state", provider)
