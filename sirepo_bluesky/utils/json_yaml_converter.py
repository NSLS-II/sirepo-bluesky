import argparse
import json
import os
from enum import Enum

import yaml


class Filetype(Enum):
    JSON = 1
    YAML = 2


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


def cli_converter():
    parser = argparse.ArgumentParser(description="Converts from .json to .yaml/.yml and vice versa")
    parser.add_argument("-i", "--input-file", dest="input_file", help="The file to be converted")
    parser.add_argument("-o", "--output-file", dest="output_file", help="The target file after conversion")
    parser.add_argument(
        "--indent", default=2, type=int, dest="indent", help="The indentation for .json files, default is 2"
    )
    args = parser.parse_args()
    if not (args.input_file and args.output_file):
        parser.error("Input_file and/or output_file is not specified")
    filetype_input = get_file_type(args.input_file)
    filetype_output = get_file_type(args.output_file)
    if filetype_input == Filetype.JSON.value and filetype_output == Filetype.YAML.value:
        json_to_yaml(args.input_file, args.output_file)
    elif filetype_input == Filetype.YAML.value and filetype_output == Filetype.JSON.value:
        yaml_to_json(args.input_file, args.output_file, indent=args.indent)
    else:
        raise RuntimeError(
            "Invalid file type: input must be .json or .yaml/.yml and output must be the opposite type"
        )


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


def dict_to_file(filename, dict, indent=2, **kwargs):
    """
    Converts a dict into a .json, .yaml, or .yml file.

    Parameters
    ----------
    fp : str
            Filepath of new file.
    dict : dict
            Dictionary to be converted.
    """
    filetype = get_file_type(filename)
    if filetype == Filetype.JSON.value:
        with open(filename, "x") as jsonfile:
            json.dump(dict, jsonfile, indent=indent, **kwargs)
    elif filetype == Filetype.YAML.value:
        with open(filename, "x") as yamlfile:
            yaml.dump(dict, yamlfile, **kwargs)
    else:
        raise RuntimeError("Invalid file type: must be .json or .yaml")


def get_file_type(filename):
    filetype = os.path.splitext(filename)[-1]
    if filetype == ".json":
        return Filetype.JSON.value
    elif filetype == ".yaml" or filetype == ".yml":
        return Filetype.YAML.value
    else:
        return -1
