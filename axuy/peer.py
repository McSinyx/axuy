# p2p networking
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

__doc__ = 'Axuy peer'
__all__ = ['PeerConfig', 'Peer']

from abc import ABC, abstractmethod
from configparser import ConfigParser
from os.path import join as pathjoin, pathsep
from pickle import dumps, loads
from queue import Empty, Queue
from socket import socket, SOCK_DGRAM, SOL_SOCKET, SO_REUSEADDR
from threading import Thread
from typing import Iterator, Tuple

from appdirs import AppDirs

from .misc import abspath, mapgen, mapidgen
from .pico import Pico


class PeerConfig:
    """Networking configurations

    Attributes
    ----------
    config : ConfigParser
        INI configuration file parser.
    host : str
        Host to bind the peer to.
    port : int
        Port to bind the peer to.
    seeder : str
        Address of the peer that created the map.
    """

    def __init__(self):
        dirs = AppDirs(appname='axuy', appauthor=False, multipath=True)
        parents = dirs.site_config_dir.split(pathsep)
        parents.append(dirs.user_config_dir)
        filenames = [pathjoin(parent, 'settings.ini') for parent in parents]

        self.config = ConfigParser()
        self.config.read(abspath('settings.ini'))    # default configuration
        self.config.read(filenames)

    # Fallback to None when attribute is missing
    def __getattr__(self, name): return None

    @property
    def seeder(self) -> Tuple[str, int]:
        """Seeder address."""
        return self._seed

    @seeder.setter
    def seeder(self, value):
        host, port = value.split(':')
        self._seed = host, int(port)

    def parse(self):
        """Parse configurations."""
        self.host = self.config.get('Peer', 'Host')
        self.port = self.config.getint('Peer', 'Port')

    def read_args(self, arguments):
        """Read and parse a argparse.ArgumentParser.Namespace."""
        for option in 'host', 'port', 'seeder':
            value = getattr(arguments, option)
            if value is not None: setattr(self, option, value)


class Peer(ABC):
    """Axuy peer.

    Parameters
    ----------
    config : PeerConfig
        Networking configurations.

    Attributes
    ----------
    sock : socket
        UDP socket for exchanging instantaneous states with other peers.
    addr : Tuple[str, int]
        Own's address.
    q : Queue[Tuple[bytes, Tuple[str, int]]]
        Queue of (data, addr), where addr is the address of the peer
        who sent the raw data.
    peers : List[Tuple[str, int], ...]
        Addresses of connected peers.
    space : numpy.ndarray of shape (12, 12, 9) of bools
        3D array of occupied space.
    pico : Pico
        Protagonist.
    picos : Dict[Tuple[str, int], Pico]
        All picos present in the map.
    view : View
        World representation and renderer.
    """

    def __init__(self, config):
        self.sock = socket(type=SOCK_DGRAM)     # UDP
        self.sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.sock.bind((config.host, config.port))
        self.addr = self.sock.getsockname()
        self.q = Queue()

        if config.seeder is None:
            mapid, self.peers = mapidgen(), []
        else:
            client = socket()
            client.connect(config.seeder)
            mapid, self.peers = loads(client.recv(1024))

        self.space = mapgen(mapid)
        self.pico = Pico(self.addr, self.space)
        self.picos = {self.addr: self.pico}

        Thread(target=self.serve, args=(mapid,), daemon=True).start()
        Thread(target=self.pull, daemon=True).start()

    @property
    @abstractmethod
    def is_running(self) -> bool:
        """Peer status."""

    @property
    def ready(self) -> Iterator[Tuple[bytes, Tuple[str, int]]]:
        """Iterator of (data, addr) that can be used without waiting,
        where addr is the address of the peer who sent the data.
        """
        while True:
            try:
                yield self.q.get_nowait()
            except Empty:
                break
            else:
                self.q.task_done()

    def serve(self, mapid):
        """Initiate other peers."""
        with socket() as server:    # TCP server
            server.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
            server.bind(self.addr)
            server.listen(7)
            print('Axuy is listening at {}:{}'.format(*self.addr))
            while self.is_running:
                conn, addr = server.accept()
                conn.send(dumps((mapid, self.peers+[self.addr])))
                conn.close()
            server.close()

    def pull(self):
        """Receive other peers' states."""
        while self.is_running: self.q.put(self.sock.recvfrom(1 << 16))
        while not self.q.empty():
            self.q.get()
            self.q.task_done()

    def __enter__(self): return self

    def sync(self):
        """Synchronize states received from other peers."""
        for data, addr in self.ready:
            if addr not in self.picos:
                self.peers.append(addr)
                self.add_pico(addr)
            self.picos[addr].sync(*loads(data))

    def push(self):
        """Push states to other peers."""
        shards = {i: (s.pos, s.rot, s.power)
                  for i, s in self.pico.shards.items()}
        data = dumps([self.pico.health, self.pico.pos, self.pico.rot, shards])
        for peer in self.peers: self.sock.sendto(data, peer)

    @abstractmethod
    def control(self):
        """Control the protagonist."""

    @abstractmethod
    def update(self):
        """Update internal states and send them to other peers."""
        self.sync()
        self.control()
        self.push()

    @abstractmethod
    def close(self):
        """Explicitly terminate stuff in subclass
        that cannot be garbage collected.
        """

    def __exit__(self, exc_type, exc_value, traceback):
        self.q.join()
        self.sock.close()
        self.close()
