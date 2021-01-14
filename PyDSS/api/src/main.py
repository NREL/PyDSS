from naerm_core.web.api_server import ApiServer
from PyDSS.api.src.web.handler import Handler
import PyDSS.api.schema as schema
from aiohttp_swagger3 import *
from http import HTTPStatus
from aiohttp import web
import threading
import requests
import logging
import json
import time
import os
logger = logging.getLogger(__name__)

def getJSONschema(host,port):
    base_path = schema.__path__._path[0]
    path = os.path.join(base_path, 'PyDSS.v1.json')
    base_url = f"http://{host}:{port}"
    url = base_url + "/docs/swagger.json"
    isValid = False
    while not isValid:
        time.sleep(3)
        response = requests.get(url)
        isValid = response.status_code == HTTPStatus.OK

    json_content = response.json()
    json_content['info'].update({"contact":
                {"name": "Aadil Latif", 
                "email": "Aadil.Latif@nrel.gov", 
                "url": "https://www.nrel.gov/"}
            })
    
    with open(path, 'w') as outfile:
        json.dump(json_content, outfile, indent=4, sort_keys=True)
    logger.info(f"Export the schema file to {path}")

class pydss_server(ApiServer):
    def __init__(self, debug=True, **kwargs):
        super().__init__(**kwargs)
        self.handler = Handler(self.config.helics, self.config.endpoints, loop=self.loop, debug=debug)
        self.app = web.Application()
        self.swagger = SwaggerDocs(
            self.app,
            title="PyDSS RESTful API documentation",
            version="1.0",
            description = "The API enables creating PyDSS instances, running simulations and creation of new projects.",
            swagger_ui_settings=SwaggerUiSettings(path="/docs/"),
            # components="components.yaml"
        )
        self.register_media_handlers()
        self.add_routes()
        self.t = threading.Thread(name='pydss thread', target=getJSONschema, args=(self.host,self.port))
        self.t.start()
        self.run_app(on_cleanup_task=self.cleanup_background_tasks)

    def register_media_handlers(self):
        #self.swagger.register_media_type_handler("multipart/form-data", self.handler.post_pydss_create)
        return
    

    def add_routes(self):
        self.swagger.add_routes([
            web.get('/cosims/federates/pydss/instances', self.handler.get_instance_uuids),
            web.get('/cosims/federates/pydss/status/uuid/{uuid}', self.handler.get_instance_status),
            web.post('/cosims/federates/pydss', self.handler.post_pydss),
            web.delete('/cosims/federates/pydss', self.handler.delete_pydss)
        ])
    async def cleanup_background_tasks(self, app):
        logger.info("cleanup_background_tasks")
        self.t.join()
        self.handler.shutdown_event.set()

if __name__ == "__main__":
    FORMAT = '%(asctime)s -  %(levelname)s - %(message)s'
    logging.basicConfig(level=logging.INFO,format=FORMAT)
    #endpoints_file='app/endpoints.yaml'
    instance = pydss_server()