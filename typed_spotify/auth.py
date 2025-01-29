import asyncio
import base64
import json
import logging
import secrets
import webbrowser
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Union
from urllib.parse import urlencode

from aiohttp import web
from httpx import AsyncClient, HTTPError
from pydantic import BaseModel, Field, field_validator

from typed_spotify.exceptions import AuthenticationError

logger = logging.getLogger(__name__)


class Token(BaseModel):
    """OAuth token model"""

    token_type: str = Field(default="Bearer", pattern="^Bearer$")
    access_token: str
    refresh_token: Optional[str] = None
    scope: Union[str, List[str]] = Field(default="")
    expires_in: int = Field(gt=0)
    expires_at: Optional[datetime] = None

    @property
    def is_expired(self) -> bool:
        """Check if the token is expired with a 30-second buffer."""
        if not self.expires_at:
            return True
        return datetime.now(timezone.utc) >= (self.expires_at - timedelta(seconds=30))

    @field_validator("expires_at", mode="before")
    def set_expires_at(cls, v: Optional[datetime], info) -> Optional[datetime]:
        """Set expires_at if not provided using expires_in."""
        context = info.data
        if not v and "expires_in" in context:
            return datetime.now(timezone.utc) + timedelta(seconds=context["expires_in"] - 60)
        return v


class TokenStorage(ABC):
    """Abstract base class for token storage implementations."""

    @abstractmethod
    async def save_token(self, token: Token) -> None:
        """Save a token to storage."""
        pass

    @abstractmethod
    async def load_token(self) -> Optional[Token]:
        """Load a token from storage."""
        pass

    @abstractmethod
    async def delete_token(self) -> None:
        """Delete a token from storage."""
        pass


class MemoryTokenStorage(TokenStorage):
    """In-memory token storage for testing."""

    def __init__(self):
        self._token: Optional[Token] = None

    async def save_token(self, token: Token) -> None:
        self._token = token

    async def load_token(self) -> Optional[Token]:
        return self._token

    async def delete_token(self) -> None:
        self._token = None


