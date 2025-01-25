import asyncio
import logging
from json import JSONDecodeError
from typing import Any, Dict, Optional, List, Literal, Type, Union

from httpx import AsyncClient, HTTPError

from typed_spotify.exceptions import (
    AuthenticationError,
    APIError,
    RateLimitError,
    ResourceNotFoundError,
    ValidationError,
)
from typed_spotify.models import (
    Album,
    Artist,
    Audiobook,
    BooleanArray,
    Category,
    Chapter,
    CursorPaging,
    Device,
    Episode,
    Image,
    ItemList,
    Markets,
    Paging,
    PlaybackQueue,
    PlaybackState,
    PlayHistoryPage,
    Playlist,
    PlaylistSnapshotId,
    PlaylistTrack,
    SavedItem,
    SearchResults,
    Show,
    SimplifiedAlbum,
    SimplifiedAudiobook,
    SimplifiedChapter,
    SimplifiedEpisode,
    SimplifiedPlaylist,
    SimplifiedShow,
    SimplifiedTrack,
    SimplifiedUser,
    Track,
    User,
    PagingObjectResponse,
    CursorPagingResponse,
)

logger = logging.getLogger(__name__)


class SpotifyClient:
    """Spotify API client."""

    def __init__(self, access_token: str, request_timeout: float = 30.0):
        """Initialize the client with authentication handler."""
        self.client = AsyncClient(
            base_url="https://api.spotify.com/v1",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=request_timeout,
        )

    async def __aenter__(self) -> "SpotifyClient":
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def get_album(self, album_id: str, market: Optional[str] = None) -> Album:
        """Get Spotify catalog information for a single album.

        Args:
            album_id: The Spotify ID of the album
            market: An ISO 3166-1 alpha-2 country code for content availability
        """
        params = {"market": market} if market else None
        return await self._request("GET", f"/albums/{album_id}", params=params, response_model=Album)

    async def get_several_albums(self, album_ids: List[str], market: Optional[str] = None) -> List[Album]:
        """Get Spotify catalog information for multiple albums.

        Args:
            album_ids: List of Spotify album IDs (maximum: 20)
            market: An ISO 3166-1 alpha-2 country code for content availability
        """
        if len(album_ids) > 20:
            raise ValidationError("Maximum of 20 album IDs allowed")

        params = {"ids": ",".join(album_ids)}
        if market:
            params["market"] = market

        response = await self._request("GET", "/albums", params=params, response_model=ItemList[Album])
        return response.items

    async def get_album_tracks(
        self, album_id: str, limit: int = 20, offset: int = 0, market: Optional[str] = None
    ) -> Paging[SimplifiedTrack]:
        """Get Spotify catalog information about an album's tracks.

        Args:
            album_id: The Spotify ID of the album
            limit: Maximum number of tracks to return (1-50)
            offset: Index of the first track to return
            market: An ISO 3166-1 alpha-2 country code for content availability
        """
        if not 0 <= limit <= 50:
            raise ValidationError("Limit must be between 0 and 50")

        params = {"limit": limit, "offset": offset}
        if market:
            params["market"] = market

        return await self._request(
            "GET", f"/albums/{album_id}/tracks", params=params, response_model=Paging[SimplifiedTrack]
        )

    async def get_saved_albums(
        self, limit: int = 20, offset: int = 0, market: Optional[str] = None
    ) -> Paging[SavedItem[Album]]:
        """Get user's saved albums.

        Scopes:
            user-library-read

        Args:
            limit: Maximum number of albums to return (1-50)
            offset: Index of the first album to return
            market: An ISO 3166-1 alpha-2 country code for content availability
        """
        if not 0 <= limit <= 50:
            raise ValidationError("Limit must be between 0 and 50")

        params = {"limit": limit, "offset": offset}
        if market:
            params["market"] = market

        return await self._request("GET", "/me/albums", params=params, response_model=Paging[SavedItem[Album]])

    async def save_albums(self, album_ids: List[str]) -> None:
        """Save albums to current user's library.

        Scopes:
            user-library-modify

        Args:
            album_ids: List of Spotify album IDs to save (max 50)
        """
        if len(album_ids) > 50:
            raise ValidationError("Maximum of 50 album IDs allowed")

        await self._request("PUT", "/me/albums", json={"ids": album_ids})

    async def remove_saved_albums(self, album_ids: List[str]) -> None:
        """Remove albums from current user's library.

        Scopes:
            user-library-modify

        Args:
            album_ids: List of Spotify album IDs to remove (max 50)
        """
        if len(album_ids) > 50:
            raise ValidationError("Maximum of 50 album IDs allowed")

        await self._request("DELETE", "/me/albums", json={"ids": album_ids})

    async def check_saved_albums(self, album_ids: List[str]) -> List[bool]:
        """Check if albums are saved in current user's library.

        Scopes:
            user-library-read

        Args:
            album_ids: List of Spotify album IDs to check (max 50)

        Returns:
            List of booleans indicating if each album is saved
        """
        if len(album_ids) > 50:
            raise ValidationError("Maximum of 50 album IDs allowed")

        response = await self._request(
            "GET", "/me/albums/contains", params={"ids": ",".join(album_ids)}, response_model=BooleanArray
        )
        return response.root

    async def get_new_releases(self, limit: int = 20, offset: int = 0) -> Paging[SimplifiedAlbum]:
        """Get new album releases featured in Spotify.

        Args:
            limit: Maximum number of albums to return (1-50)
            offset: Index of the first album to return
        """
        if not 0 <= limit <= 50:
            raise ValidationError("Limit must be between 0 and 50")

        response = await self._request(
            "GET",
            "/browse/new-releases",
            params={"limit": limit, "offset": offset},
            response_model=PagingObjectResponse[SimplifiedAlbum],
        )
        return response.items

    async def get_artist(self, artist_id: str) -> Artist:
        """Get Spotify catalog information for a single artist.

        Args:
            artist_id: The Spotify ID of the artist
        """
        return await self._request("GET", f"/artists/{artist_id}", response_model=Artist)

    async def get_several_artists(self, artist_ids: List[str]) -> List[Artist]:
        """Get Spotify catalog information for several artists.

        Args:
            artist_ids: List of the Spotify IDs for the artists (max 50)
        """
        if len(artist_ids) > 50:
            raise ValidationError("Maximum of 50 artist IDs allowed")

        response = await self._request(
            "GET", "/artists", params={"ids": ",".join(artist_ids)}, response_model=ItemList[Artist]
        )
        return response.items

    async def get_artist_albums(
        self,
        artist_id: str,
        limit: int = 20,
        offset: int = 0,
        include_groups: Optional[List[Literal["album", "single", "appears_on", "compilation"]]] = None,
        market: Optional[str] = None,
    ) -> Paging[SimplifiedAlbum]:
        """Get Spotify catalog information about an artist's albums.

        Args:
            artist_id: The Spotify ID of the artist
            limit: Maximum number of albums to return (1-50)
            offset: Index of the first album to return
            include_groups: List of keywords to filter the response
            market: An ISO 3166-1 alpha-2 country code for content availability
        """
        if not 0 <= limit <= 50:
            raise ValidationError("Limit must be between 0 and 50")

        params = {"limit": limit, "offset": offset}

        if include_groups:
            params["include_groups"] = ",".join(include_groups)
        if market:
            params["market"] = market

        return await self._request(
            "GET", f"/artists/{artist_id}/albums", params=params, response_model=Paging[SimplifiedAlbum]
        )

    async def get_artist_top_tracks(self, artist_id: str, market: str) -> List[Track]:
        """Get Spotify catalog information about an artist's top tracks by country.

        Args:
            artist_id: The Spotify ID of the artist
            market: An ISO 3166-1 alpha-2 country code for content availability
        """
        response = await self._request(
            "GET", f"/artists/{artist_id}/top-tracks", params={"market": market}, response_model=ItemList[Track]
        )
        return response.items

    async def get_audiobook(self, audiobook_id: str, market: Optional[str] = None) -> Audiobook:
        """Get Spotify catalog information for a single audiobook.

        Notes:
            Audiobooks are only available in US, UK, Canada, Ireland, New Zealand and Australia.

        Args:
            audiobook_id: The Spotify ID of the audiobook
            market: An ISO 3166-1 alpha-2 country code for content availability
        """
        params = {"market": market} if market else None
        return await self._request("GET", f"/audiobooks/{audiobook_id}", params=params, response_model=Audiobook)

    async def get_several_audiobooks(self, audiobook_ids: List[str], market: Optional[str] = None) -> List[Audiobook]:
        """Get Spotify catalog information for several audiobooks.

        Notes:
            - Audiobooks are only available in US, UK, Canada, Ireland, New Zealand and Australia.

        Args:
            audiobook_ids: List of Spotify audiobook IDs (max 50)
            market: An ISO 3166-1 alpha-2 country code for content availability
        """
        if len(audiobook_ids) > 50:
            raise ValidationError("Maximum of 50 audiobook IDs allowed")

        params = {"ids": ",".join(audiobook_ids)}
        if market:
            params["market"] = market

        response = await self._request("GET", "/audiobooks", params=params, response_model=ItemList[Audiobook])
        return response.items

    async def get_audiobook_chapters(
        self, audiobook_id: str, limit: int = 20, offset: int = 0, market: Optional[str] = None
    ) -> Paging[SimplifiedChapter]:
        """Get Spotify catalog information about an audiobook's chapters.

        Notes:
            Audiobooks are only available in US, UK, Canada, Ireland, New Zealand and Australia.

        Args:
            audiobook_id: The Spotify ID of the audiobook
            limit: Maximum number of chapters to return (1-50)
            offset: Index of the first chapter to return
            market: An ISO 3166-1 alpha-2 country code for content availability
        """
        if not 0 <= limit <= 50:
            raise ValidationError("Limit must be between 0 and 50")

        params = {"limit": limit, "offset": offset}
        if market:
            params["market"] = market

        return await self._request(
            "GET", f"/audiobooks/{audiobook_id}/chapters", params=params, response_model=Paging[SimplifiedChapter]
        )

    async def get_saved_audiobooks(self, limit: int = 20, offset: int = 0) -> Paging[SimplifiedAudiobook]:
        """Get user's saved audiobooks.

        Scopes:
            user-library-read

        Args:
            limit: Maximum number of audiobooks to return (1-50)
            offset: Index of the first audiobook to return
        """
        if not 0 <= limit <= 50:
            raise ValidationError("Limit must be between 0 and 50")

        return await self._request(
            "GET",
            "/me/audiobooks",
            params={"limit": limit, "offset": offset},
            response_model=Paging[SimplifiedAudiobook],
        )

    async def save_audiobooks(self, audiobook_ids: List[str]) -> None:
        """Save audiobooks to user's library.

        Scopes:
            user-library-modify

        Args:
            audiobook_ids: List of Spotify audiobook IDs to save (max 50)
        """
        if len(audiobook_ids) > 50:
            raise ValidationError("Maximum of 50 audiobook IDs allowed")

        await self._request("PUT", "/me/audiobooks", params={"ids": ",".join(audiobook_ids)})

    async def remove_saved_audiobooks(self, audiobook_ids: List[str]) -> None:
        """Remove audiobooks from user's library.

        Scopes:
            user-library-modify

        Args:
            audiobook_ids: List of Spotify audiobook IDs to remove (max 50)
        """
        if len(audiobook_ids) > 50:
            raise ValidationError("Maximum of 50 audiobook IDs allowed")

        await self._request("DELETE", "/me/audiobooks", params={"ids": ",".join(audiobook_ids)})

    async def check_saved_audiobooks(self, audiobook_ids: List[str]) -> List[bool]:
        """Check if audiobooks are saved in user's library.

        Scopes:
            user-library-read

        Args:
            audiobook_ids: List of Spotify audiobook IDs to check (max 50)
        """
        if len(audiobook_ids) > 50:
            raise ValidationError("Maximum of 50 audiobook IDs allowed")

        response = await self._request(
            "GET", "/me/audiobooks/contains", params={"ids": ",".join(audiobook_ids)}, response_model=BooleanArray
        )
        return response.root

    async def get_category(self, category_id: str, locale: Optional[str] = None) -> Category:
        """Get a single category used to tag items in Spotify.

        Args:
            category_id: The Spotify category ID
            locale: Desired language (ISO 639-1 + ISO 3166-1 alpha-2 country code, e.g. 'es_MX')
        """
        params = {"locale": locale} if locale else None
        return await self._request("GET", f"/browse/categories/{category_id}", params=params, response_model=Category)

    async def get_several_categories(
        self, limit: int = 20, offset: int = 0, locale: Optional[str] = None
    ) -> List[Category]:
        """Get a list of categories used to tag items in Spotify.

        Args:
            limit: Maximum number of categories to return (1-50)
            offset: Index of the first category to return
            locale: Desired language (ISO 639-1 + ISO 3166-1 alpha-2 country code, e.g. 'es_MX')
        """
        if not 0 <= limit <= 50:
            raise ValidationError("Limit must be between 0 and 50")

        params = {"limit": limit, "offset": offset}
        if locale:
            params["locale"] = locale

        response = await self._request("GET", "/browse/categories", params=params, response_model=ItemList[Category])
        return response.items

    async def get_chapter(self, chapter_id: str, market: Optional[str] = None) -> Chapter:
        """Get Spotify catalog information for a single audiobook chapter.

        Notes:
            Chapters are only available in US, UK, Canada, Ireland, New Zealand and Australia.

        Args:
            chapter_id: The Spotify ID of the chapter
            market: An ISO 3166-1 alpha-2 country code for content availability
        """
        params = {"market": market} if market else None
        return await self._request("GET", f"/chapters/{chapter_id}", params=params, response_model=Chapter)

    async def get_several_chapters(self, chapter_ids: List[str], market: Optional[str] = None) -> List[Chapter]:
        """Get Spotify catalog information for several audiobook chapters.

        Notes:
            Chapters are only available in US, UK, Canada, Ireland, New Zealand and Australia.

        Args:
            chapter_ids: List of Spotify chapter IDs (max 50)
            market: An ISO 3166-1 alpha-2 country code for content availability
        """
        if len(chapter_ids) > 50:
            raise ValidationError("Maximum of 50 chapter IDs allowed")

        params = {"ids": ",".join(chapter_ids)}
        if market:
            params["market"] = market

        response = await self._request("GET", "/chapters", params=params, response_model=ItemList[Chapter])
        return response.items

    async def get_episode(self, episode_id: str, market: Optional[str] = None) -> Episode:
        """Get Spotify catalog information for a single episode.

        Scopes:
            user-read-playback-position

        Args:
            episode_id: The Spotify ID for the episode
            market: An ISO 3166-1 alpha-2 country code for content availability
        """
        params = {"market": market} if market else None
        return await self._request("GET", f"/episodes/{episode_id}", params=params, response_model=Episode)

    async def get_several_episodes(self, episode_ids: List[str], market: Optional[str] = None) -> List[Episode]:
        """Get Spotify catalog information for several episodes.

        Scopes:
            user-read-playback-position

        Args:
            episode_ids: List of the Spotify IDs for the episodes (max 50)
            market: An ISO 3166-1 alpha-2 country code for content availability
        """
        if len(episode_ids) > 50:
            raise ValidationError("Maximum of 50 episode IDs allowed")

        params = {"ids": ",".join(episode_ids)}
        if market:
            params["market"] = market

        response = await self._request("GET", "/episodes", params=params, response_model=ItemList[Episode])
        return response.items

    async def get_saved_episodes(
        self, limit: int = 20, offset: int = 0, market: Optional[str] = None
    ) -> Paging[SavedItem[Episode]]:
        """Get a list of the episodes saved in the current user's library.

        Scopes:
            user-library-read
            user-read-playback-position

        Notes:
            This API endpoint is in beta and could change without warning.

        Args:
            limit: Maximum number of episodes to return (1-50)
            offset: Index of the first episode to return
            market: An ISO 3166-1 alpha-2 country code for content availability
        """
        if not 0 <= limit <= 50:
            raise ValidationError("Limit must be between 0 and 50")

        params = {"limit": limit, "offset": offset}
        if market:
            params["market"] = market

        return await self._request("GET", "/me/episodes", params=params, response_model=Paging[SavedItem[Episode]])

    async def save_episodes(self, episode_ids: List[str]) -> None:
        """Save episodes to current user's library.

        Scopes:
            user-library-modify

        Notes:
            This API endpoint is in beta and could change without warning.

        Args:
            episode_ids: List of the Spotify IDs for the episodes (max 50)
        """
        if len(episode_ids) > 50:
            raise ValidationError("Maximum of 50 episode IDs allowed")

        await self._request("PUT", "/me/episodes", params={"ids": ",".join(episode_ids)})

    async def remove_saved_episodes(self, episode_ids: List[str]) -> None:
        """Remove episodes from current user's library.

        Scopes:
            user-library-modify

        Notes:
            This API endpoint is in beta and could change without warning.

        Args:
            episode_ids: List of the Spotify IDs for the episodes (max 50)
        """
        if len(episode_ids) > 50:
            raise ValidationError("Maximum of 50 episode IDs allowed")

        await self._request("DELETE", "/me/episodes", params={"ids": ",".join(episode_ids)})

    async def check_saved_episodes(self, episode_ids: List[str]) -> List[bool]:
        """Check if episodes are saved in current user's library.

        Scopes:
            user-library-read

        Notes:
            This API endpoint is in beta and could change without warning.

        Args:
            episode_ids: List of the Spotify IDs for the episodes (max 50)
        """
        if len(episode_ids) > 50:
            raise ValidationError("Maximum of 50 episode IDs allowed")

        response = await self._request(
            "GET", "/me/episodes/contains", params={"ids": ",".join(episode_ids)}, response_model=BooleanArray
        )
        return response.root

    async def get_available_markets(self) -> Markets:
        """Get the list of markets where Spotify is available.

        Returns:
            List of country codes where Spotify is available
        """
        return await self._request("GET", "/markets", response_model=Markets)

    async def get_playback_state(
        self, market: Optional[str] = None, additional_types: Optional[List[Literal["track", "episode"]]] = None
    ) -> Optional[PlaybackState]:
        """Get information about the user's current playback state.

        Scopes:
            user-read-playback-state

        Args:
            additional_types: Types of media in addition to track the API should handle
            market: An ISO 3166-1 alpha-2 country code for content availability
        """
        params = {}
        if market:
            params["market"] = market
        if additional_types:
            params["additional_types"] = ",".join(additional_types)

        return await self._request("GET", "/me/player", params=params, response_model=PlaybackState)

    async def get_currently_playing(
        self, additional_types: Optional[List[Literal["track", "episode"]]] = None, market: Optional[str] = None
    ) -> Optional[PlaybackState]:
        """Get the object currently being played on the user's account.

        Scopes:
            user-read-currently-playing

        Args:
            additional_types: Types of media in addition to track the API should handle
            market: An ISO 3166-1 alpha-2 country code for content availability
        """
        params = {}
        if market:
            params["market"] = market
        if additional_types:
            params["additional_types"] = ",".join(additional_types)

        return await self._request("GET", "/me/player/currently-playing", params=params, response_model=PlaybackState)

    async def get_recently_played(
        self, limit: int = 20, after: Optional[int] = None, before: Optional[int] = None
    ) -> PlayHistoryPage:
        """Get the user's recently played tracks.

        Scopes:
            user-read-recently-played

        Args:
            limit: Maximum number of tracks to return (1-50)
            after: Unix timestamp in ms to get tracks after (exclusive)
            before: Unix timestamp in ms to get tracks before (exclusive)
        """
        if not 0 <= limit <= 50:
            raise ValidationError("Limit must be between 0 and 50")
        if after and before:
            raise ValidationError("Cannot specify both after and before")

        params = {"limit": limit}
        if after:
            params["after"] = after
        if before:
            params["before"] = before

        return await self._request("GET", "/me/player/recently-played", params=params, response_model=PlayHistoryPage)

    async def get_queue(self) -> PlaybackQueue:
        """Get the user's queue.

        Scopes:
            user-read-currently-playing
            user-read-playback-state

        Returns:
            Current track and queue information
        """
        return await self._request("GET", "/me/player/queue", response_model=PlaybackQueue)

    async def get_available_devices(self) -> List[Device]:
        """Get user's available devices.

        Scopes:
            user-read-playback-state

        Returns:
            List of available devices
        """
        response = await self._request("GET", "/me/player/devices", response_model=ItemList[Device])
        return response.items

    async def transfer_playback(self, device_id: str, play: Optional[bool] = None) -> None:
        """Transfer playback to a specified device.

        Scopes:
            user-modify-playback-state

        Notes:
            Only works for premium users

        Args:
            device_id: Device to transfer playback to
            play: Whether to ensure playback happens on new device
        """
        data = {"device_ids": [device_id]}
        if play is not None:
            data["play"] = play

        await self._request("PUT", "/me/player", json=data)

    async def start_playback(
        self,
        device_id: Optional[str] = None,
        context_uri: Optional[str] = None,
        uris: Optional[List[str]] = None,
        offset: Optional[Dict[str, Any]] = None,
        position_ms: Optional[int] = None,
    ) -> None:
        """Start a new context or resume playback on the user's active device.

        Scopes:
            user-modify-playback-state

        Notes:
            Only works for premium users

        Args:
            device_id: Device ID to target, if not supplied targets active device
            context_uri: Spotify URI of context to play (album, artist, playlist)
            uris: List of Spotify track URIs to play
            offset: Offset into context (position or uri)
            position_ms: Position in track to start at
        """
        params = {"device_id": device_id} if device_id else None
        data = {}
        if context_uri:
            data["context_uri"] = context_uri
        if uris:
            data["uris"] = uris
        if offset:
            data["offset"] = offset
        if position_ms is not None:
            data["position_ms"] = position_ms

        await self._request("PUT", "/me/player/play", params=params, json=data if data else None)

    async def pause_playback(self, device_id: Optional[str] = None) -> None:
        """Pause playback on the user's account.

        Scopes:
            user-modify-playback-state

        Notes:
            Only works for premium users

        Args:
            device_id: Device ID to target, if not supplied targets active device
        """
        params = {"device_id": device_id} if device_id else None
        await self._request("PUT", "/me/player/pause", params=params)

    async def skip_next(self, device_id: Optional[str] = None) -> None:
        """Skip to next track in the user's queue.

        Scopes:
            user-modify-playback-state

        Note:
            Only works for premium users

        Args:
            device_id: Device ID to target, if not supplied targets active device
        """
        params = {"device_id": device_id} if device_id else None
        await self._request("POST", "/me/player/next", params=params)

    async def skip_previous(self, device_id: Optional[str] = None) -> None:
        """Skip to previous track in the user's queue.

        Scopes:
            user-modify-playback-state

        Notes:
            Only works for premium users

        Args:
            device_id: Device ID to target, if not supplied targets active device
        """
        params = {"device_id": device_id} if device_id else None
        await self._request("POST", "/me/player/previous", params=params)

    async def seek_to_position(self, position_ms: int, device_id: Optional[str] = None) -> None:
        """Seek to position in currently playing track.

        Scopes:
            user-modify-playback-state

        Notes:
            Only works for premium users

        Args:
            position_ms: Position in milliseconds to seek to
            device_id: Device ID to target, if not supplied targets active device
        """
        params = {"position_ms": position_ms}
        if device_id:
            params["device_id"] = device_id

        await self._request("PUT", "/me/player/seek", params=params)

    async def set_repeat_mode(self, state: Literal["track", "context", "off"], device_id: Optional[str] = None) -> None:
        """Set repeat mode for playback.

        Scopes:
            user-modify-playback-state

        Notes:
            Only works for premium users

        Args:
            state: Repeat mode to set
            device_id: Device ID to target, if not supplied targets active device
        """
        params = {"state": state}
        if device_id:
            params["device_id"] = device_id

        await self._request("PUT", "/me/player/repeat", params=params)

    async def set_volume(self, volume_percent: int, device_id: Optional[str] = None) -> None:
        """Set volume for user's current playback device.

        Scopes:
            user-modify-playback-state

        Note:
            Only works for premium users

        Args:
            volume_percent: Volume to set (0-100)
            device_id: Device ID to target, if not supplied targets active device
        """
        if not 0 <= volume_percent <= 100:
            raise ValidationError("Volume must be between 0 and 100")

        params = {"volume_percent": volume_percent}
        if device_id:
            params["device_id"] = device_id

        await self._request("PUT", "/me/player/volume", params=params)

    async def set_shuffle(self, state: bool, device_id: Optional[str] = None) -> None:
        """Toggle shuffle on/off for user's playback.

        Scopes:
            user-modify-playback-state

        Notes:
            Only works for premium users

        Args:
            state: Shuffle state to set
            device_id: Device ID to target, if not supplied targets active device
        """
        params = {"state": "true" if state else "false"}
        if device_id:
            params["device_id"] = device_id

        await self._request("PUT", "/me/player/shuffle", params=params)

    async def add_to_queue(self, uri: str, device_id: Optional[str] = None) -> None:
        """Add item to end of user's playback queue.

        Required scopes:
            user-modify-playback-state

        Notes:
            - Only works for premium users

        Args:
            uri: Spotify track/episode URI to add
            device_id: Device ID to target, if not supplied targets active device
        """
        params = {"uri": uri}
        if device_id:
            params["device_id"] = device_id

        await self._request("POST", "/me/player/queue", params=params)

    async def get_playlist(
        self,
        playlist_id: str,
        fields: Optional[str] = None,
        additional_types: Optional[List[Literal["track", "episode"]]] = None,
        market: Optional[str] = None,
    ) -> Playlist:
        """Get Spotify catalog information for a single playlist.

        Notes:
            If neither market or user country are provided, the content is considered
            unavailable for the client.

        Args:
            playlist_id: The Spotify ID of the playlist
            fields: Filters for the query: a comma-separated list of the fields to return
                For example: 'description,uri' or 'tracks.items(added_at,added_by.id)'
            additional_types: A list of item types that your client supports besides the
                default track type. Valid types are: track and episode.
            market: An ISO 3166-1 alpha-2 country code for content availability

        Returns:
            Detailed playlist object
        """
        params = {}
        if fields:
            params["fields"] = fields
        if additional_types:
            params["additional_types"] = ",".join(additional_types)
        if market:
            params["market"] = market

        return await self._request("GET", f"/playlists/{playlist_id}", params=params, response_model=Playlist)

    async def change_playlist_details(
        self,
        playlist_id: str,
        name: Optional[str] = None,
        public: Optional[bool] = None,
        collaborative: Optional[bool] = None,
        description: Optional[str] = None,
    ) -> None:
        """Change a playlist's name and public/private state.

        Scopes:
            playlist-modify-public
            playlist-modify-private

        Notes:
            The user must own the playlist to modify it
            Collaborative can only be set to true on non-public playlists

        Args:
            playlist_id: The Spotify ID of the playlist
            name: The new name for the playlist
            public: The playlist's public/private status:
                true = public, false = private, None = status not relevant
            collaborative: If true, the playlist will become collaborative
            description: Value for playlist description
        """
        if collaborative and public:
            raise ValidationError("Collaborative playlists cannot be public")

        data = {}
        if name is not None:
            data["name"] = name
        if public is not None:
            data["public"] = public
        if collaborative is not None:
            data["collaborative"] = collaborative
        if description is not None:
            data["description"] = description

        await self._request("PUT", f"/playlists/{playlist_id}", json=data)

    async def get_playlist_items(
        self,
        playlist_id: str,
        limit: int = 20,
        offset: int = 0,
        fields: Optional[str] = None,
        additional_types: Optional[List[Literal["track", "episode"]]] = None,
        market: Optional[str] = None,
    ) -> Paging[PlaylistTrack]:
        """Get full details of the items of a playlist owned by a Spotify user.

        Scopes:
            playlist-read-private

        Notes:
            If neither market or user country are provided, the content is considered
            unavailable for the client.

        Args:
            playlist_id: The Spotify ID of the playlist
            limit: Maximum number of items to return (1-50, default: 20)
            offset: Index of the first item to return (default: 0)
            fields: Filters for the query: a comma-separated list of the fields to return
                For example: 'description,uri' or 'tracks.items(added_at,added_by.id)'
            additional_types: List of item types that your client supports besides the
                default track type. Valid types are: track and episode.
            market: An ISO 3166-1 alpha-2 country code for content availability

        Returns:
            Paging object containing playlist tracks
        """
        if not 0 < limit <= 50:
            raise ValidationError("Limit must be between 1 and 50")

        params = {"limit": limit, "offset": offset}

        if market:
            params["market"] = market
        if fields:
            params["fields"] = fields
        if additional_types:
            params["additional_types"] = ",".join(additional_types)

        return await self._request(
            "GET", f"/playlists/{playlist_id}/tracks", params=params, response_model=Paging[PlaylistTrack]
        )

    async def replace_playlist_items(self, playlist_id: str, uris: List[str]) -> str:
        """Replace all items in a playlist with the provided tracks/episodes.

        Scopes:
            playlist-modify-public
            playlist-modify-private

        Notes:
            This operation will overwrite all existing items in the playlist

        Args:
            playlist_id: The Spotify ID of the playlist
            uris: List of Spotify URIs to set (track or episode URIs)
                Maximum of 100 items can be set in one request

        Returns:
            New snapshot ID of the playlist
        """
        if len(uris) > 100:
            raise ValidationError("Maximum of 100 URIs allowed")

        response = await self._request(
            "PUT", f"/playlists/{playlist_id}/tracks", json={"uris": uris}, response_model=PlaylistSnapshotId
        )
        return response.snapshot_id

    async def reorder_playlist_items(
        self,
        playlist_id: str,
        range_start: int,
        insert_before: int,
        range_length: int = 1,
        snapshot_id: Optional[str] = None,
    ) -> str:
        """Reorder items in a playlist.

        Scopes:
            playlist-modify-public
            playlist-modify-private

        Args:
            playlist_id: The Spotify ID of the playlist
            range_start: Position of the first item to be reordered
            insert_before: Position where the items should be inserted
            range_length: Amount of items to be reordered (default: 1)
            snapshot_id: Playlist's snapshot ID to make changes against

        Returns:
            New snapshot ID of the playlist
        """
        data = {
            "range_start": range_start,
            "insert_before": insert_before,
            "range_length": range_length,
        }
        if snapshot_id:
            data["snapshot_id"] = snapshot_id

        response = await self._request(
            "PUT", f"/playlists/{playlist_id}/tracks", json=data, response_model=PlaylistSnapshotId
        )
        return response.snapshot_id

    async def add_playlist_items(self, playlist_id: str, uris: List[str], position: Optional[int] = None) -> str:
        """Add one or more items to a user's playlist.

        Scopes:
            playlist-modify-public
            playlist-modify-private

        Args:
            playlist_id: The Spotify ID of the playlist
            uris: List of Spotify URIs to add (track or episode URIs) (maximum: 100)
            position: Zero-based position to insert the items
                If omitted, items will be appended to the playlist
                Items are added in the order they appear in the uris list

        Returns:
            New snapshot ID of the playlist
        """
        if len(uris) > 100:
            raise ValidationError("Maximum of 100 URIs allowed")

        data = {"uris": uris}
        if position is not None:
            if position < 0:
                raise ValidationError("Position must be non-negative")
            data["position"] = position

        response = await self._request(
            "POST", f"/playlists/{playlist_id}/tracks", json=data, response_model=PlaylistSnapshotId
        )
        return response.snapshot_id

    async def remove_playlist_items(self, playlist_id: str, uris: List[str], snapshot_id: Optional[str] = None) -> str:
        """Remove one or more items from a user's playlist.

        Scopes:
            playlist-modify-public
            playlist-modify-private

        Args:
            playlist_id: The Spotify ID of the playlist
            uris: List of Spotify URIs to remove (track or episode URIs)
                Maximum of 100 items can be removed in one request
            snapshot_id: Playlist's snapshot ID against which to make the changes
                If specified, API will validate items exist before making changes

        Returns:
            New snapshot ID of the playlist
        """
        if len(uris) > 100:
            raise ValidationError("Maximum of 100 URIs allowed")

        tracks = [{"uri": uri} for uri in uris]

        data = {"tracks": tracks}
        if snapshot_id:
            data["snapshot_id"] = snapshot_id

        response = await self._request(
            "DELETE", f"/playlists/{playlist_id}/tracks", json=data, response_model=PlaylistSnapshotId
        )
        return response.snapshot_id

    async def get_current_user_playlists(self, limit: int = 20, offset: int = 0) -> Paging[SimplifiedPlaylist]:
        """Get a list of the playlists owned or followed by the current user.

        Scopes:
            playlist-read-private

        Args:
            limit: Maximum number of playlists to return (1-50, default: 20)
            offset: Index of the first playlist to return (default: 0)
                Maximum offset: 100,000

        Returns:
            Paging object containing simplified playlists
        """
        if not 0 < limit <= 50:
            raise ValidationError("Limit must be between 1 and 50")
        if offset > 100_000:
            raise ValidationError("Maximum offset is 100,000")

        params = {"limit": limit, "offset": offset}

        return await self._request("GET", "/me/playlists", params=params, response_model=Paging[SimplifiedPlaylist])

    async def get_user_playlists(self, user_id: str, limit: int = 20, offset: int = 0) -> Paging[SimplifiedPlaylist]:
        """Get a list of the playlists owned or followed by a Spotify user.

        Scopes:
            playlist-read-private
            playlist-read-collaborative

        Args:
            user_id: The Spotify user ID
            limit: Maximum number of playlists to return (1-50, default: 20)
            offset: Index of the first playlist to return (default: 0)
                Maximum offset: 100,000

        Returns:
            Paging object containing simplified playlists
        """
        if not 0 < limit <= 50:
            raise ValidationError("Limit must be between 1 and 50")
        if offset > 100_000:
            raise ValidationError("Maximum offset is 100,000")

        params = {"limit": limit, "offset": offset}

        return await self._request(
            "GET", f"/users/{user_id}/playlists", params=params, response_model=Paging[SimplifiedPlaylist]
        )

    async def create_playlist(
        self,
        user_id: str,
        name: str,
        public: bool = True,
        collaborative: bool = False,
        description: Optional[str] = None,
    ) -> Playlist:
        """Create a playlist for a Spotify user.

        Scopes:
            playlist-modify-public
            playlist-modify-private

        Notes:
            Users are generally limited to a maximum of 11,000 playlists
            The playlist will be empty until tracks are added

        Args:
            user_id: The Spotify user ID
            name: The name for the new playlist (doesn't need to be unique)
            public: Whether the playlist should be public (default: True)
                If collaborative is True, this will be set to False
            collaborative: Whether the playlist should be collaborative (default: False)
                Note: If True, public will be set to False automatically
            description: Optional description for the playlist

        Returns:
            The newly created playlist object
        """
        # Collaborative playlists must be private
        if collaborative:
            public = False

        data = {"name": name, "public": public, "collaborative": collaborative}
        if description is not None:
            data["description"] = description

        return await self._request("POST", f"/users/{user_id}/playlists", json=data, response_model=Playlist)

    async def get_playlist_cover_image(self, playlist_id: str) -> List[Image]:
        """Get the current image associated with a specific playlist.

        Notes:
            Images are returned in descending size order (largest first)
            The image URLs are temporary and will expire in less than a day

        Args:
            playlist_id: The Spotify ID of the playlist

        Returns:
            List of image objects ordered by size (largest first)
        """
        response = await self._request("GET", f"/playlists/{playlist_id}/images", response_model=ItemList[Image])
        return response.items

    async def add_custom_playlist_cover_image(self, playlist_id: str, image_data_base64: str) -> None:
        """Replace the image used to represent a specific playlist.

        Scopes:
            ugc-image-upload
            playlist-modify-public
            playlist-modify-private

        Notes:
            The image must be a JPEG and the total payload size must be less than 256 KB after base64 decoding

        Args:
            playlist_id: The Spotify ID of the playlist
            image_data_base64: Base64 encoded JPEG image data
                Must be under 256 KB after base64 decoding
        """
        # Validate base64 format
        try:
            # Remove potential data URL prefix
            if "base64," in image_data_base64:
                image_data_base64 = image_data_base64.split("base64,")[1]

            # Check if it's valid base64
            import base64

            image_data = base64.b64decode(image_data_base64)
        except Exception as e:
            raise ValidationError("Invalid base64 image data") from e

        # Check size limit (256 KB)
        if len(image_data) > 256 * 1024:  # 256 KB in bytes
            raise ValidationError("Image data exceeds 256 KB limit")

        await self._request(
            "PUT", f"/playlists/{playlist_id}/images", data=image_data_base64, headers={"Content-Type": "image/jpeg"}
        )

    async def search(
        self,
        q: str,
        types: List[Literal["album", "artist", "playlist", "track", "show", "episode", "audiobook"]],
        limit: int = 20,
        offset: int = 0,
        include_external: Optional[Literal["audio"]] = None,
        market: Optional[str] = None,
    ) -> SearchResults:
        """Search for albums, artists, playlists, tracks, shows, episodes, or audiobooks.

        Notes:
            Audiobooks are only available in US, UK, Canada, Ireland, New Zealand and Australia markets
            The tag:new filter returns albums released in the past two weeks
            The tag:hipster filter returns albums in the lowest 10% popularity

        Args:
            q: Search query string. You can narrow down the search using field filters:
                - album, artist, track, year: For albums, artists and tracks
                - genre: For artists and tracks
                - isrc, track: For tracks only
                - upc, tag:new, tag:hipster: For albums only
            types: List of item types to search across
            limit: Maximum number of results per type (1-50, default: 20)
            offset: Offset of the first result to return (0-1000)
            include_external: If 'audio', signals that client can play external audio
            market: ISO 3166-1 alpha-2 country code for content availability

        Returns:
            Search results containing requested item types
        """
        if not 0 < limit <= 50:
            raise ValidationError("Limit must be between 1 and 50")
        if not 0 <= offset <= 1000:
            raise ValidationError("Offset must be between 0 and 1000")

        params = {"q": q, "type": ",".join(types), "limit": limit, "offset": offset}

        if market:
            params["market"] = market
        if include_external:
            params["include_external"] = include_external

        return await self._request("GET", "/search", params=params, response_model=SearchResults)

    async def get_show(self, show_id: str, market: Optional[str] = None) -> Show:
        """Get Spotify catalog information for a single show.

        Scopes:
            user-read-playback-position

        Notes:
            If neither market nor user country are provided, the content is considered
            unavailable for the client.

        Args:
            show_id: The Spotify ID of the show
            market: An ISO 3166-1 alpha-2 country code for content availability.
                If not provided and user token available, will use user's country.

        Returns:
            Detailed show object including episodes
        """
        params = {}
        if market:
            params["market"] = market

        return await self._request("GET", f"/shows/{show_id}", params=params, response_model=Show)

    async def get_several_shows(self, show_ids: List[str], market: Optional[str] = None) -> List[SimplifiedShow]:
        """Get Spotify catalog information for several shows.

        Notes:
            If neither market nor user country are provided, the content is considered
            unavailable for the client.

        Args:
            show_ids: List of Spotify show IDs (maximum: 50)
            market: An ISO 3166-1 alpha-2 country code for content availability.
                If not provided and user token available, will use user's country.

        Returns:
            List of simplified show objects
        """
        if len(show_ids) > 50:
            raise ValidationError("Maximum of 50 show IDs allowed")

        params = {"ids": ",".join(show_ids)}
        if market:
            params["market"] = market

        response = await self._request("GET", "/shows", params=params, response_model=ItemList[SimplifiedShow])
        return response.items

    async def get_show_episodes(
        self, show_id: str, market: Optional[str] = None, limit: int = 20, offset: int = 0
    ) -> Paging[SimplifiedEpisode]:
        """Get Spotify catalog information about a show's episodes.

        Scopes:
            user-read-playback-position

        Notes:
            If neither market nor user country are provided, the content is considered
            unavailable for the client.

        Args:
            show_id: The Spotify ID of the show
            market: An ISO 3166-1 alpha-2 country code for content availability.
                If not provided and user token available, will use user's country.
            limit: Maximum number of episodes to return (1-50, default: 20)
            offset: Index of the first episode to return (default: 0)

        Returns:
            Paging object containing simplified episode objects
        """
        if not 0 < limit <= 50:
            raise ValidationError("Limit must be between 1 and 50")

        params = {"limit": limit, "offset": offset}
        if market:
            params["market"] = market

        return await self._request(
            "GET", f"/shows/{show_id}/episodes", params=params, response_model=Paging[SimplifiedEpisode]
        )

    async def get_saved_shows(self, limit: int = 20, offset: int = 0) -> Paging[SavedItem[Show]]:
        """Get a list of shows saved in the current user's library.

        Scopes:
            user-library-read

        Args:
            limit: Maximum number of shows to return (1-50, default: 20)
            offset: Index of the first show to return (default: 0)

        Returns:
            Paging object containing saved show objects with timestamps
        """
        if not 0 < limit <= 50:
            raise ValidationError("Limit must be between 1 and 50")

        params = {"limit": limit, "offset": offset}

        return await self._request("GET", "/me/shows", params=params, response_model=Paging[SavedItem[Show]])

    async def save_shows(self, show_ids: List[str]) -> None:
        """Save one or more shows to current user's library.

        Scopes:
            user-library-modify

        Args:
            show_ids: List of Spotify show IDs to save (maximum: 50)
        """
        if len(show_ids) > 50:
            raise ValidationError("Maximum of 50 show IDs allowed")

        await self._request("PUT", "/me/shows", params={"ids": ",".join(show_ids)})

    async def remove_shows(self, show_ids: List[str], market: Optional[str] = None) -> None:
        """Delete one or more shows from current user's library.

        Scopes:
            user-library-modify

        Notes:
            If neither market nor user country are provided, the content is considered unavailable for the client.

        Args:
            show_ids: List of Spotify show IDs to remove (max 50)
            market: An ISO 3166-1 alpha-2 country code for content availability.
                If not provided and user token available, will use user's country.
        """
        if len(show_ids) > 50:
            raise ValidationError("Maximum of 50 show IDs allowed")

        params = {"ids": ",".join(show_ids)}
        if market:
            params["market"] = market

        await self._request("DELETE", "/me/shows", params=params)

    async def check_saved_shows(self, show_ids: List[str]) -> List[bool]:
        """Check if one or more shows are saved in current user's library.

        Scopes:
            user-library-read

        Args:
            show_ids: List of Spotify show IDs to check (maximum: 50)

        Returns:
            List of booleans indicating if each show is saved
            Index matches the order of the input show_ids list
        """
        if len(show_ids) > 50:
            raise ValidationError("Maximum of 50 show IDs allowed")

        response = await self._request(
            "GET", "/me/shows/contains", params={"ids": ",".join(show_ids)}, response_model=BooleanArray
        )
        return response.root

    async def get_track(self, track_id: str, market: Optional[str] = None) -> Track:
        """Get Spotify catalog information for a single track.

        Notes:
            If neither market nor user country are provided, the content is considered
            unavailable for the client.

        Args:
            track_id: The Spotify ID of the track
            market: An ISO 3166-1 alpha-2 country code for content availability.
                If not provided and user token available, will use user's country.

        Returns:
            Detailed track object
        """
        params = {}
        if market:
            params["market"] = market

        return await self._request("GET", f"/tracks/{track_id}", params=params, response_model=Track)

    async def get_several_tracks(self, track_ids: List[str], market: Optional[str] = None) -> List[Track]:
        """Get Spotify catalog information for multiple tracks.

        Notes:
            If neither market nor user country are provided, the content is considered
            unavailable for the client.

        Args:
            track_ids: List of Spotify track IDs (maximum: 50)
            market: An ISO 3166-1 alpha-2 country code for content availability.
                If not provided and user token available, will use user's country.

        Returns:
            List of track objects in the order requested
        """
        if len(track_ids) > 50:
            raise ValidationError("Maximum of 50 track IDs allowed")

        params = {"ids": ",".join(track_ids)}
        if market:
            params["market"] = market

        response = await self._request("GET", "/tracks", params=params, response_model=ItemList[Track])
        return response.items

    async def get_saved_tracks(
        self, limit: int = 20, offset: int = 0, market: Optional[str] = None
    ) -> Paging[SavedItem[Track]]:
        """Get tracks saved in the current user's 'Your Music' library.

        Scopes:
            user-library-read

        Notes:
            If neither market nor user country are provided, the content is considered
            unavailable for the client.

        Args:
            limit: Maximum number of tracks to return (1-50, default: 20)
            offset: Index of the first track to return (default: 0)
            market: An ISO 3166-1 alpha-2 country code for content availability.
                If not provided and user token available, will use user's country.

        Returns:
            Paging object containing saved track objects with timestamps
        """
        if not 0 < limit <= 50:
            raise ValidationError("Limit must be between 1 and 50")

        params = {"limit": limit, "offset": offset}
        if market:
            params["market"] = market

        return await self._request("GET", "/me/tracks", params=params, response_model=Paging[SavedItem[Track]])

    async def save_tracks(self, track_ids: List[str]) -> None:
        """Save tracks to current user's 'Your Music' library.

        Scopes:
            user-library-modify

        Args:
            track_ids: List of Spotify track IDs to save (maximum: 50)
        """
        if len(track_ids) > 50:
            raise ValidationError("Maximum of 50 track IDs allowed")

        await self._request("PUT", "/me/tracks", params={"ids": ",".join(track_ids)})

    async def remove_tracks(self, track_ids: List[str]) -> None:
        """Remove tracks from current user's 'Your Music' library.

        Scopes:
            user-library-modify

        Args:
            track_ids: List of Spotify track IDs to remove (maximum: 50)
        """
        if len(track_ids) > 50:
            raise ValidationError("Maximum of 50 track IDs allowed")

        await self._request("DELETE", "/me/tracks", params={"ids": ",".join(track_ids)})

    async def check_saved_tracks(self, track_ids: List[str]) -> List[bool]:
        """Check if tracks are saved in current user's 'Your Music' library.

        Scopes:
            user-library-read

        Args:
            track_ids: List of Spotify track IDs to check (maximum: 50)

        Returns:
            List of booleans indicating if each track is saved
            Index matches the order of the input track_ids list
        """
        if len(track_ids) > 50:
            raise ValidationError("Maximum of 50 track IDs allowed")

        response = await self._request(
            "GET", "/me/tracks/contains", params={"ids": ",".join(track_ids)}, response_model=BooleanArray
        )
        return response.root

    async def get_current_user(self) -> User:
        """Get detailed profile information about the current user.

        Scopes:
            user-read-private (for country, explicit_content settings, product level)
            user-read-email (for email address)

        Notes:
            Some fields will be None if their required scopes are not authorized

        Returns:
            Detailed user profile object
        """
        return await self._request("GET", "/me", response_model=User)

    async def get_top_items(
        self,
        type: Literal["artists", "tracks"],
        time_range: Literal["long_term", "medium_term", "short_term"] = "medium_term",
        limit: int = 20,
        offset: int = 0,
    ) -> Union[Paging[Artist], Paging[Track]]:
        """Get the current user's top artists or tracks based on calculated affinity.

        Scopes:
            user-top-read

        Args:
            type: The type of items to return ("artists" or "tracks")
            time_range: Time frame for affinity calculation:
                - long_term: calculated from ~1 year of data
                - medium_term: approximately last 6 months
                - short_term: approximately last 4 weeks
            limit: Maximum number of items to return (1-50, default: 20)
            offset: Index of the first item to return (default: 0)

        Returns:
            Paging object containing either artists or tracks, depending on type parameter
        """
        if not 0 < limit <= 50:
            raise ValidationError("Limit must be between 1 and 50")

        params = {"time_range": time_range, "limit": limit, "offset": offset}

        response_model = Paging[Artist] if type == "artists" else Paging[Track]

        return await self._request("GET", f"/me/top/{type}", params=params, response_model=response_model)

    async def get_user(self, user_id: str) -> SimplifiedUser:
        """Get public profile information about a Spotify user.

        Args:
            user_id: The Spotify user ID

        Returns:
            User profile object with public information
        """
        return await self._request("GET", f"/users/{user_id}", response_model=SimplifiedUser)

    async def follow_playlist(self, playlist_id: str, public: bool = True) -> None:
        """Add the current user as a follower of a playlist.

        Scopes:
            playlist-modify-public
            playlist-modify-private

        Args:
            playlist_id: The Spotify ID of the playlist
            public: Whether the playlist should appear in user's public profile
        """
        data = {"public": public} if public is not None else {}

        await self._request("PUT", f"/playlists/{playlist_id}/followers", json=data)

    async def unfollow_playlist(self, playlist_id: str) -> None:
        """Remove the current user as a follower of a playlist.

        Scopes:
            playlist-modify-public
            playlist-modify-private

        Args:
            playlist_id: The Spotify ID of the playlist
        """
        await self._request("DELETE", f"/playlists/{playlist_id}/followers")

    async def get_followed_artists(self, limit: int = 20, after: Optional[str] = None) -> CursorPaging[Artist]:
        """Get the current user's followed artists.

        Scopes:
            user-follow-read

        Args:
            limit: Maximum number of artists to return (1-50, default: 20)
            after: Last artist ID retrieved from previous request
                Used for cursor-based pagination

        Returns:
            Cursor paging object containing artist objects
        """
        if not 0 < limit <= 50:
            raise ValidationError("Limit must be between 1 and 50")

        params = {"type": "artist", "limit": limit}
        if after:
            params["after"] = after

        response = await self._request(
            "GET", "/me/following", params=params, response_model=CursorPagingResponse[CursorPaging[Artist]]
        )
        return response.items

    async def follow(self, type: Literal["artist", "user"], ids: List[str]) -> None:
        """Add the current user as a follower of artists or users.

        Scopes:
            user-follow-modify

        Args:
            type: The type of ID to follow ("artist" or "user")
            ids: List of Spotify IDs to follow (maximum: 50)
        """
        if len(ids) > 50:
            raise ValidationError("Maximum of 50 IDs allowed")

        await self._request("PUT", "/me/following", params={"type": type, "ids": ",".join(ids)})

    async def unfollow(self, type: Literal["artist", "user"], ids: List[str]) -> None:
        """Remove the current user as a follower of artists or users.

        Scopes:
            user-follow-modify

        Args:
            type: The type of ID to unfollow ("artist" or "user")
            ids: List of Spotify IDs to unfollow (maximum: 50)
        """
        if len(ids) > 50:
            raise ValidationError("Maximum of 50 IDs allowed")

        await self._request("DELETE", "/me/following", params={"type": type, "ids": ",".join(ids)})

    async def check_if_following(self, type: Literal["artist", "user"], ids: List[str]) -> List[bool]:
        """Check if the current user is following artists or users.

        Scopes:
            user-follow-read

        Args:
            type: The type of ID to check ("artist" or "user")
            ids: List of Spotify IDs to check (maximum: 50)

        Returns:
            List of booleans indicating if each ID is followed
        """
        if len(ids) > 50:
            raise ValidationError("Maximum of 50 IDs allowed")

        response = await self._request(
            "GET", "/me/following/contains", params={"type": type, "ids": ",".join(ids)}, response_model=BooleanArray
        )
        return response.root

    async def check_if_following_playlist(self, playlist_id: str, ids: List[str]) -> List[bool]:
        """Check if the current user is following a playlist.

        Args:
            playlist_id: The Spotify ID of the playlist
            ids: List of Spotify IDs to check (maximum: 50)

        Returns:
            List of booleans indicating if each ID is following the playlist
        """
        if len(ids) > 50:
            raise ValidationError("Maximum of 50 IDs allowed")

        response = await self._request(
            "GET",
            f"/playlists/{playlist_id}/followers/contains",
            params={"ids": ",".join(ids)},
            response_model=BooleanArray,
        )
        return response.root

    async def _request[T](
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        response_model: Type[T] = None,
        max_retries: int = 3,
    ) -> Optional[T]:
        """Make an authenticated request to the Spotify API and parse the response."""
        retries = 0
        while True:
            try:
                response = await self.client.request(
                    method=method,
                    url=path,
                    params=params,
                    json=json,
                )
                response.raise_for_status()

                if not response.content:
                    return None

                try:
                    response_json = response.json()
                except JSONDecodeError:
                    return None

                return response_model.model_validate(response_json)
            except HTTPError as e:
                print(f"HTTP Error: {e}")
                if e.response:
                    status_code = e.response.status_code
                    error_msg = str(e)
                    if status_code == 401:
                        raise AuthenticationError("Invalid or expired access token") from e
                    elif status_code == 403:
                        raise AuthenticationError(
                            "Insufficient permissions to perform this action. Check your scopes."
                        ) from e
                    elif status_code == 404:
                        raise ResourceNotFoundError("The requested resource was not found") from e
                    elif status_code == 429:
                        if retries >= max_retries:
                            logger.error(f"Max retries ({max_retries}) exceeded for rate-limited request")
                            raise RateLimitError("Rate limit exceeded and max retries reached") from e
                        retry_after = int(e.response.headers.get("Retry-After", "5"))
                        logger.warning(
                            f"Rate limit exceeded. Waiting {retry_after} seconds before retry (attempt {retries + 1}/{max_retries})"
                        )
                        await asyncio.sleep(retry_after)
                        retries += 1
                        continue
                    elif status_code == 400:
                        raise ValidationError("Invalid request parameters") from e
                    else:
                        raise APIError(f"Unexpected API error: {error_msg}", status_code) from e
                raise APIError("Unknown error occurred", 500) from e
