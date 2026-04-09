from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from social_django.models import UserSocialAuth

from orders.models import Order, OrderItem, UserInteraction
from pets.models import FuturePetProfile, Pet
from products.models import Product
from users.models import SocialAccount, User, UserProfile
from users.onboarding import ONBOARDING_FORCE_PROFILE_SESSION_KEY
from users.social_auth import (
    SOCIAL_AUTH_ACCESS_SESSION_KEY,
    SOCIAL_AUTH_REFRESH_SESSION_KEY,
    SocialLoginResult,
)
from users.social_pipeline import associate_active_user_by_email


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
    def test_social_login_callback_redirects_new_user_to_profile_setup_and_stores_jwt(self, complete_social_login_mock):
        user = User.objects.create_user(email="page@example.com")
        UserProfile.objects.create(user=user, nickname="PageUser")
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
        self.assertTrue(session[ONBOARDING_FORCE_PROFILE_SESSION_KEY])

    def test_associate_active_user_by_email_ignores_inactive_user(self):
        withdrawn_user = User.objects.create_user(email="social@example.com")
        withdrawn_user.is_active = False
        withdrawn_user.save(update_fields=["is_active"])

        result = associate_active_user_by_email({"email": "social@example.com"})

        self.assertIsNone(result)


@override_settings(SOCIAL_AUTH_PROVIDERS=TEST_SOCIAL_PROVIDERS)
class AuthApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="auth@example.com", password="Password123!")
        UserProfile.objects.create(user=self.user, nickname="AuthUser")

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

    def test_withdraw_deactivates_user_and_scrubs_identity(self):
        UserSocialAuth.objects.create(user=self.user, provider="kakao", uid="oauth-uid-1")

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
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertNotEqual(self.user.email, "auth@example.com")
        self.assertFalse(self.user.has_usable_password())
        self.assertFalse(UserProfile.objects.filter(user=self.user).exists())
        self.assertFalse(UserSocialAuth.objects.filter(user=self.user).exists())

    def test_withdraw_preserves_orders(self):
        Order.objects.create(
            user=self.user,
            recipient_name="탈퇴 사용자",
            recipient_phone="01012341234",
            delivery_address="서울 강동구 올림픽로 123 | 101동 1203호",
            payment_method="카카오페이 / 일시불",
            product_total=10000,
            coupon_discount=0,
            mileage_discount=0,
            shipping_fee=0,
            total_price=10000,
        )

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
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertEqual(Order.objects.filter(user=self.user).count(), 1)

    def test_withdraw_deletes_future_pet_profile(self):
        FuturePetProfile.objects.create(
            user=self.user,
            preferred_species="dog",
            housing_type="apartment",
            experience_level="first",
            interests=["adoption"],
        )

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
        self.assertFalse(FuturePetProfile.objects.filter(user=self.user).exists())


class ProfilePageViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="page-profile@example.com", password="Password123!")
        UserProfile.objects.create(user=self.user, nickname="PageProfile")
        self.other_user = User.objects.create_user(email="other-page@example.com", password="Password123!")
        UserProfile.objects.create(user=self.other_user, nickname="TakenNick")
        self.client.force_login(self.user)

    def test_profile_post_rejects_duplicate_nickname(self):
        response = self.client.post(
            "/profile/",
            {
                "nickname": "TakenNick",
                "phone": "01012341234",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.profile.nickname, "PageProfile")

    def test_profile_post_saves_address_and_payment_method(self):
        response = self.client.post(
            "/profile/",
            {
                "nickname": "PageProfile2",
                "zipcode": "12345",
                "address_main": "서울 강동구 올림픽로 123",
                "address_detail": "101동 1203호",
                "payment_method": "카카오페이 / 일시불",
            },
        )

        self.user.refresh_from_db()
        self.assertIn(response.status_code, {status.HTTP_200_OK, status.HTTP_302_FOUND})
        self.assertEqual(self.user.profile.nickname, "PageProfile2")
        self.assertEqual(self.user.profile.recipient_name, "PageProfile2")
        self.assertEqual(self.user.profile.postal_code, "12345")
        self.assertEqual(self.user.profile.address_main, "서울 강동구 올림픽로 123")
        self.assertEqual(self.user.profile.address_detail, "101동 1203호")
        self.assertEqual(self.user.profile.address, "서울 강동구 올림픽로 123 | 101동 1203호")
        self.assertEqual(self.user.profile.payment_method, "카카오페이 / 일시불")

    def test_profile_post_requires_phone_verification_for_changed_phone(self):
        response = self.client.post(
            "/profile/",
            {
                "nickname": "PageProfile",
                "phone": "01099998888",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "연락처 인증을 완료해 주세요.")

    def test_profile_post_redirects_to_chat_when_pet_profile_is_missing_for_regular_edit(self):
        response = self.client.post(
            "/profile/",
            {
                "nickname": "PageProfile2",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response["Location"], reverse("chat"))

    def test_profile_post_redirects_to_pet_add_when_pet_profile_is_missing_in_setup_mode(self):
        session = self.client.session
        session[ONBOARDING_FORCE_PROFILE_SESSION_KEY] = True
        session.save()

        response = self.client.post(
            f"{reverse('profile')}?setup=1",
            {
                "nickname": "PageProfile2",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response["Location"], reverse("pet_add"))

    def test_profile_post_redirects_to_chat_when_future_pet_profile_exists_in_setup_mode(self):
        FuturePetProfile.objects.create(
            user=self.user,
            preferred_species="dog",
            housing_type="apartment",
            experience_level="first",
            interests=["adoption"],
        )
        session = self.client.session
        session[ONBOARDING_FORCE_PROFILE_SESSION_KEY] = True
        session.save()

        response = self.client.post(
            f"{reverse('profile')}?setup=1",
            {
                "nickname": "PageProfile2",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response["Location"], reverse("chat"))

    def test_profile_post_redirects_to_chat_when_pet_profile_exists_in_setup_mode(self):
        Pet.objects.create(
            user=self.user,
            name="코코",
            species="dog",
            breed="말티즈",
            gender="male",
            age_years=3,
            age_months=0,
            weight_kg=3.2,
            budget_range="10-20",
        )
        session = self.client.session
        session[ONBOARDING_FORCE_PROFILE_SESSION_KEY] = True
        session.save()

        response = self.client.post(
            f"{reverse('profile')}?setup=1",
            {
                "nickname": "PageProfile2",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response["Location"], reverse("chat"))


class VendorAdminPageTests(TestCase):
    def setUp(self):
        self.client = self.client_class()
        self.product = Product.objects.create(
            goods_id="GI-VENDOR-1",
            goods_name="오리젠 오리지널 독",
            brand_name="오리젠",
            price=54000,
            discount_price=49900,
            rating=4.8,
            review_count=128,
            thumbnail_url="https://example.com/orijen-thumb.png",
            product_url="https://example.com/orijen-product",
            soldout_yn=False,
            pet_type=["강아지"],
            category=["사료"],
            crawled_at=timezone.now(),
        )
        Product.objects.create(
            goods_id="GI-VENDOR-2",
            goods_name="다른 브랜드 상품",
            brand_name="로얄캐닌",
            price=46000,
            discount_price=42000,
            rating=4.6,
            review_count=98,
            thumbnail_url="https://example.com/other-thumb.png",
            product_url="https://example.com/other-product",
            soldout_yn=False,
            pet_type=["강아지"],
            category=["사료"],
            crawled_at=timezone.now(),
        )

    def test_vendor_login_page_renders(self):
        response = self.client.get(reverse("vendor-login"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "관리자 로그인")

    def test_vendor_login_post_sets_session_and_redirects_to_dashboard(self):
        response = self.client.post(
            reverse("vendor-login"),
            {"login_id": "orijen", "password": "tailtalk2026!"},
        )

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response["Location"], reverse("vendor-dashboard"))
        session = self.client.session
        self.assertEqual(session.get("tailtalk_vendor_admin_id"), "orijen")

    def test_vendor_login_post_shows_error_for_invalid_credentials(self):
        response = self.client.post(
            reverse("vendor-login"),
            {"login_id": "orijen", "password": "wrong-password"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "아이디 또는 비밀번호를 확인해 주세요")

    def test_vendor_dashboard_requires_vendor_session(self):
        response = self.client.get(reverse("vendor-dashboard"))

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response["Location"], reverse("vendor-login"))

    def test_vendor_dashboard_renders_vendor_brand_metrics(self):
        analytics_user = User.objects.create_user(email="vendor-dashboard@example.com", password="Password123!")
        today = timezone.localdate()

        pending_order = Order.objects.create(
            user=analytics_user,
            recipient_name="오리젠 고객",
            recipient_phone="01012341234",
            delivery_address="서울 강남구 테일톡로 1",
            payment_method="우리카드 1234 / 일시불",
            product_total=49900,
            total_price=49900,
            status="pending",
        )
        OrderItem.objects.create(order=pending_order, product=self.product, quantity=1, price_at_order=49900)

        completed_order = Order.objects.create(
            user=analytics_user,
            recipient_name="오리젠 고객",
            recipient_phone="01012341234",
            delivery_address="서울 강남구 테일톡로 1",
            payment_method="우리카드 1234 / 일시불",
            product_total=49900,
            total_price=49900,
            status="completed",
        )
        OrderItem.objects.create(order=completed_order, product=self.product, quantity=1, price_at_order=49900)

        cancelled_order = Order.objects.create(
            user=analytics_user,
            recipient_name="오리젠 고객",
            recipient_phone="01012341234",
            delivery_address="서울 강남구 테일톡로 1",
            payment_method="우리카드 1234 / 일시불",
            product_total=49900,
            total_price=49900,
            status="cancelled",
        )
        OrderItem.objects.create(order=cancelled_order, product=self.product, quantity=1, price_at_order=49900)

        old_order = Order.objects.create(
            user=analytics_user,
            recipient_name="오리젠 고객",
            recipient_phone="01012341234",
            delivery_address="서울 강남구 테일톡로 1",
            payment_method="우리카드 1234 / 일시불",
            product_total=49900,
            total_price=49900,
            status="completed",
        )
        OrderItem.objects.create(order=old_order, product=self.product, quantity=1, price_at_order=49900)
        old_timestamp = timezone.now() - timedelta(days=3)
        Order.objects.filter(order_id=old_order.order_id).update(created_at=old_timestamp)

        other_brand_product = Product.objects.get(goods_id="GI-VENDOR-2")
        other_brand_order = Order.objects.create(
            user=analytics_user,
            recipient_name="다른 브랜드 고객",
            recipient_phone="01012341234",
            delivery_address="서울 강남구 테일톡로 2",
            payment_method="우리카드 1234 / 일시불",
            product_total=42000,
            total_price=42000,
            status="completed",
        )
        OrderItem.objects.create(order=other_brand_order, product=other_brand_product, quantity=1, price_at_order=42000)

        session = self.client.session
        session["tailtalk_vendor_admin_id"] = "orijen"
        session.save()

        response = self.client.get(reverse("vendor-dashboard"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "대시보드")
        self.assertContains(response, "처리 대기함")
        self.assertContains(response, "확인 필요 상품")
        self.assertContains(response, "상위 성과 상품")
        self.assertContains(response, reverse("vendor-product-detail", args=["GI-VENDOR-1"]))
        self.assertContains(response, "상품 등록")
        self.assertContains(response, "취소/교환/반품")
        self.assertContains(response, "고객문의 / CS")
        primary = {item["label"]: item["value"] for item in response.context["vendor_primary_kpis"]}
        queue = {item["title"]: item["count_label"] for item in response.context["vendor_queue_items"]}
        trend = {item["label"]: item["value"] for item in response.context["vendor_trend_highlights"]}
        self.assertEqual(primary["오늘 매출"], "₩99,800")
        self.assertEqual(primary["신규 주문"], "2건")
        self.assertEqual(primary["취소 / 환불 대기"], "1건")
        self.assertEqual(queue["신규 주문"], "1건")
        self.assertEqual(queue["취소 / 환불"], "1건")
        self.assertEqual(queue["리뷰 확인"], "1건")
        self.assertEqual(trend["7일 주문"], "3건")
        self.assertEqual(trend["7일 매출"], "₩149,700")

        order_trend = {point["label"]: point["value"] for point in response.context["vendor_order_trend"]}
        self.assertEqual(order_trend[today.strftime("%m/%d")], 2)

    def test_vendor_products_filters_to_vendor_brand(self):
        session = self.client.session
        session["tailtalk_vendor_admin_id"] = "orijen"
        session.save()

        response = self.client.get(reverse("vendor-products"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "오리젠 오리지널 독")
        self.assertNotContains(response, "다른 브랜드 상품")
        self.assertContains(response, reverse("vendor-product-detail", args=["GI-VENDOR-1"]))
        self.assertContains(response, "운영 상품")
        self.assertContains(response, "전체")
        self.assertContains(response, "판매중")

    def test_vendor_product_detail_requires_vendor_session(self):
        response = self.client.get(reverse("vendor-product-detail", args=["GI-VENDOR-1"]))

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response["Location"], reverse("vendor-login"))

    def test_vendor_product_detail_renders_admin_sections(self):
        session = self.client.session
        session["tailtalk_vendor_admin_id"] = "orijen"
        session.save()

        response = self.client.get(reverse("vendor-product-detail", args=["GI-VENDOR-1"]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "오리젠 오리지널 독")
        self.assertContains(response, "운영 체크 포인트")
        self.assertContains(response, reverse("vendor-product-edit", args=["GI-VENDOR-1"]))

    def test_vendor_product_detail_blocks_other_brand_product(self):
        session = self.client.session
        session["tailtalk_vendor_admin_id"] = "orijen"
        session.save()

        response = self.client.get(reverse("vendor-product-detail", args=["GI-VENDOR-2"]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_vendor_product_create_requires_vendor_session(self):
        response = self.client.get(reverse("vendor-product-create"))

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response["Location"], reverse("vendor-login"))

    def test_vendor_product_create_renders_form_sections(self):
        session = self.client.session
        session["tailtalk_vendor_admin_id"] = "orijen"
        session.save()

        response = self.client.get(reverse("vendor-product-create"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "상품 등록")
        self.assertContains(response, "직접 입력")
        self.assertContains(response, "파일 업로드")

    def test_vendor_analytics_renders_metrics(self):
        analytics_user = User.objects.create_user(email="vendor-analytics@example.com", password="Password123!")
        order = Order.objects.create(
            user=analytics_user,
            recipient_name="오리젠 고객",
            recipient_phone="01012341234",
            delivery_address="서울 강남구 테일톡로 1",
            payment_method="우리카드 1234 / 일시불",
            product_total=49900,
            total_price=49900,
            status="completed",
        )
        OrderItem.objects.create(order=order, product=self.product, quantity=1, price_at_order=49900)
        for interaction_type, count in (
            ("impression", 5),
            ("click", 2),
            ("detail_view", 1),
            ("wishlist", 1),
            ("cart", 1),
            ("checkout_start", 1),
        ):
            for _ in range(count):
                UserInteraction.objects.create(
                    user=analytics_user,
                    product=self.product,
                    interaction_type=interaction_type,
                )

        session = self.client.session
        session["tailtalk_vendor_admin_id"] = "orijen"
        session.save()

        response = self.client.get(reverse("vendor-analytics"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "통계")
        self.assertContains(response, "퍼널")
        self.assertContains(response, "우선 액션")
        self.assertContains(response, "실제 이벤트 로그 기준")
        summary = {item["label"]: item["value"] for item in response.context["vendor_analytics_summary"]}
        funnel = {item["label"]: item["value"] for item in response.context["vendor_funnel_items"]}
        implicit = {item["label"]: item["value"] for item in response.context["vendor_implicit_metrics"]}
        self.assertEqual(response.context["vendor_analytics_period_label"], "최근 30일")
        self.assertEqual(summary["최근 30일 매출"], "₩49,900")
        self.assertEqual(summary["구매 전환율"], "100.0%")
        self.assertEqual(summary["반복 구매율"], "0.0%")
        self.assertEqual(funnel["노출"], "5")
        self.assertEqual(funnel["클릭"], "2")
        self.assertEqual(funnel["상세 진입"], "1")
        self.assertEqual(funnel["장바구니"], "1")
        self.assertEqual(funnel["구매"], "1")
        self.assertEqual(implicit["체크아웃 시작 수"], "1회")
        self.assertEqual(implicit["관심상품 추가 수"], "1회")

    def test_vendor_analytics_period_filter_excludes_old_events(self):
        analytics_user = User.objects.create_user(email="vendor-analytics-period@example.com", password="Password123!")
        recent_order = Order.objects.create(
            user=analytics_user,
            recipient_name="오리젠 고객",
            recipient_phone="01012341234",
            delivery_address="서울 강남구 테일톡로 1",
            payment_method="우리카드 1234 / 일시불",
            product_total=49900,
            total_price=49900,
            status="completed",
        )
        OrderItem.objects.create(order=recent_order, product=self.product, quantity=1, price_at_order=49900)
        for interaction_type, count in (("impression", 3), ("click", 1), ("detail_view", 1)):
            for _ in range(count):
                UserInteraction.objects.create(
                    user=analytics_user,
                    product=self.product,
                    interaction_type=interaction_type,
                )

        old_order = Order.objects.create(
            user=analytics_user,
            recipient_name="오리젠 고객",
            recipient_phone="01012341234",
            delivery_address="서울 강남구 테일톡로 1",
            payment_method="우리카드 1234 / 일시불",
            product_total=49900,
            total_price=49900,
            status="completed",
        )
        OrderItem.objects.create(order=old_order, product=self.product, quantity=1, price_at_order=49900)
        old_timestamp = timezone.now() - timedelta(days=10)
        Order.objects.filter(order_id=old_order.order_id).update(created_at=old_timestamp)
        old_interaction = UserInteraction.objects.create(
            user=analytics_user,
            product=self.product,
            interaction_type="impression",
        )
        UserInteraction.objects.filter(id=old_interaction.id).update(created_at=old_timestamp)

        session = self.client.session
        session["tailtalk_vendor_admin_id"] = "orijen"
        session.save()

        response = self.client.get(f"{reverse('vendor-analytics')}?period=7")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.context["vendor_analytics_period_label"], "최근 7일")
        summary = {item["label"]: item["value"] for item in response.context["vendor_analytics_summary"]}
        funnel = {item["label"]: item["value"] for item in response.context["vendor_funnel_items"]}
        self.assertEqual(summary["최근 7일 매출"], "₩49,900")
        self.assertEqual(funnel["노출"], "3")

    def test_vendor_orders_requires_vendor_session(self):
        response = self.client.get(reverse("vendor-orders"))

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response["Location"], reverse("vendor-login"))

    def test_vendor_orders_renders_mock_items(self):
        session = self.client.session
        session["tailtalk_vendor_admin_id"] = "orijen"
        session.save()

        response = self.client.get(f"{reverse('vendor-orders')}?focus=refund")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "주문 관리")
        self.assertContains(response, "취소/환불")

    def test_vendor_reviews_renders_mock_items(self):
        session = self.client.session
        session["tailtalk_vendor_admin_id"] = "orijen"
        session.save()

        response = self.client.get(f"{reverse('vendor-reviews')}?focus=pending")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "리뷰 관리")
        self.assertContains(response, "배송이 빨라서 재구매 의향이 있어요")

class UserProfileApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="profile@example.com", password="Password123!")
        UserProfile.objects.create(user=self.user, nickname="ProfileUser")
        self.client.force_authenticate(self.user)

    def test_get_me_returns_profile(self):
        response = self.client.get("/api/users/me/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["email"], "profile@example.com")
        self.assertEqual(response.data["user"]["nickname"], "ProfileUser")

    def test_patch_me_updates_profile_fields(self):
        response = self.client.patch(
            "/api/users/me/",
            {
                "nickname": "UpdatedUser",
                "phone": "01012341234",
                "postal_code": "12345",
                "address_main": "서울 강동구 올림픽로 123",
                "address_detail": "101동 1203호",
                "payment_method": "현대카드 M / 1234 **** **** 5678",
                "payment_card_provider": "현대카드 M",
                "payment_card_masked_number": "1234 **** **** 5678",
                "marketing_consent": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.profile.nickname, "UpdatedUser")
        self.assertEqual(self.user.profile.recipient_name, "UpdatedUser")
        self.assertEqual(self.user.profile.phone, "01012341234")
        self.assertEqual(self.user.profile.postal_code, "12345")
        self.assertEqual(self.user.profile.address_main, "서울 강동구 올림픽로 123")
        self.assertEqual(self.user.profile.address_detail, "101동 1203호")
        self.assertEqual(self.user.profile.address, "서울 강동구 올림픽로 123 | 101동 1203호")
        self.assertEqual(self.user.profile.payment_method, "현대카드 M / 1234 **** **** 5678")
        self.assertEqual(self.user.profile.payment_card_provider, "현대카드 M")
        self.assertEqual(self.user.profile.payment_card_masked_number, "1234 **** **** 5678")
        self.assertTrue(self.user.profile.marketing_consent)

    def test_get_quick_purchase_defaults_returns_structured_profile_data(self):
        self.user.profile.nickname = "배송받는사람"
        self.user.profile.recipient_name = "배송받는사람"
        self.user.profile.phone = "01012341234"
        self.user.profile.postal_code = "12345"
        self.user.profile.address_main = "서울 강동구 올림픽로 123"
        self.user.profile.address_detail = "101동 1203호"
        self.user.profile.address = "서울 강동구 올림픽로 123 | 101동 1203호"
        self.user.profile.payment_method = "현대카드 M / 1234 **** **** 5678"
        self.user.profile.payment_card_provider = "현대카드 M"
        self.user.profile.payment_card_masked_number = "1234 **** **** 5678"
        self.user.profile.save()

        response = self.client.get("/api/users/me/quick-purchase/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        quick_purchase = response.data["quick_purchase"]
        self.assertTrue(quick_purchase["has_delivery_info"])
        self.assertTrue(quick_purchase["has_payment_method"])
        self.assertEqual(quick_purchase["recipient_name"], "배송받는사람")
        self.assertEqual(quick_purchase["postal_code"], "12345")
        self.assertEqual(quick_purchase["address_main"], "서울 강동구 올림픽로 123")
        self.assertEqual(quick_purchase["address_detail"], "101동 1203호")
        self.assertEqual(quick_purchase["payment_summary"], "현대카드 M / 1234 **** **** 5678")

    def test_phone_verification_request_returns_code(self):
        response = self.client.post(
            "/api/users/me/phone-verification/request/",
            {"phone": "01012341234"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["phone"], "01012341234")
        self.assertIn("verification_code", response.data)
        self.user.refresh_from_db()
        self.assertEqual(self.user.profile.phone_verification_target, "01012341234")

    def test_phone_verification_confirm_marks_phone_verified(self):
        request_response = self.client.post(
            "/api/users/me/phone-verification/request/",
            {"phone": "01012341234"},
            format="json",
        )

        response = self.client.post(
            "/api/users/me/phone-verification/confirm/",
            {
                "phone": "01012341234",
                "verification_code": request_response.data["verification_code"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.profile.phone, "01012341234")
        self.assertTrue(self.user.profile.phone_verified)
        self.assertIsNone(self.user.profile.phone_verification_code)

    def test_patch_me_resets_phone_verified_when_phone_changes(self):
        self.user.profile.phone = "01012341234"
        self.user.profile.phone_verified = True
        self.user.profile.save(update_fields=["phone", "phone_verified", "updated_at"])

        response = self.client.patch(
            "/api/users/me/",
            {"phone": "01099998888"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.profile.phone, "01099998888")
        self.assertFalse(self.user.profile.phone_verified)

    def test_nickname_availability_returns_available_for_current_nickname(self):
        response = self.client.get("/api/users/nickname-availability/?nickname=ProfileUser")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["valid"])
        self.assertTrue(response.data["available"])

    def test_nickname_availability_returns_available_for_current_nickname_with_session_login(self):
        session_client = self.client_class()
        session_client.force_login(self.user)

        response = session_client.get("/api/users/nickname-availability/?nickname=ProfileUser")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["valid"])
        self.assertTrue(response.data["available"])

    def test_nickname_availability_returns_unavailable_for_other_users_nickname(self):
        other_user = User.objects.create_user(email="other@example.com", password="Password123!")
        UserProfile.objects.create(user=other_user, nickname="TakenNick")

        response = self.client.get("/api/users/nickname-availability/?nickname=TakenNick")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["valid"])
        self.assertFalse(response.data["available"])
        self.assertEqual(response.data["detail"], "이미 사용 중인 닉네임입니다.")

    def test_patch_me_rejects_duplicate_nickname(self):
        other_user = User.objects.create_user(email="other@example.com", password="Password123!")
        UserProfile.objects.create(user=other_user, nickname="TakenNick")

        response = self.client.patch(
            "/api/users/me/",
            {"nickname": "TakenNick"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "이미 사용 중인 닉네임입니다.")

    def test_user_profile_nickname_duplicate_is_rejected_by_api_validation(self):
        other_user = User.objects.create_user(email="other@example.com", password="Password123!")
        UserProfile.objects.create(user=other_user, nickname="TakenNick")

        response = self.client.patch(
            "/api/users/me/",
            {"nickname": "TakenNick"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "이미 사용 중인 닉네임입니다.")

class UserPreferenceApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="preferences@example.com", password="Password123!")
        UserProfile.objects.create(user=self.user, nickname="PreferenceUser")
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
        UserProfile.objects.create(user=self.user, nickname="UsedProduct")
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
