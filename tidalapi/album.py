# -*- coding: utf-8 -*-

# Copyright (C) 2019-2022 morguldir
# Copyright (C) 2014 Thomas Amland
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import copy

import dateutil.parser

import tidalapi

DEFAULT_ALBUM_IMAGE = (
    "https://tidal.com/browse/assets/images/defaultImages/defaultAlbumImage.png"
)


class Album(object):
    """
    Contains information about a TIDAL album.

    If the album is created from a media object, this object will only contain
    the id, name, cover and video cover. TIDAL does this to reduce the network load.

    """

    id = None
    name = None
    cover = None
    video_cover = None

    duration = -1
    available = False
    num_tracks = -1
    num_videos = -1
    num_volumes = -1
    tidal_release_date = None
    release_date = None
    copyright = None
    version = None
    explicit = True
    universal_product_number = -1
    popularity = -1
    user_date_added = None
    audio_quality = None

    artist = None
    artists = None

    def __init__(self, session, album_id):
        self.session = session
        self.requests = session.request
        self.artist = session.artist()
        self.id = album_id
        if album_id:
            self.requests.map_request("albums/%s" % album_id, parse=self.parse)

    def parse(self, json_obj, artist=None, artists=None):
        if artists is None:
            artists = self.session.parse_artists(json_obj["artists"])

        # Sometimes the artist field is not filled, an example is 140196345
        if not "artist" in json_obj:
            artist = artists[0]
        elif artist is None:
            artist = self.session.parse_artist(json_obj["artist"])

        self.id = json_obj["id"]
        self.name = json_obj["title"]
        self.cover = json_obj["cover"]
        self.video_cover = json_obj["videoCover"]

        self.duration = json_obj.get("duration")
        self.available = json_obj.get("streamReady")
        self.num_tracks = json_obj.get("numberOfTracks")
        self.num_videos = json_obj.get("numberOfVideos")
        self.num_volumes = json_obj.get("numberOfVolumes")
        self.copyright = json_obj.get("copyright")
        self.version = json_obj.get("version")
        self.explicit = json_obj.get("explicit")
        self.universal_product_number = json_obj.get("upc")
        self.popularity = json_obj.get("popularity")

        self.artist = artist
        self.artists = artists

        release_date = json_obj.get("releaseDate")
        self.release_date = (
            dateutil.parser.isoparse(release_date) if release_date else None
        )

        tidal_release_date = json_obj.get("streamStartDate")
        self.tidal_release_date = (
            dateutil.parser.isoparse(tidal_release_date) if tidal_release_date else None
        )

        user_date_added = json_obj.get("dateAdded")
        self.user_date_added = (
            dateutil.parser.isoparse(user_date_added) if user_date_added else None
        )
        audio_quality = json_obj.get("audioQuality")
        if audio_quality:
            self.audio_quality = tidalapi.Quality(audio_quality)

        return copy.copy(self)

    @property
    def year(self):
        """
        Convenience function to get the year using :class:`available_release_date`

        :return: An :any:`python:int` containing the year the track was released
        """
        return self.available_release_date.year if self.available_release_date else None

    @property
    def available_release_date(self):
        """
        Get the release date if it's available, otherwise get the day it was released on TIDAL

        :return: A :any:`python:datetime.datetime` object with the release date, or the tidal release date, can be None
        """
        if self.release_date:
            return self.release_date
        if self.tidal_release_date:
            return self.tidal_release_date
        return None

    def tracks(self, limit=None, offset=0):
        """
        Returns the tracks in classes album.

        :param limit: The amount of items you want returned.
        :param offset: The position of the first item you want to include.
        :return: A list of the :class:`Tracks <.Track>` in the album.
        """
        params = {"limit": limit, "offset": offset}
        return self.requests.map_request(
            "albums/%s/tracks" % self.id, params, parse=self.session.parse_track
        )

    def items(self, limit=100, offset=0):
        """
        Gets the first 100 tracks and videos in the album from TIDAL.

        :param offset: The index you want to start retrieving items from
        :return: A list of :class:`Tracks<.Track>` and :class:`Videos`<.Video>`
        """
        params = {"offset": offset, "limit": limit}
        return self.requests.map_request(
            "albums/%s/items" % self.id, params=params, parse=self.session.parse_media
        )

    def image(self, dimensions, default=DEFAULT_ALBUM_IMAGE):
        """
        A url to an album image cover

        :param dimensions: The width and height that you want from the image
        :type dimensions: int
        :return: A url to the image.

        Valid resolutions: 80x80, 160x160, 320x320, 640x640, 1280x1280
        """
        if not self.cover:
            return default

        if dimensions not in [80, 160, 320, 640, 1280]:
            raise ValueError("Invalid resolution {0} x {0}".format(dimensions))

        return self.session.config.image_url % (
            self.cover.replace("-", "/"),
            dimensions,
            dimensions,
        )

    def video(self, dimensions):
        """
        Creates a url to an mp4 video cover for the album.

        Valid resolutions: 80x80, 160x160, 320x320, 640x640, 1280x1280

        :param dimensions: The width an height of the video
        :type dimensions: int
        :return: A url to an mp4 of the video cover.
        """
        if not self.video_cover:
            raise AttributeError("This album does not have a video cover.")

        if dimensions not in [80, 160, 320, 640, 1280]:
            raise ValueError("Invalid resolution {0} x {0}".format(dimensions))

        return self.session.config.video_url % (
            self.video_cover.replace("-", "/"),
            dimensions,
            dimensions,
        )

    def page(self):
        """
        Retrieve the album page as seen on https://listen.tidal.com/album/$id

        :return: A :class:`Page` containing the different categories, e.g. similar artists and albums
        """
        return self.session.page.get("pages/album", params={"albumId": self.id})

    def similar(self):
        """
        Retrieve albums similar to the current one

        :return: A :any:`list` of similar albums
        """
        return self.requests.map_request(
            "albums/%s/similar" % self.id, parse=self.session.parse_album
        )

    def review(self) -> str:
        """
        Retrieve the album review

        :return: A :class:`str` containing the album review, with wimp links
        :raises: :class:`requests.HTTPError` if there isn't a review yet
        """
        # morguldir: TODO: Add parsing of wimplinks?
        return self.requests.request("GET", "albums/%s/review" % self.id).json()["text"]
