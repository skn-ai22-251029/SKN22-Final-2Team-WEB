from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from products.models import Product
from users.models import SocialAccount, User, UserProfile
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
class SocialLoginPageViewTests(TestCase):
    @patch("users.page_views.build_authorization_url")
    def test_social_login_start_redirects_to_provider(self, build_authorization_url_mock):
        build_authorization_url_mock.return_value = "https://nid.naver.com/oauth2.0/authorize?state=test"

        response = self.client.get("/auth/naver/start/?remember=on")

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

        response = self.client.get("/auth/kakao/callback/?code=test-code&state=test-state")

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


class UserProfileApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="profile@example.com", password="Password123!")
        UserProfile.objects.create(user=self.user, nickname="Profile User")
        self.client.force_authenticate(self.user)

    def test_get_me_returns_profile(self):
        response = self.client.get("/api/users/me/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["email"], "profile@example.com")
        self.assertEqual(response.data["user"]["nickname"], "Profile User")

    def test_patch_me_updates_profile_fields(self):
        response = self.client.patch(
            "/api/users/me/",
            {
                "nickname": "Updated User",
                "phone": "01012341234",
                "marketing_consent": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.profile.nickname, "Updated User")
        self.assertEqual(self.user.profile.phone, "01012341234")
        self.assertTrue(self.user.profile.marketing_consent)

class UserPreferenceApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="preferences@example.com", password="Password123!")
        UserProfile.objects.create(user=self.user, nickname="Preference User")
        self.client.force_authenticate(self.user)

    def test_get_preferences_returns_default_theme(self):
        response = self.client.get("/api/users/me/preferences/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["preferences"]["theme"], "system")

    def test_patch_preferences_updates_theme(self):
        response = self.client.patch(
            "/api/users/me/preferences/",
            {"theme": "dark"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["preferences"]["theme"], "dark")


class UserUsedProductApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="used-products@example.com", password="Password123!")
        UserProfile.objects.create(user=self.user, nickname="Used Product User")
        self.client.force_authenticate(self.user)
        self.product = Product.objects.create(
            goods_id="GI0001",
            goods_name="테스트 상품",
            brand_name="테스트 브랜드",
            price=10000,
            discount_price=9000,
            thumbnail_url="https://example.com/thumb.png",
            product_url="https://example.com/product",
            crawled_at=timezone.now(),
        )

    def test_post_used_products_creates_relation(self):
        response = self.client.post(
            "/api/users/me/used-products/",
            {"product_id": self.product.goods_id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["used_product"]["product_id"], self.product.goods_id)
        self.assertTrue(self.user.used_products.filter(product=self.product).exists())

    def test_delete_used_products_removes_relation(self):
        self.client.post(
            "/api/users/me/used-products/",
            {"product_id": self.product.goods_id},
            format="json",
        )

        response = self.client.delete(
            "/api/users/me/used-products/",
            {"product_id": self.product.goods_id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(self.user.used_products.filter(product=self.product).exists())
