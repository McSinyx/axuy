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
__version__ = '0.0.10'

from abc import ABC, abstractmethod
from argparse import ArgumentParser, FileType, RawTextHelpFormatter
from configparser import ConfigParser
from os.path import join as pathjoin, pathsep
from pickle import dumps, loads
from queue import Empty, Queue
from socket import SO_REUSEADDR, SOCK_DGRAM, SOL_SOCKET, socket
from sys import stdout
from threading import Thread
from typing import Iterator, Tuple

from appdirs import AppDirs

from .misc import abspath, mapgen, mapidgen
from .pico import Pico

SETTINGS = abspath('settings.ini')


class PeerConfig:
    """Networking configurations.

    Attributes
    ----------
    config : ConfigParser
        INI configuration file parser.
    options : ArgumentParser
        Command-line argument parser.
    host : str
        Host to bind the peer to.
    port : int
        Port to bind the peer to.
    seeder : str
        Address of the peer that created the map.
    """

    def __init__(self) -> None:
        dirs = AppDirs(appname='axuy', appauthor=False, multipath=True)
        parents = dirs.site_config_dir.split(pathsep)
        parents.append(dirs.user_config_dir)
        filenames = [pathjoin(parent, 'settings.ini') for parent in parents]

        # Parse configuration files
        self.config = ConfigParser()
        self.config.read(SETTINGS)
        self.config.read(filenames)
        self.fallback()

        # Parse command-line arguments
        self.options = ArgumentParser(usage='%(prog)s [options]',
                                      formatter_class=RawTextHelpFormatter)
        self.options.add_argument('-v', '--version', action='version',
                                  version='Axuy {}'.format(__version__))
        self.options.add_argument(
            '--write-config', nargs='?', const=stdout, type=FileType('w'),
            metavar='PATH', dest='cfgout',
            help='write default config to PATH (fallback: stdout) and exit')
        self.options.add_argument(
            '-c', '--config', metavar='PATH',
            help='location of the configuration file (fallback: {})'.format(
                pathsep.join(filenames)))
        self.options.add_argument(
            '--host',
            help='host to bind this peer to (fallback: {})'.format(self.host))
        self.options.add_argument(
            '-p', '--port', type=int,
            help='port to bind this peer to (fallback: {})'.format(self.port))
        self.options.add_argument(
            '-s', '--seeder', metavar='ADDRESS',
            help='address of the peer that created the map')

    def fallback(self) -> None:
        """Parse fallback configurations."""
        self.host = self.config.get('Peer', 'Host')
        self.port = self.config.getint('Peer', 'Port')

    # Fallback to None when attribute is missing
    def __getattr__(self, name): return None

    @property
    def seeder(self) -> Tuple[str, int]:
        """Seeder address."""
        return self.__seed

    @seeder.setter
    def seeder(self, value: str) -> None:
        host, port = value.split(':')
        self.__seed = host, int(port)

    def read(self, arguments):
        """Read and parse a argparse.ArgumentParser.Namespace."""
        for option in 'host', 'port', 'seeder':
            value = getattr(arguments, option)
            if value is not None: setattr(self, option, value)

    def parse(self) -> None:
        """Parse all configurations."""
        args = self.options.parse_args()
        if args.cfgout is not None:
            with open(SETTINGS) as f: args.cfgout.write(f.read())
            args.cfgout.close()
            exit()
        if args.config:     # is neither None nor empty
            self.config.read(args.config)
            self.fallback()
        self.read(args)


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
    peers : List[Tuple[str, int]]
        Addresses of connected peers.
    mapid : List[int]
        Permutation of map building blocks.
    space : numpy.ndarray of shape (12, 12, 9) of bools
        3D array of occupied space.
    pico : Pico
        Protagonist.
    picos : Dict[Tuple[str, int], Pico]
        All picos present in the map.
    last_time : float
        Timestamp of the previous update.
    """

    def __init__(self, config):
        self.sock = socket(type=SOCK_DGRAM)     # UDP
        self.sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.sock.bind((config.host, config.port))
        self.addr = self.sock.getsockname()
        self.q = Queue()

        if config.seeder is None:
            self.mapid, self.peers = mapidgen(), []
        else:
            client = socket()
            client.connect(config.seeder)
            self.mapid, self.peers = loads(client.recv(1024))

        self.space = mapgen(self.mapid)
        self.pico = Pico(self.addr, self.space)
        self.picos = {self.addr: self.pico}
        self.last_time = self.get_time()

    def __enter__(self): return self

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

    @property
    def fps(self) -> float:
        """Current loop rate."""
        return self.pico.fps

    @fps.setter
    def fps(self, fps: float) -> None:
        self.pico.fps = fps

    def serve(self) -> None:
        """Initiate other peers."""
        with socket() as server:    # TCP server
            server.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
            server.bind(self.addr)
            server.listen(7)
            print('Axuy is listening at {}:{}'.format(*self.addr))
            while self.is_running:
                conn, addr = server.accept()
                conn.send(dumps((self.mapid, self.peers+[self.addr])))
                conn.close()
            server.close()

    def pull(self) -> None:
        """Receive other peers' states."""
        while self.is_running: self.q.put(self.sock.recvfrom(1 << 16))
        while not self.q.empty():
            self.q.get()
            self.q.task_done()

    @abstractmethod
    def get_time(self) -> float:
        """Return the current time in seconds."""

    def add_pico(self, address):
        """Add pico from given address."""
        self.picos[address] = Pico(address, self.space)

    def sync(self) -> None:
        """Synchronize states received from other peers."""
        for data, addr in self.ready:
            if addr not in self.picos:
                self.peers.append(addr)
                self.add_pico(addr)
            self.picos[addr].sync(*loads(data))

    def push(self) -> None:
        """Push states to other peers."""
        shards = {i: (s.pos, s.rot, s.power)
                  for i, s in self.pico.shards.items()}
        data = dumps([self.pico.health, self.pico.pos, self.pico.rot, shards])
        for peer in self.peers: self.sock.sendto(data, peer)

    @abstractmethod
    def control(self) -> None:
        """Control the protagonist."""
        self.pico.update()  # just a reminder that this needs to be called

    def update(self) -> None:
        """Update internal states and send them to other peers."""
        next_time = self.get_time()
        self.fps = 1 / (next_time-self.last_time)
        self.last_time = next_time

        self.sync()
        self.control()
        picos = list(self.picos.values())
        for pico in picos:
            shards = {}
            for index, shard in pico.shards.items():
                shard.update(self.fps, picos)
                if shard.power: shards[index] = shard
            pico.shards = shards
        self.push()

    def run(self) -> None:
        """Start main loop."""
        Thread(target=self.serve, daemon=True).start()
        Thread(target=self.pull, daemon=True).start()
        while self.is_running: self.update()

    def __exit__(self, exc_type, exc_value, traceback):
        self.q.join()
        self.sock.close()
