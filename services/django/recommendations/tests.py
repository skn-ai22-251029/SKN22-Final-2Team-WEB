from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from pets.models import Pet
from recommendations.clients.fastapi_recommend_client import RecommendClientError
from users.models import User


class RecommendProxyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="recommend@example.com", password="Password123!")
        self.pet = Pet.objects.create(
            user=self.user,
            name="Nabi",
            species="cat",
            gender="female",
            budget_range="5_10",
        )

    @patch("recommendations.api.views.request_recommendations")
    def test_proxy_calls_fastapi_with_user_context(self, request_recommendations_mock):
        request_recommendations_mock.return_value = {
            "products": [{"goods_id": "GP001", "product_name": "추천 상품"}],
            "meta": {"reranked_count": 1},
        }
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("recommend-proxy"),
            {"query": "피부 간식", "target_pet_id": str(self.pet.pet_id), "limit": "7"},
            HTTP_X_REQUEST_ID="req-recommend-test",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Request-Id"], "req-recommend-test")
        self.assertEqual(response.json()["products"][0]["goods_id"], "GP001")
        request_recommendations_mock.assert_called_once()
        call_kwargs = request_recommendations_mock.call_args.kwargs
        self.assertEqual(call_kwargs["user_id"], self.user.id)
        self.assertEqual(call_kwargs["query"], "피부 간식")
        self.assertEqual(call_kwargs["target_pet_id"], str(self.pet.pet_id))
        self.assertEqual(call_kwargs["limit"], 7)
        self.assertEqual(call_kwargs["request_id"], "req-recommend-test")

    @patch("recommendations.api.views.request_recommendations")
    def test_proxy_uses_default_query_and_limit(self, request_recommendations_mock):
        request_recommendations_mock.return_value = {"products": [], "meta": {"reranked_count": 0}}
        self.client.force_login(self.user)

        response = self.client.get(reverse("recommend-proxy"))

        self.assertEqual(response.status_code, 200)
        call_kwargs = request_recommendations_mock.call_args.kwargs
        self.assertEqual(call_kwargs["query"], "맞춤 상품 추천")
        self.assertEqual(call_kwargs["limit"], 5)

    def test_proxy_rejects_unowned_target_pet(self):
        other_user = User.objects.create_user(email="other-recommend@example.com", password="Password123!")
        other_pet = Pet.objects.create(
            user=other_user,
            name="Bori",
            species="dog",
            gender="male",
            budget_range="5_10",
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("recommend-proxy"), {"target_pet_id": str(other_pet.pet_id)})

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "target_pet_not_found")

    @patch("recommendations.api.views.request_recommendations")
    def test_proxy_maps_fastapi_client_error(self, request_recommendations_mock):
        request_recommendations_mock.side_effect = RecommendClientError(
            "추천 서버와 연결하지 못했습니다.",
            status_code=502,
            code="recommendation_connection_failed",
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("recommend-proxy"))

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["code"], "recommendation_connection_failed")
