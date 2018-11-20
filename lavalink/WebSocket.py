import asyncio
import logging

import aiohttp

from .Events import TrackStuckEvent, TrackExceptionEvent, TrackEndEvent, StatsUpdateEvent, VoiceWebSocketClosedEvent

log = logging.getLogger('launcher')


class WebSocket:
    def __init__(self, lavalink, node, host, password, port, ws_retry, shard_count):
        self._lavalink = lavalink
        self._node = node

        self._session = aiohttp.ClientSession()
        self._ws = None
        self._queue = []
        self._ws_retry = ws_retry

        self._password = password
        self._host = host
        self._port = port

        self._uri = 'ws://{}:{}'.format(self._host, self._port)
        self._shards = shard_count
        self._is_v31 = True  # TODO: Remove _is_v31 here and from other files

        self._shutdown = False
        self._first_try = True

        self._loop = self._lavalink.loop
        self._loop.create_task(self.connect())  # TODO: Consider making add_node an async function to prevent creating a bunch of tasks?

        self.max_tries = 5
        self.tries = 0

        self.closers = (aiohttp.WSMsgType.close, aiohttp.WSMsgType.closing, aiohttp.WSMsgType.closed)

    @property
    def connected(self):
        """ Returns whether there is a valid WebSocket connection to the Lavalink server or not. """
        return self._ws and not self._ws.closed

    async def connect(self):
        """ Attempts to establish a connection to Lavalink. """
        await self._lavalink.bot.wait_until_ready()

        headers = {
            'Authorization': str(self._password),
            'Num-Shards': str(self._shards),
            'User-Id': str(self._lavalink.bot.user.id)
        }

        try:
            self._ws = await self._session.ws_connect('ws://{}:{}'.format(self._host, self._port),
                                                      heartbeat=5.0, headers=headers)
        except aiohttp.ClientConnectorError:
            if self.tries < self.max_tries:
                if self._first_try:  # If never connected, stop to try after 5 tries, otherwise infinite tries.
                    self.tries += 1
                log.warning('Failed to connect to node {}, retrying in 5s...'.format(self._uri))
                await asyncio.sleep(5.0)
                await self.connect()
                # TODO: Consider a backoff or max retry attempt.
                # Not sure why max_attempts would come in handy considering you *want* to connect to Lavalink

            else:
                log.warning('Failed to connect to node {}, and max amount of try reached.'.format(self._uri))
                self._node.set_offline()
        else:
            self.tries = 0
            self._first_try = False
            asyncio.ensure_future(self._listen())

    async def _listen(self):
        self._node.set_online()
        for entry in self._queue:
            await self._ws.send_json(entry)
        while self.connected:
            msg = await self._ws.receive()
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = msg.json()
                op = data.get('op', None)
                if op == 'event':
                    await self._manage_event(data)
                elif op == 'playerUpdate':
                    await self._lavalink.update_state(data)
                elif op == 'stats':
                    self._node.stats._update(data)
                    await self._lavalink.dispatch_event(StatsUpdateEvent(self._node))
            elif msg.type in self.closers:
                log.warning('WS sent a closer message. {}: {}'.format(msg.type, msg))
                await self._ws_disconnect(msg.data, msg.extra)
                break
        log.warning('Node {} disconnected, reconnecting...'.format(self._uri))
        await self._ws_disconnect()

    async def _manage_event(self, data):
        log.debug('Received event from node {} of type {}'.format(self._uri, data['type']))
        player = self._lavalink.players[int(data['guildId'])]
        event = None

        if data['type'] == 'TrackEndEvent':
            event = TrackEndEvent(player, data['track'], data['reason'])
        elif data['type'] == 'TrackExceptionEvent':
            event = TrackExceptionEvent(player, data['track'], data['error'])
        elif data['type'] == 'TrackStuckEvent':
            event = TrackStuckEvent(player, data['track'], data['thresholdMs'])
        elif data['type'] == 'WebSocketClosedEvent':
            event = VoiceWebSocketClosedEvent(player, data['code'], data['reason'], data['byRemote'])
        if event:
            await self._lavalink.dispatch_event(event)

    async def _ws_disconnect(self, code: int = None, reason: str = None):
        log.warning('Disconnected from node `{}` ({}): {}'.format(self._uri, code, reason))
        self._ws = None
        self._node.set_offline()  # TODO: testing without

        if not self._shutdown:
            await self._node.manager._node_disconnect(self._node)
            await self.connect()

    async def send(self, **data):
        if self.connected:
            log.debug('Sending payload {}'.format(str(data)))
            await self._ws.send_json(data)
        else:
            log.debug('Send called before node {} ready, payload queued: {}'.format(self._uri, str(data)))
            self._queue.append(data)

    def destroy(self):
        self._shutdown = True
