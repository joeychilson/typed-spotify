from importlib.metadata import version

from typed_spotify.auth import FileTokenStorage, MemoryTokenStorage, SpotifyAuth, Token, TokenStorage
from typed_spotify.client import SpotifyClient
from typed_spotify.exceptions import (
    APIError,
    AuthenticationError,
    RateLimitError,
    ResourceNotFoundError,
    SpotifyError,
    ValidationError,
)
from typed_spotify.models import (
    # Base Models
    ExternalUrls,
    ExternalIds,
    Image,
    Restrictions,
    Copyright,
    Followers,
    ResumePoint,
    Cursor,
    Cursors,
    Author,
    Narrator,
    # Generic Models
    Paging,
    CursorPaging,
    SavedItem,
    ItemList,
    CursorPagingResponse,
    PagingResponse,
    # User Models
    ExplicitContent,
    SimplifiedUser,
    User,
    # Artist Models
    SimplifiedArtist,
    Artist,
    # Album Models
    SimplifiedAlbum,
    Album,
    # Track Models
    SimplifiedTrack,
    Track,
    # Playlist Models
    PlaylistTracksRef,
    PlaylistTrack,
    SimplifiedPlaylist,
    Playlist,
    PlaylistSnapshotId,
    # Show and Episode Models
    SimplifiedShow,
    Show,
    SimplifiedEpisode,
    Episode,
    # Audiobook Models
    SimplifiedAudiobook,
    Audiobook,
    SimplifiedChapter,
    Chapter,
    # Playback Models
    PlaybackContext,
    Device,
    PlaybackActions,
    PlaybackState,
    PlaybackQueue,
    # History Models
    PlayHistory,
    # Category Models
    Category,
    # Search Models
    SearchResults,
    # Market Models
    Markets,
    # Other Models
    BooleanArray,
)

__version__ = version("typed-spotify")
__all__ = [
    # Auth
    "FileTokenStorage",
    "MemoryTokenStorage",
    "SpotifyAuth",
    "Token",
    "TokenStorage",
    # Client
    "SpotifyClient",
    # Exceptions
    "APIError",
    "AuthenticationError",
    "RateLimitError",
    "ResourceNotFoundError",
    "SpotifyError",
    "ValidationError",
    # Base Models
    "ExternalUrls",
    "ExternalIds",
    "Image",
    "Restrictions",
    "Copyright",
    "Followers",
    "ResumePoint",
    "Cursor",
    "Cursors",
    "Author",
    "Narrator",
    # Generic Models
    "Paging",
    "CursorPaging",
    "SavedItem",
    "ItemList",
    "CursorPagingResponse",
    "PagingResponse",
    # User Models
    "ExplicitContent",
    "SimplifiedUser",
    "User",
    # Artist Models
    "SimplifiedArtist",
    "Artist",
    # Album Models
    "SimplifiedAlbum",
    "Album",
    # Track Models
    "SimplifiedTrack",
    "Track",
    # Playlist Models
    "PlaylistTracksRef",
    "PlaylistTrack",
    "SimplifiedPlaylist",
    "Playlist",
    "PlaylistSnapshotId",
    # Show and Episode Models
    "SimplifiedShow",
    "Show",
    "SimplifiedEpisode",
    "Episode",
    # Audiobook Models
    "SimplifiedAudiobook",
    "Audiobook",
    "SimplifiedChapter",
    "Chapter",
    # Playback Models
    "PlaybackContext",
    "Device",
    "PlaybackActions",
    "PlaybackState",
    "PlaybackQueue",
    # History Models
    "PlayHistory",
    # Category Models
    "Category",
    # Search Models
    "SearchResults",
    # Market Models
    "Markets",
    # Other Models
    "BooleanArray",
]
