import logging
import os

import opik
from opik import Opik
from opik.configurator.configure import OpikConfigurator

from src.settings import Settings

settings = Settings()
logger = logging.getLogger(__name__)


def configure_opik( api_key, project) -> None:

    os.environ["OPIK_API_KEY"] = api_key
    os.environ["OPIK_WORKSPACE"] = "hectorrrr"
    os.environ["OPIK_PROJECT_NAME"] = project
    