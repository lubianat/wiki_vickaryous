from flask import Flask, render_template, request
import requests

app = Flask(__name__)

# Function to get data from Wikidata query
def get_wikidata():
    query = """
    SELECT ?assemblage ?assemblageLabel ?cell ?cellLabel ?sitelink
    WHERE
    {
      wd:Q126088667 wdt:P527 ?assemblage . 
      ?assemblage wdt:P527 ?cell . 
      OPTIONAL {
          ?sitelink schema:about ?cell;
          schema:isPartOf <https://en.wikipedia.org/> . 
      }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
    }
    """
    url = 'https://query.wikidata.org/sparql'
    r = requests.get(url, params={'format': 'json', 'query': query})
    data = r.json()
    
    results = {}
    for item in data['results']['bindings']:
        assemblage = item['assemblageLabel']['value']
        assemblage_qid = item['assemblage']['value'].split('/')[-1]
        cell = {
            'label': item['cellLabel']['value'],
            'qid': item['cell']['value'].split('/')[-1],
            'sitelink': item.get('sitelink', {}).get('value', '')
        }
        if assemblage not in results:
            results[assemblage] = {'qid': assemblage_qid, 'cells': []}
        results[assemblage]['cells'].append(cell)
    
    return results

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
    return render_template('index.html', headers=headers, data=data)

@app.route('/assemblage/<name>')
def assemblage(name):
    name = name.replace("+", "/")
    data = get_wikidata()
    assemblage_data = data.get(name, {})
    cells = assemblage_data.get('cells', [])
    assemblage_qid = assemblage_data.get('qid', '')
    header1, headers2 = extract_headers(name)
    return render_template('assemblage.html', name=name, cells=cells, qid=assemblage_qid, header1=header1, headers2=[headers2])

@app.route('/cell/<qid>', methods=['GET'])
def cell(qid):
    data = get_wikidata()
    cell_info = None
    for assemblage, info in data.items():
        for cell in info['cells']:
            if cell['qid'] == qid:
                cell_info = cell
                break
        if cell_info:
            break

    return render_template('cell.html', cell=cell_info)

@app.route('/about')
def about():
    return render_template('about.html')

if __name__ == '__main__':
    app.run(debug=True)
