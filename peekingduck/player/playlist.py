# Copyright 2022 AI Singapore
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Implements the PeekingDuck Pipeline PlayList class"""

from typing import List
from pathlib import Path
import logging
import yaml


# Globals
PKD_CONFIG_DIR = ".peekingduck"
PKD_PLAYLIST_FILE = "playlist.yaml"


class PlayList:
    """Implements the Pipeline PlayList class
    A playlist is a collection of pipeline URLs
    """

    # Class variable: only one instance; multiple playlist files not supported
    pipeline_list: List[str] = []

    def __init__(self, home_path: str) -> None:
        self.logger = logging.getLogger(__name__)
        # Construct path to ~user_home/.peekingduck/playlist.yaml
        self.playlist_path = Path(home_path) / PKD_CONFIG_DIR / PKD_PLAYLIST_FILE

    def __getitem__(self, i: int) -> str:
        pipeline_list = PlayList.pipeline_list

        if 0 <= i < len(pipeline_list):
            return pipeline_list[i]

        k = len(pipeline_list)
        self.logger.error(
            f"Error getting pipeline[{i}]: "
            f"List has {k} pipelines, only [0] to [{k-1}] supported."
        )
        return ""

    def __setitem__(self, i: int, value: str) -> None:
        pipeline_list = PlayList.pipeline_list

        if 0 <= i < len(pipeline_list):
            pipeline_list[i] = value
        else:
            k: int = len(pipeline_list)
            self.logger.error(
                f"Error setting pipeline[{i}]: "
                f"List has {k} pipelines, only [0] to [{k-1}] supported."
            )

    def read_playlist_file(self) -> List[str]:
        """Read playlist file

        Returns:
            List[str]: contents of playlist file
        """
        if not Path.exists(self.playlist_path):
            return []

        playlist = yaml.safe_load(self.playlist_path)
        return playlist

    def save_playlist_file(self) -> None:
        """Save playlist file"""
        playlist_map = {"playlist": PlayList.pipeline_list}
        with open(self.playlist_path, "w", encoding="utf8") as _:
            yaml.dump(playlist_map)
