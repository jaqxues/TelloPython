import logging
import socket
import threading
from datetime import datetime

from dev_utils import calc_crc8, calc_crc16
from utils import RepeatedTimer


class SocketPacket:
    def __init__(self, cmd_id, pac_type, seq_num=0, data=None):
        self.cmd_id = cmd_id
        self.data = data
        self.pac_type = pac_type
        self.seq_num = seq_num

    def to_raw_bytes(self, seq=None, data=None):
        if seq is not None:
            self.seq_num = seq
        if data is not None:
            self.data = data
        cap = 11 + (0 if self.data is None else len(self.data))

        bb = bytearray(cap)
        bb[0] = 204
        bb[1:3] = (cap << 3).to_bytes(2, byteorder='little')
        bb[3] = calc_crc8(bb, 3)
        bb[4] = self.pac_type
        bb[5:7] = self.cmd_id.to_bytes(2, byteorder='little')
        bb[7:9] = self.seq_num.to_bytes(2, byteorder='little')
        if self.data:
            bb[9:-2] = self.data
        bb[-2:] = (calc_crc16(bb, cap - 2)).to_bytes(2, byteorder='little')
        return bb

    @classmethod
    def from_raw_bytes(cls, tello, raw):
        prefix = raw[0]
        if prefix == 204:
            size = int.from_bytes(raw[1:3], byteorder='little') >> 3

            # Check CRC8 Values
            crc8_check = raw[3]
            crc8_actual = calc_crc8(raw, 3)
            if crc8_actual != crc8_check:
                logging.error(f"Mismatched CRC8 Values: (Expected - Actual) -> ({crc8_check} - {crc8_actual})")

            # Check CRC16 Values
            crc16_check = int.from_bytes(raw[-2:], byteorder='little')
            crc16_actual = calc_crc16(raw, size - 2)
            if crc16_actual != crc16_check:
                logging.error(f"Mismatched CRC16 Values: (Expected - Actual) -> ({crc16_check} - {crc16_actual})")

            pac_type = raw[4]
            cmd_id = int.from_bytes(raw[5:7], byteorder='little')
            seq_num = int.from_bytes(raw[7:9], byteorder='little')
            data = raw[9:-2]

            return cls(cmd_id, data, pac_type, seq_num)

        elif prefix == 99:
            if raw == bytearray(b'conn_ack:' + tello.PORT_TELLO_VIDEO.to_bytes(2, byteorder='little')):
                return cls(tello.CMD_ID_CONN_ACK, 0)
            logging.error(f"Mismatched Video Ports (Expected - Actual): {tello.PORT_TELLO_VIDEO} - "
                          f"{int.from_bytes(raw[-2:], byteorder='little')}")
        return SocketPacket(-1, -1, -1, None)