class FileTokenStorage(TokenStorage):
    """File-based token storage implementation."""

    def __init__(self, token_path: str = ".spotify"):
        self.token_path = Path(token_path)

    async def save_token(self, token: Token) -> None:
        try:
            self.token_path.parent.mkdir(parents=True, exist_ok=True)
            token_data = token.model_dump(exclude_none=True)

            token_data["_stored_at"] = datetime.now(timezone.utc).isoformat()

            with open(self.token_path, "w") as f:
                json.dump(token_data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save token to file: {str(e)}")
            raise AuthenticationError(f"Failed to save token: {str(e)}") from e

    async def load_token(self) -> Optional[Token]:
        try:
            if not self.token_path.exists():
                return None

            with open(self.token_path) as f:
                token_data = json.load(f)

            token_data.pop("_stored_at", None)
            return Token.model_validate(token_data)

        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.debug(f"No valid token found at {self.token_path}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error loading token from file: {str(e)}")
            return None

    async def delete_token(self) -> None:
        try:
            self.token_path.unlink(missing_ok=True)
        except Exception as e:
            logger.error(f"Failed to delete token file: {str(e)}")
            raise AuthenticationError(f"Failed to delete token: {str(e)}") from e


class SpotifyAuth:
    """Spotify authentication handler with pluggable token storage."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        scope: Optional[Union[str, List[str]]] = None,
        token_storage: Optional[TokenStorage] = None,
        callback_port: int = 9090,
        request_timeout: float = 30.0,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = f"http://localhost:{callback_port}/callback"
        self.token_storage = token_storage or FileTokenStorage()
        self.callback_port = callback_port
        self.client = AsyncClient(timeout=request_timeout)

        if isinstance(scope, list):
            self.scope = " ".join(scope)
        else:
            self.scope = scope or ""

    async def __aenter__(self) -> "SpotifyAuth":
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    @property
    async def token(self) -> Optional[Token]:
        """Get the current token from storage."""
        return await self.token_storage.load_token()

    @token.setter
    async def token(self, value: Optional[Token]) -> None:
        """Save or delete the token from storage."""
        if value is None:
            await self.token_storage.delete_token()
        else:
            await self.token_storage.save_token(value)

    def _get_auth_header(self) -> Dict[str, str]:
        """Get Basic Auth header for client credentials."""
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_b64 = base64.b64encode(auth_string.encode()).decode()
        return {
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

    async def refresh_token(self, refresh_token: str) -> Token:
        """Refresh the access token with automatic retries."""
        try:
            response = await self.client.post(
                url="https://accounts.spotify.com/api/token",
                headers=self._get_auth_header(),
                data={"grant_type": "refresh_token", "refresh_token": refresh_token},
            )
            response.raise_for_status()

            token = Token.model_validate(response.json())
            current_token = await self.token
            if not token.refresh_token and current_token:
                token.refresh_token = current_token.refresh_token
            await self.token_storage.save_token(token)
            return token

        except HTTPError as e:
            raise AuthenticationError(f"Failed to refresh token: {str(e)}") from e

    async def get_access_token(self) -> str:
        """Get a valid access token, refreshing if necessary."""
        current_token = await self.token
        if current_token and not current_token.is_expired:
            return current_token.access_token

        if current_token and current_token.refresh_token:
            try:
                return (await self.refresh_token(current_token.refresh_token)).access_token
            except AuthenticationError:
                logger.info("Token refresh failed, starting new authorization flow")

        return (await self.authorize()).access_token

    async def authorize(self) -> Token:
        """Run authorization flow"""
        app = web.Application()
        auth_code_future: asyncio.Future[str] = asyncio.Future()
        state = secrets.token_urlsafe(32)

        async def callback_handler(request: web.Request) -> web.Response:
            if request.query.get("state") != state:
                auth_code_future.set_exception(AuthenticationError("State mismatch, possible CSRF attack"))
                return web.Response(
                    content_type="text/html",
                    text="<h1>Authorization Failed</h1><p>Invalid state parameter.</p>",
                )
            if "error" in request.query:
                auth_code_future.set_exception(AuthenticationError(f"Authorization failed: {request.query['error']}"))
                return web.Response(
                    content_type="text/html",
                    text="<h1>Authorization Failed</h1><p>Please check the application logs.</p>",
                )

            if code := request.query.get("code"):
                auth_code_future.set_result(code)
                return web.Response(
                    content_type="text/html",
                    text="<h1>Authorization Successful</h1><p>You can close this window.</p>",
                )

            raise web.HTTPBadRequest(text="No authorization code received")

        app.router.add_get(path="/callback", handler=callback_handler)
        runner = web.AppRunner(app=app)
        await runner.setup()
        site = web.TCPSite(runner=runner, host="localhost", port=self.callback_port)

        try:
            await site.start()
            auth_url = "https://accounts.spotify.com/authorize?" + urlencode(
                {
                    "client_id": self.client_id,
                    "response_type": "code",
                    "redirect_uri": self.redirect_uri,
                    "scope": self.scope,
                    "state": state,
                }
            )
            webbrowser.open(auth_url)

            try:
                auth_code = await asyncio.wait_for(auth_code_future, timeout=300)
            except asyncio.TimeoutError:
                raise AuthenticationError("Authorization timed out after 5 minutes")

            try:
                response = await self.client.post(
                    url="https://accounts.spotify.com/api/token",
                    headers=self._get_auth_header(),
                    data={
                        "grant_type": "authorization_code",
                        "code": auth_code,
                        "redirect_uri": self.redirect_uri,
                    },
                )
                response.raise_for_status()

                token = Token.model_validate(response.json())
                await self.token_storage.save_token(token)
                return token

            except HTTPError as e:
                raise AuthenticationError(f"Failed to get token: {str(e)}") from e

        finally:
            await runner.cleanup()
