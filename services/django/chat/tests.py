from unittest.mock import patch

import httpx
from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from pets.models import Pet, PetAllergy, PetFoodPreference, PetHealthConcern
from users.models import User, UserProfile
from users.onboarding import ONBOARDING_FORCE_PROFILE_SESSION_KEY


class ChatPageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="chat-owner@example.com",
            password="Password123!",
        )
        UserProfile.objects.create(user=self.user, nickname="Chat Owner")
        self.client.force_login(self.user)

    def test_chat_page_renders_related_pet_fields(self):
        pet = Pet.objects.create(
            user=self.user,
            name="Nabi",
            species="cat",
            gender="female",
            budget_range="5_10",
        )
        PetHealthConcern.objects.create(pet=pet, concern="skin")
        PetAllergy.objects.create(pet=pet, ingredient="chicken")
        PetFoodPreference.objects.create(pet=pet, food_type="dry")

        response = self.client.get(reverse("chat"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["member_pets"]), 1)
        serialized_pet = response.context["member_pets"][0]
        self.assertEqual(serialized_pet["health_concerns"], ["skin"])
        self.assertEqual(serialized_pet["allergies"], ["chicken"])
        self.assertEqual(serialized_pet["food_preferences"], ["dry"])

    def test_chat_page_profile_menu_includes_wishlist_link(self):
        Pet.objects.create(
            user=self.user,
            name="Bori",
            species="dog",
            gender="male",
            budget_range="5_10",
        )

        response = self.client.get(reverse("chat"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "/products/?tab=wishlist")
        self.assertContains(response, "관심 상품")

    def test_chat_page_redirects_to_pet_add_when_profile_complete_but_no_pet(self):
        response = self.client.get(reverse("chat"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("pet_add"))

    def test_chat_page_redirects_to_profile_setup_when_profile_is_incomplete(self):
        incomplete_user = User.objects.create_user(
            email="chat-incomplete@example.com",
            password="Password123!",
        )
        UserProfile.objects.create(user=incomplete_user, nickname="")
        self.client.force_login(incomplete_user)

        response = self.client.get(reverse("chat"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], f"{reverse('profile')}?setup=1")

    def test_chat_page_redirects_to_profile_setup_when_new_user_force_flag_exists(self):
        session = self.client.session
        session[ONBOARDING_FORCE_PROFILE_SESSION_KEY] = True
        session.save()

        response = self.client.get(reverse("chat"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], f"{reverse('profile')}?setup=1")


class _FakeStreamResponse:
    def __init__(self, chunks, status_code=200):
        self._chunks = chunks
        self.status_code = status_code
        self.text = ""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def iter_bytes(self):
        for chunk in self._chunks:
            yield chunk

    def json(self):
        return {"detail": "error"}


class _FakeJsonResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = ""

    def json(self):
        return self._payload


class _ExplodingHttpxClient:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def request(self, method, url, headers=None, json=None):
        raise httpx.ConnectError("connection failed")

    def stream(self, method, url, headers=None, json=None):
        raise httpx.ConnectError("connection failed")


class _TimeoutHttpxClient:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def request(self, method, url, headers=None, json=None):
        raise httpx.ReadTimeout("timed out")

    def stream(self, method, url, headers=None, json=None):
        raise httpx.ReadTimeout("timed out")


class _FakeHttpxClient:
    last_request = None
    last_stream_request = None

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def request(self, method, url, headers=None, json=None):
        self.__class__.last_request = {
            "method": method,
            "url": url,
            "headers": headers,
            "json": json,
        }
        if method == "GET" and url.endswith("/sessions/"):
            return _FakeJsonResponse(
                {
                    "sessions": [
                        {
                            "session_id": "11111111-1111-1111-1111-111111111111",
                            "title": "기존 세션",
                            "display_date": "26/03/23",
                        }
                    ],
                    "groups": [
                        {
                            "key": "today",
                            "label": "오늘",
                            "sessions": [
                                {
                                    "session_id": "11111111-1111-1111-1111-111111111111",
                                    "title": "기존 세션",
                                    "display_date": "26/03/23",
                                }
                            ],
                        }
                    ],
                }
            )
        if method == "GET" and url.endswith("/messages/"):
            return _FakeJsonResponse(
                {
                    "session_id": "11111111-1111-1111-1111-111111111111",
                    "messages": [
                        {
                            "message_id": "22222222-2222-2222-2222-222222222222",
                            "role": "user",
                            "content": "hello",
                            "created_at": "2026-03-23T10:00:00+09:00",
                        }
                    ],
                    "history_trimmed": False,
                }
            )
        if method == "POST" and url.endswith("/sessions/"):
            return _FakeJsonResponse(
                {
                    "session_id": "33333333-3333-3333-3333-333333333333",
                    "title": json.get("title"),
                    "target_pet_id": json.get("target_pet_id"),
                    "display_date": "26/03/23",
                },
                status_code=201,
            )
        if method == "PATCH":
            return _FakeJsonResponse(
                {
                    "session_id": "11111111-1111-1111-1111-111111111111",
                    "title": json.get("title"),
                    "display_date": "26/03/23",
                }
            )
        if method == "DELETE":
            return _FakeJsonResponse({"deleted": True})
        return _FakeJsonResponse({"detail": "ok"})

    def stream(self, method, url, headers=None, json=None):
        self.__class__.last_stream_request = {
            "method": method,
            "url": url,
            "headers": headers,
            "json": json,
        }
        return _FakeStreamResponse(
            [
                b'data: {"type":"token","content":"hello"}\n\n',
                b'data: {"type":"done"}\n\n',
            ]
        )


class ChatProxyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="chat-proxy@example.com",
            password="Password123!",
        )
        UserProfile.objects.create(user=self.user, nickname="ChatProxy")

    def test_chat_proxy_requires_authentication(self):
        response = self.client.post(
            "/api/chat/",
            data='{"message":"hello"}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)

    @patch("chat.api_views.httpx.Client", _FakeHttpxClient)
    def test_chat_proxy_streams_fastapi_response_with_internal_auth_headers(self):
        self.client.force_login(self.user)

        response = self.client.post(
            "/api/chat/",
            data='{"message":"hello","thread_id":"thread-1","pet_profile":{"species":"cat"}}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/event-stream")
        payload = b"".join(response.streaming_content).decode("utf-8")
        self.assertIn('"type":"token"', payload)
        self.assertEqual(_FakeHttpxClient.last_stream_request["url"], settings.FASTAPI_INTERNAL_CHAT_URL)
        self.assertEqual(
            _FakeHttpxClient.last_stream_request["headers"]["X-Internal-Service-Token"],
            settings.INTERNAL_SERVICE_TOKEN,
        )
        self.assertEqual(_FakeHttpxClient.last_stream_request["headers"]["X-User-Id"], str(self.user.id))
        self.assertEqual(_FakeHttpxClient.last_stream_request["json"]["thread_id"], "thread-1")

    @patch("chat.api_views.httpx.Client", _FakeHttpxClient)
    def test_sessions_proxy_supports_list_create_update_delete_and_message_load(self):
        self.client.force_login(self.user)

        list_response = self.client.get("/api/chat/sessions/")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["groups"][0]["key"], "today")
        self.assertEqual(_FakeHttpxClient.last_request["url"], settings.FASTAPI_INTERNAL_CHAT_URL.rstrip("/") + "/sessions/")

        create_response = self.client.post(
            "/api/chat/sessions/",
            data='{"title":"신규 세션","target_pet_id":"44444444-4444-4444-4444-444444444444"}',
            content_type="application/json",
        )
        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(create_response.json()["title"], "신규 세션")
        self.assertEqual(_FakeHttpxClient.last_request["json"]["target_pet_id"], "44444444-4444-4444-4444-444444444444")

        patch_response = self.client.patch(
            "/api/chat/sessions/11111111-1111-1111-1111-111111111111/",
            data='{"title":"수정 제목"}',
            content_type="application/json",
        )
        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(patch_response.json()["title"], "수정 제목")

        messages_response = self.client.get("/api/chat/sessions/11111111-1111-1111-1111-111111111111/messages/")
        self.assertEqual(messages_response.status_code, 200)
        self.assertEqual(messages_response.json()["messages"][0]["content"], "hello")

        delete_response = self.client.delete("/api/chat/sessions/11111111-1111-1111-1111-111111111111/")
        self.assertEqual(delete_response.status_code, 200)
        self.assertTrue(delete_response.json()["deleted"])

    @patch("chat.api_views.httpx.Client", _FakeHttpxClient)
    def test_session_messages_proxy_streams_to_fastapi(self):
        self.client.force_login(self.user)

        response = self.client.post(
            "/api/chat/sessions/11111111-1111-1111-1111-111111111111/messages/",
            data='{"message":"hello","pet_profile":{"species":"cat"}}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/event-stream")
        payload = b"".join(response.streaming_content).decode("utf-8")
        self.assertIn('"type":"done"', payload)
        self.assertEqual(
            _FakeHttpxClient.last_stream_request["url"],
            settings.FASTAPI_INTERNAL_CHAT_URL.rstrip("/") + "/sessions/11111111-1111-1111-1111-111111111111/messages/",
        )
        self.assertEqual(_FakeHttpxClient.last_stream_request["json"]["message"], "hello")

    @patch("chat.api_views.httpx.Client", _ExplodingHttpxClient)
    def test_sessions_proxy_returns_controlled_error_when_fastapi_is_unreachable(self):
        self.client.force_login(self.user)

        response = self.client.get("/api/chat/sessions/")

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["detail"], "채팅 서버와 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.")

    @patch("chat.api_views.httpx.Client", _TimeoutHttpxClient)
    def test_sessions_proxy_returns_timeout_error_when_fastapi_response_is_delayed(self):
        self.client.force_login(self.user)

        response = self.client.get("/api/chat/sessions/")

        self.assertEqual(response.status_code, 504)
        self.assertEqual(response.json()["detail"], "채팅 서버 응답이 지연되고 있습니다. 잠시 후 다시 시도해 주세요.")

    @patch("chat.api_views.httpx.Client", _ExplodingHttpxClient)
    def test_session_messages_proxy_streams_controlled_error_event_when_fastapi_is_unreachable(self):
        self.client.force_login(self.user)

        response = self.client.post(
            "/api/chat/sessions/11111111-1111-1111-1111-111111111111/messages/",
            data='{"message":"hello"}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = b"".join(response.streaming_content).decode("utf-8")
        self.assertIn('"type": "error"', payload)
        self.assertIn("채팅 서버와 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.", payload)
