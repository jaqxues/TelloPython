import logging
import queue
import socket
import threading
import time

from utils import validate_bounds as validate, try_to_int, AtomicInteger
from abc import ABC, abstractmethod


class AdvancedTello:
    TELLO_COMMAND_PORT = 8889

    def __init__(self, tello_ip='192.168.10.1', tello_port=None):
        if tello_port is None:
            tello_port = self.TELLO_COMMAND_PORT

        self.tello_address = (tello_ip, tello_port)

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def __del__(self):
        self.socket.close()

    def _send(self, cmd_id, data, pac_type):
        """ takes the arguments of a `SocketPacketEntity`"""
        bb = bytearray()

    def _packetToByteArray(self, cmd_id, data, pac_type, seq_num):
        size = 11 + (len(data) if data is not None else 0)

        bytes = bytearray(size)
        bytes[0] = 204
        bytes[1:2] = (size << 3).to_bytes(length=2, byteorder='big')



logging.basicConfig(level=logging.DEBUG)
