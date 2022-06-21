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

from typing import List, Union
from datetime import datetime
from pathlib import Path
import logging
import yaml


# Globals
PKD_CONFIG_DIR = ".peekingduck"
PKD_PLAYLIST_FILE = "playlist.yaml"
PKD_PLAYLIST_HEADER = ["pipeline", "status", "datetime"]


class PipelineStats:
    """Implements the Pipeline Stats class to store pipeline-related information."""

    def __init__(self, pipeline: Path, exist: bool, mod_datetime: float) -> None:
        self._pipeline = pipeline
        self._exist = exist
        self._mod_datetime = mod_datetime
        self._headers = PKD_PLAYLIST_HEADER

    def __str__(self) -> str:
        return self._pipeline.name

    @property
    def exist(self) -> bool:
        return self._exist

    @property
    def mod_datetime(self) -> str:
        return datetime.fromtimestamp(self._mod_datetime).strftime("%Y-%m-%d-%H:%M:%S")

    @property
    def pipeline(self) -> str:
        return str(self._pipeline)

    @property
    def headers(self) -> List[str]:
        return self._headers


class PlayList:
    """Implements the Pipeline PlayList class
    A playlist is a collection of pipeline URLs.
    Supported operations:
    - init playlist with pipelines      O(N)
    - add pipeline to end of playlist   O(1)
    - remove pipeline from playlist     O(N)
    - access playlist[i]                O(1)
    - update playlist[i]                O(1)
    - check pipeline in playlist        O(1)
    - load and save
    """

    def __init__(self, home_path: str) -> None:
        self.logger = logging.getLogger(__name__)
        # Construct path to ~user_home/.peekingduck/playlist.yaml
        self.playlist_dir = Path(home_path) / PKD_CONFIG_DIR
        self.playlist_dir.mkdir(exist_ok=True)
        self.playlist_path = self.playlist_dir / PKD_PLAYLIST_FILE
        self.logger.info(f"playlist_path={self.playlist_path}")
        self.load_playlist_file()

    def __iter__(self):
        self._iter_idx = -1
        return self

    def __next__(self):
        self._iter_idx += 1
        if self._iter_idx < len(self._pipeline_list):
            return self._pipeline_list[self._iter_idx]
            # pipeline = self._pipeline_list[self._iter_idx]
            # return self._pipeline_stats[pipeline]
        raise StopIteration

    def __getitem__(self, i: int) -> str:
        pipeline_list = self._pipeline_list

        if 0 <= i < len(pipeline_list):
            return pipeline_list[i]
            # return self._pipeline_stats[pipeline_list[i]]

        k = len(pipeline_list)
        raise ValueError(
            f"Error getting pipeline[{i}]: "
            f"List has {k} pipelines, only [0] to [{k-1}] supported."
        )

    def __setitem__(self, i: int, value: str) -> None:
        pipeline_list = self._pipeline_list

        if 0 <= i < len(pipeline_list):
            self._pipeline_stats.pop(pipeline_list[i])  # remove old item
            pipeline_list[i] = value  # add and update new item
            self._pipeline_stats[value] = self._make_pipeline_stats(value)
        else:
            k: int = len(pipeline_list)
            raise ValueError(
                f"Error setting pipeline[{i}]: "
                f"List has {k} pipelines, only [0] to [{k-1}] supported."
            )

    def __contains__(self, item):
        res = str(item) in self._pipeline_stats
        # print(f"contains: item={type(item)} {item}, res={res}")
        return res

    def __str__(self):
        res = "\n".join([f"{i} -> {k}" for i, k in enumerate(self._pipeline_list)])
        return res

    def get_stats(self, pipeline: str) -> PipelineStats:
        return self._pipeline_stats[pipeline]

    def add_pipeline(self, pipeline_path: Union[Path, str]) -> None:
        """Add pipeline yaml file to playlist

        Args:
            pipeline_path (Union[Path, str]): path of yaml file to add
        """
        pipeline_str = str(pipeline_path)
        if pipeline_path in self:
            raise ValueError(f"Error adding existing {pipeline_path}")
        # add new pipeline and stats
        self._pipeline_list.append(pipeline_str)
        self._pipeline_stats[pipeline_str] = self._make_pipeline_stats(pipeline_str)

    def remove_pipeline(self, pipeline_path: Union[Path, str]) -> None:
        """Remove pipeline yaml file from playlist

        Args:
            pipeline_path (Union[Path, str]): path of yaml file to remove
        """
        pipeline_str = str(pipeline_path)
        if pipeline_path not in self:
            raise ValueError(f"Error removing non-existent {pipeline_path}")
        # remove old pipeline and stats
        self._pipeline_list.remove(pipeline_str)
        self._pipeline_stats.pop(pipeline_str)

    def load_playlist_file(self) -> None:
        """Load playlist file"""
        pipelines = self._read_playlist_file()
        self._pipeline_list = pipelines
        self._verify_pipeline_files()

    def save_playlist_file(self) -> None:
        """Save playlist file"""
        playlist = {"playlist": self._pipeline_list}
        self.logger.info(f"playlist_map={playlist}")
        with open(self.playlist_path, "w", encoding="utf8") as file:
            yaml.dump(playlist, file)

    def _read_playlist_file(self) -> List[str]:
        """Read contents of playlist file, if any

        Returns:
            List[str]: contents of playlist file, a list of pipelines
        """
        if not Path.exists(self.playlist_path):
            return []

        with open(self.playlist_path, "r") as file:
            playlist = yaml.safe_load(file)

        return playlist["playlist"]

    def _verify_pipeline_files(self) -> None:
        self.logger.info(f"pipelines={self._pipeline_list}")
        self._pipeline_stats = dict.fromkeys(self._pipeline_list, None)
        assert len(self._pipeline_stats.keys()) == len(self._pipeline_list)

        for pipeline in self._pipeline_list:
            self._pipeline_stats[pipeline] = self._make_pipeline_stats(pipeline)

        self.logger.info(f"stats={self._pipeline_stats}")

    def _make_pipeline_stats(self, pipeline: str) -> PipelineStats:
        pipeline_path = Path(pipeline)
        file_exist = False  # file exist flag
        mod_datetime = None  # last modified date/time
        if pipeline_path.exists():
            file_exist = True
            mod_datetime = pipeline_path.stat().st_mtime
            # mod_datetime = datetime.fromtimestamp(mod_time).strftime(
            #     "%Y-%m-%d-%H:%M:%S"
            # )

        # self._pipeline_stats[pipeline] = {
        #     "exist": file_exist,
        #     "mtime": mod_datetime,
        # }

        return PipelineStats(pipeline_path, file_exist, mod_datetime)
