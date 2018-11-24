# flake8: noqa

__title__ = 'Lavalink'
__author__ = 'Devoxin'
__license__ = 'MIT'
__copyright__ = 'Copyright 2018 Devoxin'
__version__ = '3.0.9'

import logging
import sys

from .audiotrack import *
from .client import *
from .playermanager import *
from .websockets import *
from . import events
from . import utils
from .nodemanager import Regions


log = logging.getLogger('lavalink')

fmt = logging.Formatter(
    '[%(asctime)s] [lavalink.py] [%(levelname)s] %(message)s',
    datefmt="%H:%M:%S"
)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(fmt)
log.addHandler(handler)

log.setLevel(logging.DEBUG)
