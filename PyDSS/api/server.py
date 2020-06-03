import logging
from aiohttp import web
from PyDSS.api.src.web.handler import Handler
from aiohttp_swagger3 import *

logger = logging.getLogger(__name__)

class pydss_server():
    def __init__(self):
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
