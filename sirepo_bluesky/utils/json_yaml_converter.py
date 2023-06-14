import json
import os

import yaml


def json_to_yaml(json_fp, yaml_fp, **kwargs):
    """
    Converts a .json file into a .yaml or .yml file.

    Parameters
    ----------
    json_fp : str
            Filepath of .json file.
    yaml_fp : str
            Filepath of new .yaml or .yml file.
    kwargs : dict
    """
    with open(json_fp, "r") as fp:
        data = json.load(fp)
    with open(yaml_fp, "w") as fp:
        yaml.dump(data, fp, **kwargs)


def yaml_to_json(yaml_fp, json_fp, indent=2, **kwargs):
    """
    Converts a .yaml or .yml file into a .json file.

    Parameters
    ----------
    yaml_fp : str
            Filepath of new .yaml or .yml file.
    json_fp : str
            Filepath of .json file.
    kwargs : dict
    """
    with open(yaml_fp, "r") as fp:
        data = yaml.safe_load(fp)
    with open(json_fp, "w") as fp:
        json.dump(data, fp, indent=indent, **kwargs)


def dict_to_file(fp, dict, indent=2, **kwargs):
    """
    Converts a dict into a .json, .yaml, or .yml file.

    Parameters
    ----------
    fp : str
            Filepath of new file.
    dict : dict
            Dictionary to be converted.
    """
    filetype = os.path.splitext(fp)[-1]
    if filetype == ".json":
        with open(fp, "x") as jsonfile:
            json.dump(dict, jsonfile, indent=indent, **kwargs)
    elif filetype == ".yaml" or filetype == ".yml":
        with open(fp, "x") as yamlfile:
            yaml.dump(dict, yamlfile, **kwargs)
    else:
        raise RuntimeError("Invalid file type: must be .json or .yaml")
