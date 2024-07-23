import requests
import csv


# Function to get data from Wikidata query
def get_wikidata():
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


# Function to extract headers from assemblage name
def extract_headers(name):
    name = name.split("(")[1]
    name = name.replace(")", "")
    terms = name.split("→")
    headers = [term.strip() for term in terms]
    return headers


# Function to extract the short ID of the assemblage
def extract_assemblage_short_id(name):
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

        headers = extract_headers(assemblage)
        short_id = extract_assemblage_short_id(assemblage)

        for i in range(len(headers) - 2):
            edges.append([headers[i], headers[i + 1], "", "", "", i + 1])

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


# Function to write edge list to CSV file
def write_edges_to_csv(edges, filename):
    with open(filename, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "name 1",
                "name 2",
                "Wikidata QID 2",
                "Cell Ontology ID 2",
                "Wikipedia Link 2",
                "level",
            ]
        )
        writer.writerows(edges)


# Main script
def main():
    data = get_wikidata()
    edges = build_edge_list(data)
    write_edges_to_csv(edges, "directed_edge_list.csv")


if __name__ == "__main__":
    main()
