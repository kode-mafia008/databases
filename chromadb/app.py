from flask import Flask, render_template, jsonify, request
import os
import time
import logging
import chromadb
from chromadb.config import Settings

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Initialize ChromaDB client with retry logic
client = None
max_retries = 30  # 5 minutes (30 * 10 seconds)

logging.info(f"Attempting to connect to ChromaDB at chroma:8000")

for retry in range(max_retries):
    try:
        logging.info(f"Attempt {retry+1} to connect to ChromaDB...")
        client = chromadb.HttpClient(
            host="chroma",
            port=8000,
            settings=Settings(allow_reset=True, anonymized_telemetry=False),
        )
        # Test the connection
        client.heartbeat()
        logging.info("Successfully connected to ChromaDB!")
        break
    except Exception as e:
        logging.error(f"Failed to connect to ChromaDB: {e}")
        if retry < max_retries - 1:
            logging.info("Retrying in 10 seconds...")
            time.sleep(10)
        else:
            logging.error("Max retries reached, could not connect to ChromaDB")

if client is None:
    logging.warning("Starting with fallback mode - ChromaDB connection not available")


@app.route('/')
def index():
    collections = client.list_collections()
    return render_template('index.html', collections=[c.name for c in collections])

@app.route('/collections')
def get_collections():
    collections = client.list_collections()
    return jsonify([c.name for c in collections])

@app.route('/collection/<name>')
def get_collection(name):
    collection = client.get_collection(name)
    limit = request.args.get('limit', default=100, type=int)
    offset = request.args.get('offset', default=0, type=int)
    
    # Get collection info
    count = collection.count()
    
    # Get sample data with pagination
    results = None
    try:
        if count > 0:
            # Try to get data based on IDs if available
            results = collection.get(limit=limit, offset=offset)
    except Exception as e:
        # Fallback to peek if get fails
        results = collection.peek(limit)
    
    return jsonify({
        "name": name,
        "count": count,
        "data": results
    })

@app.route('/templates/index.html')
def index_template():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>ChromaDB Explorer</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            h1 { color: #333; }
            .collection { 
                cursor: pointer; 
                padding: 10px; 
                margin: 5px 0; 
                background-color: #f0f0f0; 
                border-radius: 4px;
            }
            .collection:hover { background-color: #e0e0e0; }
            #collection-data { 
                margin-top: 20px; 
                border: 1px solid #ddd; 
                padding: 15px;
                border-radius: 4px;
            }
            pre { white-space: pre-wrap; }
        </style>
    </head>
    <body>
        <h1>ChromaDB Explorer</h1>
        
        <h2>Collections</h2>
        <div id="collections-list">Loading...</div>
        
        <div id="collection-data">
            <h2>Collection Data</h2>
            <div id="collection-info">Select a collection to view data</div>
            <pre id="collection-json"></pre>
        </div>
        
        <script>
            // Fetch collections on page load
            fetch('/collections')
                .then(response => response.json())
                .then(collections => {
                    const listElement = document.getElementById('collections-list');
                    if (collections.length === 0) {
                        listElement.innerHTML = '<p>No collections found</p>';
                        return;
                    }
                    
                    listElement.innerHTML = collections.map(name => 
                        `<div class="collection" onclick="loadCollection('${name}')">${name}</div>`
                    ).join('');
                });
            
            // Load collection data
            function loadCollection(name) {
                document.getElementById('collection-info').innerHTML = `Loading ${name}...`;
                document.getElementById('collection-json').innerHTML = '';
                
                fetch(`/collection/${name}`)
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('collection-info').innerHTML = 
                            `Collection: ${name} (${data.count} items)`;
                        document.getElementById('collection-json').innerHTML = 
                            JSON.stringify(data.data, null, 2);
                    })
                    .catch(error => {
                        document.getElementById('collection-info').innerHTML = 
                            `Error loading collection ${name}: ${error.message}`;
                    });
            }
        </script>
    </body>
    </html>
    """

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
