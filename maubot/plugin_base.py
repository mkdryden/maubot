# maubot - A plugin-based Matrix bot system.
# Copyright (C) 2021 Tulir Asokan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
from typing import Type, Optional, TYPE_CHECKING
from abc import ABC
from asyncio import AbstractEventLoop

from sqlalchemy.engine.base import Engine
from aiohttp import ClientSession
from yarl import URL

if TYPE_CHECKING:
    from mautrix.util.logging import TraceLogger
    from mautrix.util.config import BaseProxyConfig
    from .client import MaubotMatrixClient
    from .plugin_server import PluginWebApp
    from .loader import BasePluginLoader


class Plugin(ABC):
    client: 'MaubotMatrixClient'
    http: ClientSession
    id: str
    log: 'TraceLogger'
    loop: AbstractEventLoop
    loader: 'BasePluginLoader'
    config: Optional['BaseProxyConfig']
    database: Optional[Engine]
    webapp: Optional['PluginWebApp']
    webapp_url: Optional[URL]

    def __init__(self, client: 'MaubotMatrixClient', loop: AbstractEventLoop, http: ClientSession,
                 instance_id: str, log: 'TraceLogger', config: Optional['BaseProxyConfig'],
                 database: Optional[Engine], webapp: Optional['PluginWebApp'],
                 webapp_url: Optional[str], loader: 'BasePluginLoader') -> None:
        self.client = client
        self.loop = loop
        self.http = http
        self.id = instance_id
        self.log = log
        self.config = config
        self.database = database
        self.webapp = webapp
        self.webapp_url = URL(webapp_url) if webapp_url else None
        self.loader = loader
        self._handlers_at_startup = []

    def register_handler_class(self, obj) -> None:
        warned_webapp = False
        for key in dir(obj):
            if key.startswith('__') and key.endswith('__'):  # ignore magic attributes
                 continue
            val = getattr(obj, key, None)
            try:
                if val.__mb_event_handler__:
                    self._handlers_at_startup.append((val, val.__mb_event_type__))
                    self.client.add_event_handler(val.__mb_event_type__, val)
            except AttributeError:
                pass
            try:
                web_handlers = val.__mb_web_handler__
            except AttributeError:
                pass
            else:
                if len(web_handlers) > 0 and self.webapp is None:
                    if not warned_webapp:
                        self.log.warning(f"{type(obj).__name__} has web handlers, but the webapp"
                                         " feature isn't enabled in the plugin's maubot.yaml")
                    warned_webapp = True
                    continue
                for method, path, kwargs in web_handlers:
                    self.webapp.add_route(method=method, path=path, handler=val, **kwargs)

    async def pre_start(self) -> None:
        pass

    async def internal_start(self) -> None:
        await self.pre_start()
        self.register_handler_class(self)
        await self.start()

    async def start(self) -> None:
        pass

    async def pre_stop(self) -> None:
        pass

    async def internal_stop(self) -> None:
        await self.pre_stop()
        for func, event_type in self._handlers_at_startup:
            self.client.remove_event_handler(event_type, func)
        if self.webapp is not None:
            self.webapp.clear()
        await self.stop()

    async def stop(self) -> None:
        pass

    @classmethod
    def get_config_class(cls) -> Optional[Type['BaseProxyConfig']]:
        return None

    def on_external_config_update(self) -> None:
        if self.config:
            self.config.load_and_update()
