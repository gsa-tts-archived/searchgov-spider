"""
We may be getting the batches given to us in csv formats from superadmin. Wrote a quick script to help change them into json formmats for jsonnet use.
"""

import json
import csv


def read_csv_to_dict(file_path):
    data = []
    with open(file_path, "r") as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            data.append(row)
    return data


def editDict(csv_data):
    for item in csv_data:
        item["allow_query_string"] = False
        item["handle_javascript"] = False
        item["output_target"] = "csv"
        item["schedule"] = "30 09 * * MON"
        item.pop("Created")


def toJSON(dict_data):
    if dict_data:
        with open("TriCare.json", "w") as file:
            json.dump(dict_data, file, indent=4)


file_path = "TriCare.csv"
csv_data = read_csv_to_dict(file_path)
dict_data = editDict(csv_data)
toJSON(dict_data)
