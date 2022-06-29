# Copyright 2022 AI Singapore
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import List
from pathlib import Path

import os
import pytest
import time

from peekingduck.player.playlist import PlayList


def get_files(path: Path) -> List[str]:
    files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
    return files


def read_file(path: Path) -> str:
    with open(path, "r") as file:
        contents = file.read()

    return contents


def print_file(path: Path) -> None:
    print(f"-- file: {path}")
    contents = read_file(path)
    lines = contents.split("\n")
    print(f"-- contents: {len(contents)} --")
    for i, line in enumerate(lines):
        print(f"{i} -> {line}")
    print("----")


@pytest.mark.usefixtures("tmp_dir")
class TestPlayList:
    def test_playlist_debug(self):
        print("---")
        home_path = Path.cwd()
        print(f"home_path={home_path}")

        pipeline_1 = home_path / "src" / "pkd_pipeline1.yml"
        pipeline_2 = home_path / "src" / "pkd_pipeline2.yml"
        pipeline_3 = home_path / "src" / "pkd_pipeline3.yml"

        playlist_a = PlayList(home_path)

        print(f"Playlist A:\n", playlist_a)
        files = get_files(home_path / ".peekingduck")
        print(f"files={files}")

        playlist_a.add_pipeline(pipeline_1)
        playlist_a.save_playlist_file()

        files = get_files(home_path / ".peekingduck")
        print(f"files={files}")

        print_file(playlist_a._playlist_path)

        playlist_a.add_pipeline(pipeline_2)
        playlist_a.add_pipeline(pipeline_3)
        playlist_a.save_playlist_file()

        print_file(playlist_a._playlist_path)

        print(f"Playlist A:\n{playlist_a}")

        playlist_b = PlayList(home_path)
        print(f"Playlist B:\n{playlist_b}")

        # diff objects, same contents
        assert playlist_a != playlist_b
        set_a = set(playlist_a)
        set_b = set(playlist_b)
        print(f"Set A:\n{set_a}")
        print(f"Set B:\n{set_b}")
        assert set_a == set_b

    def test_playlist_add_one_pipeline(self):
        print("---")
        home_path = Path.cwd()
        print(f"home_path={home_path}")
        playlist = PlayList(home_path)

        pipeline_1 = home_path / "src" / "pkd_pipeline1.yml"

        assert pipeline_1 not in playlist
        playlist.add_pipeline(pipeline_1)
        assert pipeline_1 in playlist

    def test_playlist_add_duplicate_pipeline(self):
        print("---")
        home_path = Path.cwd()
        print(f"home_path={home_path}")
        playlist = PlayList(home_path)
        pipeline_1 = home_path / "src" / "pkd_pipeline1.yml"

        playlist.add_pipeline(pipeline_1)
        len_prior = len(playlist)

        playlist.add_pipeline(pipeline_1)
        len_after = len(playlist)
        # no change in playlist after adding duplicate pipeline
        assert len_prior == len_after

    def test_playlist_delete_one_pipeline(self):
        print("---")
        home_path = Path.cwd()
        print(f"home_path={home_path}")
        playlist = PlayList(home_path)

        pipeline_1 = home_path / "src" / "pkd_pipeline1.yml"

        playlist.add_pipeline(pipeline_1)
        assert pipeline_1 in playlist
        # print(f"Playlist after add 1:\n{playlist}")

        playlist.delete_pipeline(pipeline_1)
        assert pipeline_1 not in playlist
        # print(f"Playlist after delete 1:\n{playlist}")

    def test_playlist_delete_non_existent_pipeline(self):
        print("---")
        home_path = Path.cwd()
        print(f"home_path={home_path}")
        playlist = PlayList(home_path)

        pipeline_1 = home_path / "src" / "pkd_pipeline1.yml"
        pipeline_2 = home_path / "src" / "pkd_pipeline2.yml"

        playlist.add_pipeline(pipeline_1)
        len_prior = len(playlist)

        playlist.delete_pipeline(pipeline_2)
        len_after = len(playlist)
        # no change in playlist after deleting non-existent pipeline
        assert len_prior == len_after

    def test_playlist_add_and_delete_pipelines(self):
        print("---")
        home_path = Path.cwd()
        print(f"home_path={home_path}")
        playlist = PlayList(home_path)

        pipeline_1 = home_path / "src" / "pkd_pipeline1.yml"
        pipeline_2 = home_path / "src" / "pkd_pipeline2.yml"
        pipeline_3 = home_path / "src" / "pkd_pipeline3.yml"

        assert pipeline_1 not in playlist

        playlist.add_pipeline(pipeline_1)
        playlist.add_pipeline(pipeline_2)
        playlist.add_pipeline(pipeline_3)

        print(f"Playlist after add 1,2,3:\n{playlist}")
        assert pipeline_3 in playlist
        assert pipeline_2 in playlist
        assert pipeline_1 in playlist

        playlist.delete_pipeline(pipeline_1)
        print(f"Playlist after delete 1:\n{playlist}")
        assert pipeline_1 not in playlist
        assert pipeline_2 in playlist
        assert pipeline_3 in playlist

        playlist.delete_pipeline(pipeline_3)
        print(f"Playlist after delete 3:\n{playlist}")
        assert pipeline_1 not in playlist
        assert pipeline_2 in playlist
        assert pipeline_3 not in playlist

    def test_playlist_iteration(self):
        print("---")
        home_path = Path.cwd()
        print(f"home_path={home_path}")
        playlist = PlayList(home_path)

        pipeline_1 = home_path / "src" / "pkd_pipeline1.yml"
        pipeline_2 = home_path / "src" / "pkd_pipeline2.yml"
        pipeline_3 = home_path / "src" / "pkd_pipeline3.yml"
        pipeline_4 = home_path / "src" / "pkd_pipeline4.yml"

        playlist.add_pipeline(pipeline_3)
        playlist.add_pipeline(pipeline_1)
        playlist.add_pipeline(pipeline_4)
        playlist.add_pipeline(pipeline_2)

        for i, pipeline in enumerate(playlist):
            print(f"{i} {pipeline}")

    def test_playlist_verify_files(self):
        print("---")
        home_path = Path.cwd()
        print(f"home_path={home_path}")

        pipeline_1 = home_path / "src" / "pkd_pipeline1.yml"
        pipeline_2 = home_path / "src" / "pkd_pipeline2.yml"
        pipeline_3 = home_path / "src" / "pkd_pipeline3.yml"

        # create files
        Path(home_path / "src").mkdir()
        Path(pipeline_1).touch()
        time.sleep(1)
        Path(pipeline_2).touch()
        time.sleep(2)
        Path(pipeline_3).touch()

        playlist_a = PlayList(home_path)
        playlist_a.add_pipeline(pipeline_1)
        playlist_a.add_pipeline(pipeline_2)
        playlist_a.add_pipeline(pipeline_3)
        print(f"Playlist A:\n{playlist_a}")
        playlist_a.save_playlist_file()

        playlist_b = PlayList(home_path)
        print(f"Playlist B:\n{playlist_b}")

        # diff objects, same contents
        assert playlist_a != playlist_b
        assert set(playlist_a) == set(playlist_b)
