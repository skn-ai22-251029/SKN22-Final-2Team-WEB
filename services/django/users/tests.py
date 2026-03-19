from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from users.models import SocialAccount, User, UserProfile
from users.oauth import SocialUserProfile
from users.social_auth import (
    SOCIAL_AUTH_ACCESS_SESSION_KEY,
    SOCIAL_AUTH_REFRESH_SESSION_KEY,
    SocialLoginResult,
)


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

    @patch("users.views.build_authorization_url")
    def test_social_login_get_returns_authorization_url(self, build_authorization_url_mock):
        build_authorization_url_mock.return_value = "https://accounts.google.com/o/oauth2/auth?state=test"

        response = self.client.get("/api/auth/social/google/?remember=on")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["provider"], "google")
        self.assertIn("authorization_url", response.data)
        self.assertIn("callback_url", response.data)

    @patch("users.views.complete_social_login")
    def test_social_login_callback_returns_tokens_and_logs_in_session(self, complete_social_login_mock):
        user = User.objects.create_user(email="callback@example.com")
        UserProfile.objects.create(user=user, nickname="Callback User")
        complete_social_login_mock.return_value = SocialLoginResult(
            user=user,
            backend_path="social_core.backends.google.GoogleOAuth2",
            provider="google",
            is_new_user=False,
        )

        session = self.client.session
        session["tailtalk_social_oauth_remember"] = True
        session.save()

        response = self.client.get("/api/auth/social/google/callback/?code=test-code&state=test-state")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["email"], "callback@example.com")

        session = self.client.session
        self.assertIn(SOCIAL_AUTH_ACCESS_SESSION_KEY, session)
        self.assertIn(SOCIAL_AUTH_REFRESH_SESSION_KEY, session)


@override_settings(SOCIAL_AUTH_PROVIDERS=TEST_SOCIAL_PROVIDERS)
class SocialLoginPageViewTests(TestCase):
    @patch("users.page_views.build_authorization_url")
    def test_social_login_start_redirects_to_provider(self, build_authorization_url_mock):
        build_authorization_url_mock.return_value = "https://nid.naver.com/oauth2.0/authorize?state=test"

        response = self.client.get("/auth/social/naver/?remember=on")

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response["Location"], "https://nid.naver.com/oauth2.0/authorize?state=test")

    @patch("users.page_views.complete_social_login")
    def test_social_login_callback_redirects_to_profile_and_stores_jwt(self, complete_social_login_mock):
        user = User.objects.create_user(email="page@example.com")
        UserProfile.objects.create(user=user, nickname="Page User")
        complete_social_login_mock.return_value = SocialLoginResult(
            user=user,
            backend_path="social_core.backends.kakao.KakaoOAuth2",
            provider="kakao",
            is_new_user=True,
        )

        session = self.client.session
        session["tailtalk_social_oauth_remember"] = False
        session.save()

        response = self.client.get("/auth/social/kakao/callback/?code=test-code&state=test-state")

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response["Location"], f"{reverse('profile')}?setup=1")

        session = self.client.session
        self.assertIn(SOCIAL_AUTH_ACCESS_SESSION_KEY, session)
        self.assertIn(SOCIAL_AUTH_REFRESH_SESSION_KEY, session)


@override_settings(SOCIAL_AUTH_PROVIDERS=TEST_SOCIAL_PROVIDERS)
class AuthApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="auth@example.com", password="Password123!")
        UserProfile.objects.create(user=self.user, nickname="Auth User")

    def test_login_returns_access_and_refresh_tokens(self):
        response = self.client.post(
            "/api/auth/login/",
            {"email": "auth@example.com", "password": "Password123!"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["email"], "auth@example.com")

    def test_logout_blacklists_refresh_token(self):
        login_response = self.client.post(
            "/api/auth/login/",
            {"email": "auth@example.com", "password": "Password123!"},
            format="json",
        )
        access = login_response.data["access"]
        refresh = login_response.data["refresh"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        logout_response = self.client.post("/api/auth/logout/", {"refresh": refresh}, format="json")
        self.assertEqual(logout_response.status_code, status.HTTP_204_NO_CONTENT)

        refresh_response = self.client.post("/api/auth/token/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_withdraw_deletes_user(self):
        login_response = self.client.post(
            "/api/auth/login/",
            {"email": "auth@example.com", "password": "Password123!"},
            format="json",
        )
        access = login_response.data["access"]
        refresh = login_response.data["refresh"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        response = self.client.delete("/api/auth/withdraw/", {"refresh": refresh}, format="json")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(email="auth@example.com").exists())
