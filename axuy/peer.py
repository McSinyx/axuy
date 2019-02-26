# peer.py - peer main loop
# Copyright (C) 2019  Nguyễn Gia Phong
#
# This file is part of Axuy
#
# Axuy is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Axuy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Axuy.  If not, see <https://www.gnu.org/licenses/>.

__doc__ = 'Axuy main loop'

from argparse import ArgumentParser, RawTextHelpFormatter
from pickle import dumps, loads
from socket import socket, SOCK_DGRAM, SOL_SOCKET, SO_REUSEADDR
from threading import Thread

from .misc import mapgen, mapidgen
from .pico import Picobot
from .view import View


class Peer:
    """Axuy peer.
    TODO: Documentation
    """

    def __init__(self, args):
        if args.seeder is None:
            mapid = mapidgen()
            self.peers = []
        else:
            client = socket()
            host, port = args.seeder.split(':')
            self.peers = [(host, int(port))]
            client.connect(*self.peers)
            data = loads(client.recv(1024))
            mapid = data['mapid']
            self.peers.extend(data['peers'])

        self.space = mapgen(mapid)
        self.pico = Picobot(self.space, (0, 0, 0))
        self.view = View(self.pico, args.width, args.height, self.space)

        address = args.host, args.port
        data_server = Thread(target=self.serve,
                             args=(address, mapid))
        data_server.daemon = True
        data_server.start()

        self.sock = socket(type=SOCK_DGRAM)   # UDP
        self.sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.sock.bind(address)

        pusher = Thread(target=self.push)
        pusher.daemon = True
        pusher.start()
        puller = Thread(target=self.pull)
        puller.daemon = True
        puller.start()

    def serve(self, address, mapid):
        """Initiate peers."""
        self.server = socket()  # TCP server
        self.server.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.server.bind(address)
        self.server.listen(7)
        while self.view.is_running:
            conn, addr = self.server.accept()
            conn.send(dumps({'mapid': mapid, 'peers': self.peers}))
            conn.close()
        self.server.close()

    def push(self):
        """Send own state to peers."""
        while self.view.is_running:
            for peer in self.peers: 
                self.sock.sendto(dumps(self.view.camera.state), peer)

    def pull(self):
        """Receive peers' state."""
        while self.view.is_running:
            data, addr = self.sock.recvfrom(1024)
            pos, rot = loads(data)
            try:
                self.view.picos[addr].update(pos, rot)
            except KeyError:
                self.view.picos[addr] = Picobot(self.space, pos, rot)
                self.peers.append(addr)

    def __enter__(self): return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.server.close()
        self.sock.close()
        self.view.close()


def main():
    """Parse command-line arguments and start main loop."""
    parser = ArgumentParser(usage='%(prog)s [options]',
                            formatter_class=RawTextHelpFormatter)
    parser.add_argument('--seeder')
    parser.add_argument('--host')
    parser.add_argument('--port', type=int)
    parser.add_argument('--width', type=int, help='window width')
    parser.add_argument('--height', type=int, help='window height')
    with Peer(parser.parse_args()) as peer:
        while peer.view.is_running: peer.view.update()
