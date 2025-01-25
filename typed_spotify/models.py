from datetime import datetime
from typing import List, Optional, Literal, Union, Generic, TypeVar

from pydantic import AliasChoices, BaseModel, RootModel, Field

T = TypeVar("T")


# Base Models
class ExternalUrls(BaseModel):
    spotify: str


class ExternalIds(BaseModel):
    upc: Optional[str] = None
    isrc: Optional[str] = None
    ean: Optional[str] = None


class Image(BaseModel):
    url: str
    width: Optional[int] = None
    height: Optional[int] = None


class Restrictions(BaseModel):
    reason: Literal["market", "product", "explicit"]


class Copyright(BaseModel):
    text: str
    type: str


class Followers(BaseModel):
    total: int
    href: Optional[str] = None


class ResumePoint(BaseModel):
    fully_played: bool
    resume_position_ms: int


class Cursor(BaseModel):
    after: Optional[str] = None
    before: Optional[str] = None


class Cursors(BaseModel):
    after: Optional[str] = None
    before: Optional[str] = None


class Author(BaseModel):
    name: str


class Narrator(BaseModel):
    name: str


# Generic Models
class Paging[T](BaseModel):
    href: str
    items: List[T]
    limit: int
    next: Optional[str] = None
    offset: int
    previous: Optional[str] = None
    total: int


class CursorPaging(BaseModel, Generic[T]):
    href: str
    items: List[T]
    limit: int
    next: Optional[str] = None
    cursors: Cursor
    total: int


class SavedItem[T](BaseModel):
    added_at: datetime
    item: T = Field(validation_alias=AliasChoices("show", "track", "album", "episode", "audiobook"))


class ItemList[T](BaseModel):
    items: List[Optional[T]] = Field(
        validation_alias=AliasChoices(
            "categories",
            "albums",
            "artists",
            "tracks",
            "shows",
            "episodes",
            "audiobooks",
        )
    )


class CursorPagingResponse[T](BaseModel):
    items: CursorPaging[T] = Field(
        validation_alias=AliasChoices(
            "categories",
            "albums",
            "artists",
            "tracks",
            "shows",
            "episodes",
            "audiobooks",
        )
    )


class PagingResponse[T](BaseModel):
    items: Paging[T] = Field(
        validation_alias=AliasChoices(
            "categories",
            "albums",
            "artists",
            "tracks",
            "shows",
            "episodes",
            "audiobooks",
        )
    )


# User Models
class ExplicitContent(BaseModel):
    filter_enabled: bool
    filter_locked: bool


class SimplifiedUser(BaseModel):
    id: str
    uri: str
    href: str
    type: Literal["user"]
    external_urls: ExternalUrls
    followers: Optional[Followers] = None
    display_name: Optional[str] = None


class User(SimplifiedUser):
    country: Optional[str] = None
    email: Optional[str] = None
    explicit_content: Optional[ExplicitContent] = None
    images: List[Image]
    product: Optional[str] = None


# Artist Models
class SimplifiedArtist(BaseModel):
    id: str
    uri: str
    href: str
    type: Literal["artist"]
    name: str
    external_urls: ExternalUrls


class Artist(SimplifiedArtist):
    followers: Followers
    genres: List[str] = Field(default_factory=list)
    images: List[Image]
    popularity: int


# Album Models
class SimplifiedAlbum(BaseModel):
    id: str
    uri: str
    href: str
    type: Literal["album"]
    name: str
    album_type: Literal["album", "single", "compilation"]
    album_group: Optional[Literal["album", "single", "compilation", "appears_on"]] = None
    total_tracks: int
    release_date: str
    release_date_precision: Literal["year", "month", "day"]
    artists: List[SimplifiedArtist]
    images: List[Image]
    external_urls: ExternalUrls
    available_markets: List[str]
    restrictions: Optional[Restrictions] = None


class Album(SimplifiedAlbum):
    external_ids: ExternalIds
    tracks: Paging["SimplifiedTrack"]
    copyrights: List[Copyright]
    label: str
    popularity: int


# Track Models
class SimplifiedTrack(BaseModel):
    id: str
    uri: str
    href: str
    type: Literal["track"]
    name: str
    artists: List[SimplifiedArtist]
    duration_ms: int
    track_number: int
    disc_number: int = 1
    explicit: bool
    external_urls: ExternalUrls
    is_playable: Optional[bool] = None
    is_local: bool = False
    available_markets: List[str]
    restrictions: Optional[Restrictions] = None


class Track(SimplifiedTrack):
    album: SimplifiedAlbum
    external_ids: ExternalIds
    popularity: int


# Playlist Models
class PlaylistTracksRef(BaseModel):
    href: str
    total: int


class PlaylistTrack(BaseModel):
    added_at: Optional[datetime] = None
    added_by: Optional[SimplifiedUser] = None
    is_local: bool = False
    track: Optional[Union[Track, "Episode"]] = None


class PlaylistTrackObject(BaseModel):
    items: List[PlaylistTrack]
    href: str
    limit: int
    next: Optional[str] = None
    offset: int
    previous: Optional[str] = None
    total: int


class SimplifiedPlaylist(BaseModel):
    id: str
    snapshot_id: str
    uri: str
    href: str
    type: Literal["playlist"]
    name: str
    description: Optional[str] = None
    public: Optional[bool] = None
    collaborative: bool = False
    owner: SimplifiedUser
    images: List[Image]
    tracks: PlaylistTracksRef
    external_urls: ExternalUrls


