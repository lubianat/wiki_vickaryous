from flask import Flask, render_template, request
import requests
from flask_caching import Cache
from oaklib import get_adapter

app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

# Initialize the OAK adapter
adapter = get_adapter("sqlite:obo:cl")

# Function to get data from Wikidata query
#@cache.cached(timeout=7200, key_prefix='wikidata_query')  # Cache for 2 hours
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
    url = 'https://query.wikidata.org/sparql'
    headers = {
        'User-Agent': 'MyWikidataApp/1.0 (https://example.com; myemail@example.com)'
    }
    r = requests.get(url, params={'format': 'json', 'query': query}, headers=headers)
    r.raise_for_status()
    data = r.json()
    
    results = {}
    for item in data['results']['bindings']:
        assemblage = item['assemblageLabel']['value']
        assemblage_qid = item['assemblage']['value'].split('/')[-1]
        cell = {
            'label': item['cellLabel']['value'],
            'qid': item['cell']['value'].split('/')[-1],
            'sitelink': item.get('sitelink', {}).get('value', ''),
            'cellOntologyID': item.get('cellOntologyID', {}).get('value', '')
        }
        if assemblage not in results:
            results[assemblage] = {'qid': assemblage_qid, 'cells': []}
        results[assemblage]['cells'].append(cell)
    
    return results

# Function to fetch Cell Ontology information
def fetch_cell_ontology_info(cell_ontology_id):
    if not cell_ontology_id:
        return None
    cell_ontology_id = cell_ontology_id.replace("_", ":")
    info = {
        'id': cell_ontology_id,
        'name': adapter.label(cell_ontology_id),
        'definition': adapter.definition(cell_ontology_id),
        'relationships': []
    }
    
    for rel, parent in adapter.outgoing_relationships(cell_ontology_id):
        info['relationships'].append({
            'relationship': rel,
            'relationship_label': adapter.label(rel),
            'parent': parent,
            'parent_label': adapter.label(parent)
        })
    
    return info

# Function to extract headers from assemblage name
def extract_headers(name):
    name = name.split("(")[1]
    name = name.replace(")", "")
    terms = name.split('→')
    header1 = terms[0].strip()
    header2 = terms[1].strip() if len(terms) > 1 else ''
    return header1, header2

@app.route('/')
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

    return render_template('index.html', headers=headers, data=data)

@app.route('/assemblage/<name>')
def assemblage(name):
    original_name = name.replace("+", "/")
    data = get_wikidata()
    assemblage_data = data.get(original_name, {})
    cells = assemblage_data.get('cells', [])
    assemblage_qid = assemblage_data.get('qid', '')
    header1, headers2 = extract_headers(original_name)
    return render_template('assemblage.html', name=original_name, cells=cells, qid=assemblage_qid, header1=header1, headers2=[headers2])

def extract_assemblage_short_name(name):
    start = name.find("Hall") + 5
    end = name.find("(") - 1
    return name[start:end].strip()

@app.route('/cell/<qid>', methods=['GET'])
def cell(qid):
    data = get_wikidata()
    cell_info = None
    assemblage_name = ""
    assemblage_safe_name = ""
    assemblage_cells = []
    cell_ontology_info = None

    for assemblage, info in data.items():
        for cell in info['cells']:
            if cell['qid'] == qid:
                cell_info = cell
                assemblage_name = assemblage
                assemblage_safe_name = assemblage.replace("/", "+")
                assemblage_cells = [c for c in info['cells'] if c['qid'] != qid]
                if 'cellOntologyID' in cell:
                    cell_ontology_info = fetch_cell_ontology_info(cell['cellOntologyID'])
                break
        if cell_info:
            break

    short_name = extract_assemblage_short_name(assemblage_name)
    return render_template('cell.html', cell=cell_info, assemblage_name=short_name, assemblage_cells=assemblage_cells, assemblage_safe_name=assemblage_safe_name, cell_ontology_info=cell_ontology_info)

@app.route('/about')
def about():
    return render_template('about.html')

if __name__ == '__main__':
    app.run(debug=True)
