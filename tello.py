import logging
import queue
import socket
import threading
import time

from utils import validate_bounds as validate, try_to_int, AtomicInteger
from abc import ABC, abstractmethod


class DroneInterface(ABC):
    TELLO_COMMAND_PORT = 8889
    TELLO_VIDEO_PORT = 11111
    TELLO_STATE_PORT = 8890

    def __init__(self, local_ip='', local_port=8889, state_interval=0.2, command_timeout=3.0, move_timeout=15.0,
                 tello_ip='192.168.10.1'):

        self.state_interval = state_interval
        self.command_timeout = command_timeout
        self.move_timeout = move_timeout

        self.response_queue = queue.Queue(1)
        self.scheduled_responses = AtomicInteger()
        self.states = {}

        self.tello_address = (tello_ip, self.TELLO_COMMAND_PORT)
        self.local_state_port = self.TELLO_STATE_PORT
        self.local_video_port = self.TELLO_VIDEO_PORT

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket_state = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.socket.bind((local_ip, local_port))
        self.socket_state.bind((local_ip, self.local_state_port))

        self.receive_ack_thread = threading.Thread(target=self._receive_ack)
        self.receive_ack_thread.daemon = True
        self.receive_ack_thread.start()
        self.receive_state_thread = threading.Thread(target=self._receive_state)
        self.receive_state_thread.daemon = True
        self.receive_state_thread.start()

    def __del__(self):
        self.socket.close()
        self.socket_state.close()

    def _receive_ack(self):
        while True:
            try:
                data, _ = self.socket.recvfrom(1518)
                if data:
                    if self.scheduled_responses.value == 0:
                        self.response_queue.put(data.decode(encoding='utf-8'))
                    else:
                        self.scheduled_responses.dec()
                        logging.warning('Not Putting Response into Queue. Response probably from other Command that '
                                        f'timed out (Response Value: {data})')
            except socket.error:
                logging.error('Ack Socket Failed')
            except UnicodeDecodeError:
                logging.error('Illegal Answer?')

    def _receive_state(self):
        while True:
            try:
                data, ip = self.socket_state.recvfrom(1024)
                if data:
                    data = data.decode(encoding='utf-8')
                    if ';' in data:
                        states = data.replace(';\r\n', '').split(';')
                        self.states = {s[0]: s[1] for s in map(lambda item: item.split(':'), states)}

                time.sleep(self.state_interval)
            except socket.error:
                logging.error('State Socket Failed')
            except UnicodeDecodeError:
                logging.error('Illegal Answer?')

    def send_command(self, command, command_timeout=None, none_response=False):
        if command_timeout is None:
            command_timeout = self.command_timeout
        print('>> Send Command:', command)

        self.socket.sendto(command.encode(encoding='utf-8'), self.tello_address)

        if none_response:
            logging.debug(f'Not awaiting response for command {command}')
            return 'ok'
        try:
            command_response = self.response_queue.get(timeout=command_timeout)
        except queue.Empty:
            logging.error("Empty Response Queue")
            self.scheduled_responses.inc()
            command_response = "none_response"

        if command.endswith("?"):
            command_response = command_response.replace("\r\n", "")

        logging.debug(command_response)
        return command_response

    @abstractmethod
    def get_sdk_name(self):
        pass


