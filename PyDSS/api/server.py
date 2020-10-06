from PyDSS.api.src.web.handler import Handler
import PyDSS.api.schema as schema
from aiohttp_swagger3 import *
from aiohttp import web
import threading
import requests
import logging
import json
import time
import os
logger = logging.getLogger(__name__)

def getJSONschema(host, port):
    base_path = schema.__path__._path[0]
    path = os.path.join(base_path, 'PyDSS.v1.json')
    base_url = f"http://{host}:{port}"
    url = base_url + "/docs/swagger.json"
    isValid = False
    while not isValid:
        time.sleep(3)
        response = requests.get(url)
        isValid = response.status_code == 200
    with open(path, 'w') as outfile:
        json.dump(response.json(), outfile, indent=4, sort_keys=True)
    logger.info(f"Export the schema file to {path}")

class pydss_server():
    def __init__(self, host, port):
        self.handler = Handler()
        self.app = web.Application()
        self.swagger = SwaggerDocs(
            self.app,
            title="PyDSS RESTful API documentation",
            version="2.0.1",
            description = "The API enables creating PyDSS instances, running simulations and creation of new projects.",
            swagger_ui_settings=SwaggerUiSettings(path="/docs/"),
            # components="components.yaml"
        )
        self.register_media_handlers()
        self.add_routes()
        t = threading.Thread(name='child procs', target=getJSONschema, args=(host, port,))
        t.start()

    def register_media_handlers(self):
        self.swagger.register_media_type_handler("multipart/form-data", self.handler.post_pydss_create)
        return

    def add_routes(self):
        self.swagger.add_routes([
            web.get('/simulators/pydss/instances', self.handler.get_instance_uuids),
            web.get('/simulators/pydss/status/uuid/{uuid}', self.handler.get_instance_status),
            web.get('/simulators/pydss/info', self.handler.get_pydss_project_info),

            web.put('/simulators/pydss', self.handler.put_pydss),

            web.post('/simulators/pydss', self.handler.post_pydss),
            web.post('/simulators/pydss/create', self.handler.post_pydss_create, validate=False),

            web.delete('/simulators/pydss', self.handler.delete_pydss)
        ])
    async def clean_background_tasks(self, app):
        logger.info("cleanup_background_tasks")
        self.handler.event.set()
