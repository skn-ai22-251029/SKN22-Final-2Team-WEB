import json
import secrets
from dataclasses import dataclass
from urllib import error, parse, request

from django.conf import settings


class SocialAuthError(Exception):
    pass


@dataclass
class SocialUserProfile:
    provider: str
    provider_user_id: str
    email: str
    nickname: str
    profile_image_url: str
    extra_data: dict


class OAuthProviderClient:
    def __init__(self, provider: str):
        provider_config = settings.SOCIAL_AUTH_PROVIDERS.get(provider)
        if not provider_config:
            raise SocialAuthError(f"Unsupported provider: {provider}")

        self.provider = provider
        self.config = provider_config

        if not self.config.get("client_id") or not self.config.get("client_secret"):
            raise SocialAuthError(f"{provider} OAuth credentials are not configured.")

    def build_authorization_url(self, redirect_uri: str, state: str | None = None) -> dict:
        state = state or secrets.token_urlsafe(24)
        query = {
            "client_id": self.config["client_id"],
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": state,
        }

        if self.provider == "google":
            query["scope"] = "openid email profile"
            query["access_type"] = "offline"
            query["include_granted_scopes"] = "true"
        elif self.provider == "kakao":
            query["scope"] = "profile_nickname profile_image account_email"

        return {
            "provider": self.provider,
            "authorization_url": f"{self.config['authorize_url']}?{parse.urlencode(query)}",
            "state": state,
        }

    def exchange_code(self, code: str, redirect_uri: str, state: str | None = None) -> SocialUserProfile:
        token_data = {
            "grant_type": "authorization_code",
            "client_id": self.config["client_id"],
            "client_secret": self.config["client_secret"],
            "code": code,
            "redirect_uri": redirect_uri,
        }

        if self.provider == "naver":
            if not state:
                raise SocialAuthError("Naver login requires state.")
            token_data["state"] = state

        token_response = self._post_form_json(self.config["token_url"], token_data)
        access_token = token_response.get("access_token")
        if not access_token:
            raise SocialAuthError(f"{self.provider} token response did not include an access token.")

        profile_response = self._get_json(
            self.config["userinfo_url"],
            headers={"Authorization": f"Bearer {access_token}"},
        )
        return self._normalize_profile(profile_response)

    def _normalize_profile(self, payload: dict) -> SocialUserProfile:
        if self.provider == "google":
            provider_user_id = str(payload["sub"])
            return SocialUserProfile(
                provider=self.provider,
                provider_user_id=provider_user_id,
                email=payload.get("email", ""),
                nickname=payload.get("name") or payload.get("email", "").split("@")[0] or f"google_{provider_user_id}",
                profile_image_url=payload.get("picture", ""),
                extra_data=payload,
            )

        if self.provider == "naver":
            response = payload.get("response") or {}
            provider_user_id = str(response["id"])
            return SocialUserProfile(
                provider=self.provider,
                provider_user_id=provider_user_id,
                email=response.get("email", ""),
                nickname=response.get("nickname") or response.get("name") or f"naver_{provider_user_id}",
                profile_image_url=response.get("profile_image", ""),
                extra_data=payload,
            )

        if self.provider == "kakao":
            account = payload.get("kakao_account") or {}
            profile = account.get("profile") or {}
            provider_user_id = str(payload["id"])
            return SocialUserProfile(
                provider=self.provider,
                provider_user_id=provider_user_id,
                email=account.get("email", ""),
                nickname=profile.get("nickname") or f"kakao_{provider_user_id}",
                profile_image_url=profile.get("profile_image_url", ""),
                extra_data=payload,
            )

        raise SocialAuthError(f"Unsupported provider: {self.provider}")

    def _post_form_json(self, url: str, data: dict) -> dict:
        encoded = parse.urlencode(data).encode()
        req = request.Request(url, data=encoded, headers={"Content-Type": "application/x-www-form-urlencoded"})
        return self._read_json(req)

    def _get_json(self, url: str, headers: dict | None = None) -> dict:
        req = request.Request(url, headers=headers or {})
        return self._read_json(req)

    def _read_json(self, req: request.Request) -> dict:
        try:
            with request.urlopen(req, timeout=10) as response:
                return json.loads(response.read().decode())
        except error.HTTPError as exc:
            body = exc.read().decode(errors="ignore")
            raise SocialAuthError(f"{self.provider} request failed: {body or exc.reason}") from exc
        except error.URLError as exc:
            raise SocialAuthError(f"{self.provider} request failed: {exc.reason}") from exc