class Drone1_3(DroneInterface):
    def get_sdk_name(self):
        return "1.3"

    def enter_sdk_mode(self):
        return self.send_command('command')

    def start_stream(self):
        return self.send_command('streamon')

    def stop_stream(self):
        return self.send_command('streamoff')

    def take_off(self):
        return self.send_command('takeoff', self.move_timeout)

    def land(self):
        return self.send_command('land', self.move_timeout)

    def emergency(self):
        return self.send_command('emergency', none_response=True)  # For some reason does not send any response

    def _move(self, direction, distance):
        return self.send_command(f'{direction} {self._validate_move_distance(distance)}', self.move_timeout)

    def move_backward(self, distance):
        return self._move('back', distance)

    def move_forward(self, distance):
        return self._move('forward', distance)

    def move_left(self, distance):
        return self._move('left', distance)

    def move_right(self, distance):
        return self._move('right', distance)

    def move_up(self, distance):
        return self._move('up', distance)

    def move_down(self, distance):
        return self._move('down', distance)

    def _turn(self, direction, degree):
        return self.send_command(f'{direction} {self._validate_degree(degree)}', self.move_timeout)

    def clockwise(self, degree):
        return self._turn('cw', degree)

    def counter_clockwise(self, degree):
        return self._turn('ccw', degree)

    def _flip(self, direction):
        return self.send_command(f'flip {direction}')

    def flip_left(self):
        return self._flip('l')

    def flip_right(self):
        return self._flip('r')

    def flip_forward(self):
        return self._flip('f')

    def flip_backward(self):
        return self._flip('b')

    def go_location(self, x, y, z, speed):
        return self.send_command(self._go_location_command(x, y, z, speed), self.move_timeout)

    def curve(self, x1, y1, z1, x2, y2, z2, speed):
        return self.send_command(self._curve_command(x1, y1, z1, x2, y2, z2, speed), self.move_timeout)

    def set_speed(self, speed):
        return self.send_command(f'speed {validate(speed, 10, 100)}')

    def set_rc(self, a, b, c, d):
        for x in (a, b, c, d):
            assert -100 < x < 100
        return self.send_command(f'rc {a} {b} {c} {d}')

    def set_wifi_password(self, ssid, passwd):
        return self.send_command(f'wifi {ssid} {passwd}')

    def get_speed(self):  # Unit: cm/s
        return try_to_int(self.send_command('speed?'))

    def get_battery(self):  # Unit: %
        return try_to_int(self.send_command('battery?'))

    def get_flight_time(self):  # Unit: s
        return try_to_int(self.send_command('time?'))

    def get_height(self):  # Unit: cm
        return try_to_int(self.send_command('height?'))

    def get_temp(self):  # Unit: °C
        return try_to_int(self.send_command('temp?'))

    def get_attitude(self):  # IMU Attitude Data
        return self.send_command('attitude?')

    def get_barometer(self):  # Unit: m
        return self.send_command('baro?')

    def get_acceleration(self):  # Unit: 0.001g
        return self.send_command('acceleration?')

    def get_tof_distance(self):
        return self.send_command('tof?')

    def get_wifi_snr(self):
        return self.send_command('wifi?')

    def get_last_states(self):
        return self.states

    def _validate_distance(self, dist):
        return validate(dist, 20, 500)

    def _validate_move_distance(self, dist):
        return validate(dist, 20, 500)

    def _validate_degree(self, degree):
        return validate(degree, 1, 3600)

    def _go_location_command(self, x, y, z, speed):
        dist = ' '.join(map(self._validate_distance, (x, y, z)))

        return f'go {dist} {validate(speed, 10, 100)}'

    def _curve_command(self, x1, y1, z1, x2, y2, z2, speed):
        dist = ' '.join(map(self._validate_distance, (x1, y1, z1, x2, y2, z2)))

        return f'curve {dist} {validate(speed, 10, 60)}'


class Drone2_0(Drone1_3):
    def get_sdk_name(self):
        return "2.0"

    def _turn(self, direction, degree):
        return self.send_command(f'{direction} {validate(degree, 1, 360)}', self.move_timeout)

    def stop(self):
        return self.send_command('stop')

    def _validate_distance(self, dist):
        return validate(dist, -500, 500)

    def _validate_degree(self, degree):
        return validate(degree, 1, 360)

    def go_location(self, x, y, z, speed):
        assert not all(map(lambda i: -20 < i < 20, (x, y, z)))

        return super().go_location(x, y, z, speed)

    def start_mpd(self):
        return self.send_command("mon")

    def stop_mpd(self):
        return self.send_command("moff")

    def mpd_direction(self, x):
        assert x in range(3)
        return self.send_command(f"mdirection {x}")

    def connect_ap(self, ssid, passwd):
        return self.send_command(f"ap {ssid} {passwd}")

    def jump(self, x, y, z, speed, yaw, mid1, mid2):
        _assert_mid(mid1, mid2)
        dist = ' '.join(map(self._validate_distance, (x, y, z)))

        return self.send_command(f'{dist}, {validate(speed, 10, 100)}, {yaw}, {mid1}, {mid2}')

    def curve_mpd(self, x1, y1, z1, x2, y2, z2, speed, mid):
        _assert_mid(mid)
        return self.send_command(f'{self._curve_command(x1, y1, z1, x2, y2, z2, speed)} {mid}', self.move_timeout)

    def go_location_mpd(self, x, y, z, speed, mid):
        _assert_mid(mid)
        return self.send_command(f'{self._go_location_command(x, y, z, speed)} {mid}', self.move_timeout)


def _assert_mid(*mids):
    pads = map(lambda i: f'm{i}', range(1, 9))
    for mid in mids:
        assert mid in pads


logging.basicConfig(level=logging.DEBUG)
