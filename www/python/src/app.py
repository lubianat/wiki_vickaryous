from flask import Flask, render_template, request, jsonify
import requests
from flask_caching import Cache

app = Flask(__name__)
cache = Cache(app, config={"CACHE_TYPE": "simple"})


def query_wikidata():
    query = """
    SELECT ?assemblage ?assemblageLabel ?cell ?cellLabel ?sitelink ?cellOntologyID
    WHERE
    {
      wd:Q126088667 wdt:P527 ?assemblage . 
      ?assemblage wdt:P527 ?cell . 
      OPTIONAL {
          ?cell wdt:P7963 ?cellOntologyID .
      }
      OPTIONAL {
          ?sitelink schema:about ?cell;
          schema:isPartOf <https://en.wikipedia.org/> . 
      }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
    }
    """
    url = "https://query.wikidata.org/sparql"
    headers = {
        "User-Agent": "MyWikidataApp/1.0 (https://example.com; myemail@example.com)"
    }
    r = requests.get(url, params={"format": "json", "query": query}, headers=headers)
    r.raise_for_status()
    return r.json()


# Function to get data from Wikidata query
@cache.cached(timeout=7200, key_prefix="wikidata_query")  # Cache for 2 hours
# Updated SPARQL query to include Cell Ontology ID
def get_wikidata():
    data = query_wikidata()
    results = {}
    for item in data["results"]["bindings"]:
        assemblage = item["assemblageLabel"]["value"]
        assemblage_qid = item["assemblage"]["value"].split("/")[-1]
        cell = {
            "label": item["cellLabel"]["value"],
            "qid": item["cell"]["value"].split("/")[-1],
            "sitelink": item.get("sitelink", {}).get("value", ""),
            "cellOntologyID": item.get("cellOntologyID", {}).get("value", ""),
        }
        if assemblage not in results:
            results[assemblage] = {"qid": assemblage_qid, "cells": []}
        results[assemblage]["cells"].append(cell)

    return results


# Function to extract headers from assemblage name
def extract_headers(name):
    name = name.split("(")[1]
    name = name.replace(")", "")
    terms = name.split("→")
    header1 = terms[0].strip()
    header2 = terms[1].strip() if len(terms) > 1 else ""
    return header1, header2


@app.route("/")
def index():
    data = get_wikidata()
    headers = {}
    for name in data.keys():
        header1, header2 = extract_headers(name)
        name_safe = name.replace("/", "+")
        if header1 not in headers:
            headers[header1] = {}
        if header2 not in headers[header1]:
            headers[header1][header2] = []
        headers[header1][header2].append(name_safe)

    # Sort the assemblages alphabetically
    for header1 in headers:
        for header2 in headers[header1]:
            headers[header1][header2].sort()

    return render_template("index.html", headers=headers, data=data)


@app.route("/assemblage/<name>")
def assemblage(name):
    original_name = name.replace("+", "/")
    data = get_wikidata()
    assemblage_data = data.get(original_name, {})
    cells = assemblage_data.get("cells", [])
    assemblage_qid = assemblage_data.get("qid", "")
    header1, headers2 = extract_headers(original_name)
    return render_template(
        "assemblage.html",
        name=original_name,
        cells=cells,
        qid=assemblage_qid,
        header1=header1,
        headers2=[headers2],
    )


def extract_assemblage_short_name(name):
    start = name.find("Hall") + 5
    end = name.find("(") - 1
    return name[start:end].strip()


@app.route("/cell/<qid>", methods=["GET"])
def cell(qid):
    data = get_wikidata()
    cell_info = None
    assemblage_name = ""
    assemblage_safe_name = ""
    assemblage_cells = []
    cell_ontology_id = None

    for assemblage, info in data.items():
        for cell in info["cells"]:
            if cell["qid"] == qid:
                cell_info = cell
                assemblage_name = assemblage
                assemblage_safe_name = assemblage.replace("/", "+")
                assemblage_cells = [c for c in info["cells"] if c["qid"] != qid]
                cell_ontology_id = cell.get("cellOntologyID")
                break
        if cell_info:
            break

    short_name = extract_assemblage_short_name(assemblage_name)
    return render_template(
        "cell.html",
        cell=cell_info,
        assemblage_name=short_name,
        assemblage_cells=assemblage_cells,
        assemblage_safe_name=assemblage_safe_name,
        cell_ontology_id=cell_ontology_id,
    )


# Function to extract headers from assemblage name
def extract_headers_2(name):
    name = name.split("(")[1]
    name = name.replace(")", "")
    terms = name.split("→")
    headers = [term.strip() for term in terms]
    return headers


# Function to extract the short ID of the assemblage
def extract_assemblage_short_id_2(name):
    return name.split()[4]


# Function to parse data and build edge list
def build_edge_list(data):
    edges = []
    for item in data["results"]["bindings"]:
        assemblage = item["assemblageLabel"]["value"]
        assemblage_qid = item["assemblage"]["value"].split("/")[-1]
        cell_label = item["cellLabel"]["value"]
        cell_qid = item["cell"]["value"].split("/")[-1]
        cell_ontology_id = item.get("cellOntologyID", {}).get("value", "")
        sitelink = item.get("sitelink", {}).get("value", "")

        headers = extract_headers_2(assemblage)
        short_id = extract_assemblage_short_id_2(assemblage)

        for i in range(len(headers) - 2):
            edges.append([headers[i], headers[i + 1], "", "", "", i + 2])

        # Add pre-terminal label and assemblage number
        if len(headers) > 1:
            pre_terminal_edge = [
                headers[-2],
                f"{headers[-1]} (assemblage {short_id})",
                assemblage_qid,
                "",
                "",
                "pre-terminal",
            ]
            if pre_terminal_edge not in edges:
                edges.append(pre_terminal_edge)

        terminal_edge = [
            f"{headers[-1]} (assemblage {short_id})",
            cell_label,
            cell_qid,
            cell_ontology_id,
            sitelink,
            "terminal",
        ]
        if terminal_edge not in edges:
            edges.append(terminal_edge)

    # Remove duplicate edges
    unique_edges = []
    for edge in edges:
        if edge not in unique_edges:
            unique_edges.append(edge)

    return unique_edges


@app.route("/data")
def data():
    data = query_wikidata()
    edges = build_edge_list(data)
    return jsonify(edges)


@app.route("/about")
def about():
    return render_template("about.html")


if __name__ == "__main__":
    app.run()
