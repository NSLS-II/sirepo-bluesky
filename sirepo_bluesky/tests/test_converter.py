import pytest

from sirepo_bluesky.utils.json_yaml_converter import dict_to_file, json_to_yaml, yaml_to_json


def test_converter(tmp_path):
    test_dict = {"a": 1, "b": 2, "c": 3}
    dict_to_file(tmp_path / "test1.json", test_dict)
    dict_to_file(tmp_path / "test2.json", test_dict, indent=4)
    dict_to_file(tmp_path / "test.yaml", test_dict)
    with pytest.raises(RuntimeError):
        dict_to_file("test.json1", test_dict)

    json_to_yaml(tmp_path / "test1.json", tmp_path / "test1.yaml")

    yaml_to_json(tmp_path / "test.yaml", tmp_path / "test1.json")
    yaml_to_json(tmp_path / "test.yaml", tmp_path / "test2.json", indent=4)
