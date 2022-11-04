import argparse
import glob
import json
import os

from tabulate import tabulate


def find_predefined_examples(
    *,
    path=None,
    sim_type=None,
    pattern="00*",
    outfile=None,
    tablefmt="rst",
    verbose=False,
):

    base_url = "https://github.com/NSLS-II/sirepo-bluesky/tree/main/"

    pattern_file = f"{pattern}/sirepo-data.json"
    sim_jsons = sorted(glob.glob(os.path.join(path, sim_type, pattern_file)))
    headers = ["Simulation ID", "Description"]
    table = []
    for sim_json in sim_jsons:
        with open(sim_json, "r") as f:
            sim_dict = json.load(f)
            sim_info = sim_dict["models"]["simulation"]
            sim_id = sim_info["simulationId"]
            desc = sim_info["name"]
            trimmed_json_path = sim_json.replace("../", "")
            table.append(
                [
                    f"``{sim_id}``",
                    f"`{desc} " f"<{os.path.join(base_url, trimmed_json_path)}>`_",
                ]
            )

    maxcolwidths = [20, 80]

    tbl = tabulate(table, headers, tablefmt=tablefmt, maxcolwidths=maxcolwidths)

    indented_tbl = "\n".join([f"   {row}" for row in tbl.split("\n")])

    tbl = f"""
.. table::
   :width: 100%
   :widths: {" ".join([str(x) for x in maxcolwidths])}

{indented_tbl}
"""

    if verbose:
        print(tbl)
    with open(outfile, "w") as f:
        f.write(tbl)


if __name__ == "__main__":
    description = "Find predefined examples and print a summary about them."
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--path",
        type=str,
        required=True,
        help="path where to perform the search (without the simulation type part)",
    )
    parser.add_argument(
        "--sim-type",
        type=str,
        required=True,
        help="simulation type (`srw`, `shadow`, `madx`, etc.)",
    )
    parser.add_argument("--pattern", type=str, default="00*", help="search pattern")
    parser.add_argument(
        "--outfile", type=str, required=True, help="output file for the resulting table"
    )
    parser.add_argument("--tablefmt", type=str, default="rst", help="table format")
    parser.add_argument(
        "--verbose", action="store_true", help="print the resulting table"
    )

    args = parser.parse_args()

    path = args.path
    sim_type = args.sim_type.lower()
    pattern = args.pattern
    outfile = args.outfile
    tablefmt = args.tablefmt
    verbose = args.verbose

    find_predefined_examples(
        path=path,
        sim_type=sim_type,
        pattern=pattern,
        outfile=outfile,
        tablefmt=tablefmt,
        verbose=verbose,
    )