class AdvancedTello:
    CMD_ID_CONN_REQ = 1
    CMD_ID_CONN_ACK = 2
    CMD_ID_VIDEO_STUFF = 37  # TODO Figure out what this is
    CMD_ID_TIME_REQ = 70
    CMD_ID_JOYSTICK = 80
    CMD_ID_TAKE_OFF = 84
    CMD_ID_LAND = 85
    CMD_ID_FLIP = 92
    CMD_ID_ALT_LIMIT = 4182

    PORT_TELLO_CMD = 8889
    PORT_TELLO_VIDEO = 6037

    def __init__(self, tello_ip='192.168.10.1', tello_port=None):
        if tello_port is None:
            tello_port = self.PORT_TELLO_CMD
        self.tello_address = tello_ip, tello_port

        # SO_REUSEADDR to send "emergency" commands etc while socket is busy
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.thread_cmd_receiver = threading.Thread(target=self._receive_cmds)
        self.thread_cmd_receiver.daemon = True
        self.thread_cmd_receiver.start()

        self.seq_num = 0
        self.joystick_data = 0
        self.joystick_emitter = RepeatedTimer(0.02, self._emit_joystick_data)

    def __del__(self):
        self.socket.close()
        self.joystick_emitter.stop()

    def connect(self):
        self._send_packet(SocketPacket(self.CMD_ID_CONN_REQ, 0))

    def take_off(self):
        self._send_packet(SocketPacket(self.CMD_ID_TAKE_OFF, 104))

    def land(self):
        self._send_packet(SocketPacket(self.CMD_ID_LAND, 104, data=bytearray(b'\x00')))

    def flip(self, direction=0):
        assert direction in range(8)
        self._send_packet(SocketPacket(self.CMD_ID_FLIP, 112, data=bytearray([direction])))

    def start_joystick(self):
        self.joystick_emitter.start()

    def stop_joystick(self):
        self.joystick_emitter.stop()
        self.update_joystick(1024, 1024, 1024, 1024, 0)
        self._emit_joystick_data()

    def update_joystick(self, roll, pitch, throttle, yaw, speed_mode=0):
        """Values for roll, pitch, throttle, yaw:
                Min (movement on corresponding axis): 364
                ...
                Normal (no movement on corresponding axis): 1024
                ...
                Max (movement on corresponding axis): 1684
            speed_mode: 0 or 1 (0 is slow, 1 is fast)
        """
        self.joystick_data = ((roll & 2047) | ((pitch & 2047) << 11)) | ((2047 & throttle) << 22) \
                             | ((2047 & yaw) << 33) | (speed_mode << 44)

    def _receive_cmds(self):
        while True:
            try:
                data, _ = self.socket.recvfrom(1024)
                packet = SocketPacket.from_raw_bytes(self, data)
                self._handle_received_packet(packet)
            except socket.error:
                logging.error("Command Socket Failed")

    def _emit_joystick_data(self):
        self._send_packet(SocketPacket(self.CMD_ID_JOYSTICK, 96))

    def _handle_received_packet(self, packet):
        if packet.cmd_id == self.CMD_ID_CONN_ACK:
            logging.debug("Successfully connected to Tello")
        elif packet.cmd_id == self.CMD_ID_TIME_REQ:
            self._send_packet(SocketPacket(self.CMD_ID_TIME_REQ, 80))
        # logging.debug(f"Received Command {packet.cmd_id}")

    # Mostly found in com.ryzerobotics.tello.gcs.core.cmd.d (ZOCmdStore)
    def _send_packet(self, packet: SocketPacket):
        """Sends packets, intercepts Commands that need special treatment (CMD_ID_CONN_REQ) etc."""
        raw = None
        data = None
        seq = 0

        if packet.cmd_id == self.CMD_ID_CONN_REQ:
            raw = bytearray(b'conn_req:' + self.PORT_TELLO_VIDEO.to_bytes(2, byteorder='little'))
            self.seq_num += 1

        elif packet.cmd_id == self.CMD_ID_TIME_REQ:
            dt = datetime.now()
            # First Byte empty (0)
            data = bytearray(b'\x00' +
                             dt.year.to_bytes(2, byteorder='little') +
                             dt.month.to_bytes(2, byteorder='little') +
                             dt.day.to_bytes(2, byteorder='little') +
                             dt.hour.to_bytes(2, byteorder='little') +
                             dt.minute.to_bytes(2, byteorder='little') +
                             dt.second.to_bytes(2, byteorder='little') +
                             (dt.microsecond & 0xffff).to_bytes(2, byteorder='little'))

            seq = self.seq_num
            self.seq_num += 1

        elif packet.cmd_id == self.CMD_ID_JOYSTICK:
            dt = datetime.now()
            data = bytearray(11)
            data[:6] = self.joystick_data.to_bytes(6, byteorder='little')
            data[6] = dt.hour
            data[7] = dt.minute
            data[8] = dt.second
            data[9:11] = (dt.microsecond & 0xffff).to_bytes(2, byteorder='little')

        elif packet.cmd_id == self.CMD_ID_VIDEO_STUFF:
            # seq should be 0 for this packet
            seq = 0
        else:
            seq = self.seq_num
            self.seq_num += 1

        if raw is None:
            raw = packet.to_raw_bytes(seq, data)
        self.socket.sendto(raw, self.tello_address)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
