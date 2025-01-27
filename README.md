# typed-spotify

An async and typed Spotify API client for Python.

Note: This is a work in progress. Not all endpoints are tested.

## Example

```python
import time
import os
from typed_spotify.client import SpotifyClient
from typed_spotify.auth import SpotifyAuth


async def main():
    auth = SpotifyAuth(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        scope=["user-read-private", "user-read-email"],
        callback_port=8080,
    )

    client = SpotifyClient(auth=auth)

    response = await client.get_current_user()
    print(response)

if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
```