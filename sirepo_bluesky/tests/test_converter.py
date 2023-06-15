import json

import pytest
import yaml

from sirepo_bluesky.utils.json_yaml_converter import dict_to_file, json_to_yaml, yaml_to_json


def test_dict_to_file(tmp_path):
    test_dict = {"a": 1, "b": 2, "c": 3}

    dict_to_file(tmp_path / "test1.json", test_dict)
    with open(tmp_path / "test1.json", "r") as fp:
        assert test_dict == json.load(fp)

    dict_to_file(tmp_path / "test2.json", test_dict, indent=4)
    with open(tmp_path / "test2.json", "r") as fp:
        assert test_dict == json.load(fp)

    dict_to_file(tmp_path / "test.yaml", test_dict)
    with open(tmp_path / "test.yaml", "r") as fp:
        assert test_dict == yaml.safe_load(fp)

    with pytest.raises(RuntimeError):
        dict_to_file("test.json1", test_dict)


def test_json_yaml_converters(tmp_path):
    test_dict = {"a": 1, "b": 2, "c": 3}
    dict_to_file(tmp_path / "test1.json", test_dict)

    json_to_yaml(tmp_path / "test1.json", tmp_path / "test.yaml")
    with open(tmp_path / "test.yaml", "r") as fp:
        assert test_dict == yaml.safe_load(fp)

    yaml_to_json(tmp_path / "test.yaml", tmp_path / "test2.json")
    with open(tmp_path / "test2.json", "r") as fp:
        assert test_dict == json.load(fp)

    yaml_to_json(tmp_path / "test.yaml", tmp_path / "test3.json", indent=4)
    with open(tmp_path / "test3.json", "r") as fp:
        assert test_dict == json.load(fp)