class Playlist(SimplifiedPlaylist):
    followers: Followers
    tracks: PlaylistTrackObject


class PlaylistSnapshotId(BaseModel):
    snapshot_id: str


# Show and Episode Models
class SimplifiedShow(BaseModel):
    id: str
    uri: str
    href: str
    type: Literal["show"]
    name: str
    publisher: str
    description: str
    html_description: str
    media_type: str
    is_externally_hosted: bool
    external_urls: ExternalUrls
    images: List[Image]
    languages: List[str]
    total_episodes: int
    available_markets: List[str]
    copyrights: List[Copyright]
    explicit: bool


class Show(SimplifiedShow):
    episodes: Paging["SimplifiedEpisode"]


class SimplifiedEpisode(BaseModel):
    id: str
    uri: str
    href: str
    type: Literal["episode"]
    name: str
    description: str
    html_description: str
    duration_ms: int
    release_date: str
    release_date_precision: Literal["year", "month", "day"]
    explicit: bool
    is_externally_hosted: bool
    is_playable: bool
    languages: List[str]
    external_urls: ExternalUrls
    images: List[Image]
    resume_point: Optional[ResumePoint] = None
    restrictions: Optional[Restrictions] = None


class Episode(SimplifiedEpisode):
    show: SimplifiedShow


# Audiobook Models
class SimplifiedAudiobook(BaseModel):
    id: str
    uri: str
    href: str
    type: Literal["audiobook"]
    name: str
    authors: List[Author]
    narrators: List[Narrator]
    description: str
    html_description: str
    publisher: str
    explicit: bool
    external_urls: ExternalUrls
    images: List[Image]
    languages: List[str]
    media_type: str
    total_chapters: int
    available_markets: List[str]
    restrictions: Optional[Restrictions] = None
    edition: Optional[str] = None


class Audiobook(SimplifiedAudiobook):
    chapters: Paging["SimplifiedChapter"]
    copyrights: List[Copyright] = Field(default_factory=list)


class SimplifiedChapter(BaseModel):
    id: str
    uri: str
    href: str
    type: Literal["episode"]
    name: str
    description: str
    html_description: str
    chapter_number: int
    duration_ms: int
    explicit: bool
    external_urls: ExternalUrls
    images: List[Image]
    is_playable: bool
    languages: List[str]
    release_date: str
    release_date_precision: Literal["year", "month", "day"]
    resume_point: Optional[ResumePoint] = None
    restrictions: Optional[Restrictions] = None
    available_markets: List[str]


class Chapter(SimplifiedChapter):
    audiobook: SimplifiedAudiobook


# Playback Models
class PlaybackContext(BaseModel):
    type: Literal["artist", "playlist", "album", "show"]
    href: str
    external_urls: ExternalUrls
    uri: str


class Device(BaseModel):
    id: Optional[str] = None
    is_active: bool
    is_private_session: bool
    is_restricted: bool
    name: str
    type: Literal["computer", "smartphone", "speaker"]
    volume_percent: Optional[int] = None
    supports_volume: bool


class PlaybackActions(BaseModel):
    interrupting_playback: Optional[bool] = None
    pausing: Optional[bool] = None
    resuming: Optional[bool] = None
    seeking: Optional[bool] = None
    skipping_next: Optional[bool] = None
    skipping_prev: Optional[bool] = None
    toggling_repeat_context: Optional[bool] = None
    toggling_shuffle: Optional[bool] = None
    toggling_repeat_track: Optional[bool] = None
    transferring_playback: Optional[bool] = None


class PlaybackState(BaseModel):
    device: Optional[Device] = None
    repeat_state: Optional[Literal["off", "track", "context"]] = None
    shuffle_state: Optional[bool] = None
    context: Optional[PlaybackContext] = None
    timestamp: int
    progress_ms: Optional[int] = None
    is_playing: bool
    item: Optional[Union[Track, Episode]] = None
    currently_playing_type: Literal["track", "episode", "ad", "unknown"]
    actions: PlaybackActions


class PlaybackQueue(BaseModel):
    currently_playing: Optional[Union[Track, Episode]] = None
    queue: List[Union[Track, Episode]]


# History Models
class PlayHistory(BaseModel):
    track: Track
    played_at: datetime
    context: Optional[PlaybackContext] = None


class PlayHistoryPage(BaseModel):
    href: str
    limit: int
    next: Optional[str] = None
    cursors: Cursors
    total: int
    items: List[PlayHistory]


# Category Models
class Category(BaseModel):
    id: str
    uri: str
    href: str
    name: str
    icons: List[Image]


# Search Models
class SearchResults(BaseModel):
    tracks: Optional[Paging[Track]] = None
    artists: Optional[Paging[Artist]] = None
    albums: Optional[Paging[SimplifiedAlbum]] = None
    playlists: Optional[Paging[SimplifiedPlaylist]] = None
    shows: Optional[Paging[SimplifiedShow]] = None
    episodes: Optional[Paging[SimplifiedEpisode]] = None
    audiobooks: Optional[Paging[SimplifiedAudiobook]] = None


# Market Models
class Markets(BaseModel):
    markets: List[str]


# Other Models
class BooleanArray(RootModel[List[bool]]):
    """Model for API endpoints that return a root-level array of booleans."""

    pass
