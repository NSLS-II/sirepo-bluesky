import json
import os
import subprocess
from pprint import pprint

import pytest
import yaml

from sirepo_bluesky.utils.json_yaml_converter import dict_to_file, json_to_yaml, yaml_to_json


def test_dict_to_file(tmp_path):
    test_dict = {"a": 1, "b": 2, "c": 3}

    dict_to_file(test_dict, tmp_path / "test1.json")
    with open(tmp_path / "test1.json", "r") as fp:
        assert test_dict == json.load(fp)

    dict_to_file(test_dict, tmp_path / "test2.json", indent=4)
    with open(tmp_path / "test2.json", "r") as fp:
        assert test_dict == json.load(fp)

    dict_to_file(test_dict, tmp_path / "test.yaml")
    with open(tmp_path / "test.yaml", "r") as fp:
        assert test_dict == yaml.safe_load(fp)

    with pytest.raises(ValueError):
        dict_to_file(test_dict, "test.jpeg")

    test_dict = {"a": 1, "b": 2, "c": 4}

    with pytest.raises(FileExistsError):
        dict_to_file(test_dict, tmp_path / "test2.json")

    dict_to_file(test_dict, tmp_path / "test2.json", openmode="w")
    with open(tmp_path / "test2.json", "r") as fp:
        assert test_dict == json.load(fp)


def test_json_yaml_converters(tmp_path):
    test_dict = {"a": 1, "b": 2, "c": 3}
    dict_to_file(test_dict, tmp_path / "test1.json")

    json_to_yaml(tmp_path / "test1.json", tmp_path / "test.yaml")
    with open(tmp_path / "test.yaml", "r") as fp:
        assert test_dict == yaml.safe_load(fp)

    yaml_to_json(tmp_path / "test.yaml", tmp_path / "test2.json")
    with open(tmp_path / "test2.json", "r") as fp:
        assert test_dict == json.load(fp)

    yaml_to_json(tmp_path / "test.yaml", tmp_path / "test3.json", indent=4)
    with open(tmp_path / "test3.json", "r") as fp:
        assert test_dict == json.load(fp)


@pytest.mark.docker
def test_dict_to_file_from_simulation(tmp_path, shadow_tes_simulation):
    # Sirepo must be running for this test to pass, deselect with '-m "not docker"'
    test_dict = shadow_tes_simulation.data

    dict_to_file(test_dict, tmp_path / "test1.json")
    with open(tmp_path / "test1.json", "r") as fp:
        assert test_dict == json.load(fp)

    dict_to_file(test_dict, tmp_path / "test2.json", indent=4)
    with open(tmp_path / "test2.json", "r") as fp:
        assert test_dict == json.load(fp)

    dict_to_file(test_dict, tmp_path / "test.yaml")
    with open(tmp_path / "test.yaml", "r") as fp:
        assert test_dict == yaml.safe_load(fp)

    pprint(test_dict)


def test_cli_converter(tmp_path):
    test_dict = {"a": 1, "b": 2, "c": 3}

    dict_to_file(test_dict, tmp_path / "test1.json")

    assert os.path.isfile(tmp_path / "test1.json")

    subprocess.run(
        f"json-yaml-converter -i {tmp_path / 'test1.json'} -o {tmp_path / 'test.yaml'} -v".split(), check=True
    )

    assert os.path.isfile(tmp_path / "test.yaml")

    with open(str(tmp_path / "test.yaml"), "r") as fp:
        assert test_dict == yaml.safe_load(fp)

    subprocess.run(
        f"json-yaml-converter -i {tmp_path / 'test.yaml'} -o {tmp_path / 'test2.json'} -v".split(), check=True
    )
    with open(str(tmp_path / "test2.json"), "r") as fp:
        assert test_dict == yaml.safe_load(fp)
