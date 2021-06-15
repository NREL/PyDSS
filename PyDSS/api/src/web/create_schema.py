import requests
import json

def getJSONschema(ip, port, path):
    base_url = f"http://{ip}:{port}"
    url = base_url + "/docs/swagger.json"

    response = requests.get(url)
    with open(path, 'w') as outfile:
        json.dump(response.json(), outfile)

getJSONschema("127.0.0.1", 9090, r"C:\Users\alatif\Desktop\PyDSS_service\pydss_service\test.json")