import argparse
import json
import os
from enum import Enum

import yaml


class Filetype(Enum):
    JSON = 1
    YAML = 2


def json_to_yaml(json_fp, yaml_fp, openmode="x", **kwargs):
    """
    Converts a .json file into a .yaml or .yml file.

    Parameters
    ----------
    json_fp : str
        Filepath of .json file.
    yaml_fp : str
        Filepath of new .yaml or .yml file.
    openmode : str
        Mode to be passed to open. Set to "x" by default to avoid overwriting files.
    kwargs : dict
        Will be passed to yaml.dump.
    """
    with open(json_fp, "r") as fp:
        data = json.load(fp)
    with open(yaml_fp, mode=openmode) as fp:
        yaml.dump(data, fp, **kwargs)


def yaml_to_json(yaml_fp, json_fp, indent=2, openmode="x", **kwargs):
    """
    Converts a .yaml or .yml file into a .json file.

    Parameters
    ----------
    yaml_fp : str
        Filepath of new .yaml or .yml file.
    json_fp : str
        Filepath of .json file.
    indent : int
        Indentation of .json file, default is 2.
    openmode : str
        Mode to be passed to open. Set to "x" by default to avoid overwriting files.
    kwargs : dict
        Will be passed to json.dump.
    """
    with open(yaml_fp, "r") as fp:
        data = yaml.safe_load(fp)
    with open(json_fp, mode=openmode) as fp:
        json.dump(data, fp, indent=indent, **kwargs)


def dict_to_file(dict, filename, indent=2, openmode="x", **kwargs):
    """
    Converts a dict into a .json, .yaml, or .yml file.

    Parameters
    ----------
    dict : dict
        Dictionary to be converted.
    filename : str
        Filepath of new file.
    indent : int
        Indentation of .json file to be created, default is 2.
    openmode : str
        Mode to be passed to open. Set to "x" by default to avoid overwriting files.
    kwargs : dict
        Will be passed to json.dump or yaml.dump.
    """
    filetype = get_file_type(filename)
    if filetype == Filetype.JSON:
        with open(filename, mode=openmode) as jsonfile:
            json.dump(dict, jsonfile, indent=indent, **kwargs)
    elif filetype == Filetype.YAML:
        with open(filename, mode=openmode) as yamlfile:
            yaml.dump(dict, yamlfile, **kwargs)
    else:
        raise RuntimeError("Invalid file type: must be .json or .yaml")


def cli_converter():
    # Uses command json-yaml-converter on command line
    parser = argparse.ArgumentParser(description="Converts from .json to .yaml/.yml and vice versa")
    parser.add_argument("-i", "--input-file", dest="input_file", help="The file to be converted")
    parser.add_argument("-o", "--output-file", dest="output_file", help="The target file after conversion")
    parser.add_argument(
        "--indent", default=2, type=int, dest="indent", help="The indentation for .json files, default is 2"
    )
    parser.add_argument(
        "-v", "--verbose", dest="verbose", action="store_true", help="Gives more information when running"
    )
    args = parser.parse_args()
    if args.verbose:
        print(f"\n{args.input_file = }")
        print(f"{args.output_file = }")
        print(f"{args.indent = }")
    if not (args.input_file and args.output_file):
        parser.error("Input_file and/or output_file is not specified")
    filetype_input = get_file_type(args.input_file)
    filetype_output = get_file_type(args.output_file)
    if filetype_input == Filetype.JSON and filetype_output == Filetype.YAML:
        json_to_yaml(args.input_file, args.output_file)
        if args.verbose:
            print(".yaml file created.")
    elif filetype_input == Filetype.YAML and filetype_output == Filetype.JSON:
        yaml_to_json(args.input_file, args.output_file, indent=args.indent)
        if args.verbose:
            print(".json file created.")
    else:
        raise RuntimeError("Invalid conversion: must convert from .json to .yaml/.yml or vice versa")


def get_file_type(filename):
    filetype = os.path.splitext(filename)[-1]
    if filetype == ".json":
        return Filetype.JSON
    elif filetype == ".yaml" or filetype == ".yml":
        return Filetype.YAML
    else:
        raise ValueError("Invalid file type: file must be .json or .yaml/.yml")
