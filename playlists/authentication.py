from dataclasses import dataclass
from functools import lru_cache
import uuid

import jwt
from django.conf import settings
from jwt import PyJWKClient
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication, get_authorization_header

from .middleware import set_database_claims


@dataclass(frozen=True)
class SupabaseUser:
    id: str
    role: str
    claims: dict

    @property
    def is_authenticated(self):
        return True


@lru_cache(maxsize=4)
def _jwks_client(url):
    return PyJWKClient(url, cache_keys=True)


class SupabaseJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        header = get_authorization_header(request).split()
        if not header:
            return None
        if len(header) != 2 or header[0].lower() != b"bearer":
            raise exceptions.AuthenticationFailed("Use a Bearer access token.")

        token = header[1].decode("utf-8")
        try:
            claims = self._decode_token(token)
        except (jwt.PyJWTError, ValueError, RuntimeError) as error:
            raise exceptions.AuthenticationFailed("Invalid or expired access token.") from error

        subject = claims.get("sub")
        if not subject or claims.get("role") != "authenticated":
            raise exceptions.AuthenticationFailed("This account is not authorized.")
        try:
            user_id = str(uuid.UUID(subject))
        except (TypeError, ValueError, AttributeError) as error:
            raise exceptions.AuthenticationFailed("Invalid user identity in token.") from error

        app_metadata = claims.get("app_metadata") or {}
        if not isinstance(app_metadata, dict):
            raise exceptions.AuthenticationFailed("Invalid account role in token.")
        role = app_metadata.get("role", "user")
        set_database_claims(user_id)
        return SupabaseUser(id=user_id, role=role, claims=claims), claims

    def authenticate_header(self, request):
        return "Bearer"

    def _decode_token(self, token):
        unverified_header = jwt.get_unverified_header(token)
        algorithm = unverified_header.get("alg")
        options = {"require": ["exp", "sub", "aud"]}
        decode_options = {
            "audience": settings.SUPABASE_JWT_AUDIENCE,
            "options": options,
        }
        if settings.SUPABASE_JWT_ISSUER:
            decode_options["issuer"] = settings.SUPABASE_JWT_ISSUER

        if algorithm == "HS256":
            if not settings.SUPABASE_JWT_SECRET:
                raise ValueError("SUPABASE_JWT_SECRET is required for HS256 tokens.")
            return jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                **decode_options,
            )

        if not settings.SUPABASE_JWKS_URL:
            raise ValueError("SUPABASE_JWKS_URL is required for asymmetric tokens.")
        signing_key = _jwks_client(settings.SUPABASE_JWKS_URL).get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=[signing_key.algorithm_name],
            **decode_options,
        )
