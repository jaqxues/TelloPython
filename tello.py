import logging
import queue
import socket
import threading
import time
from utils import validate_bounds as validate, try_to_int


class Drone:
    TELLO_COMMAND_PORT = 8889
    TELLO_VIDEO_PORT = 11111
    TELLO_STATE_PORT = 8890

    def __init__(self, local_ip='', local_port=8889, state_interval=0.2, command_timeout=5.0, tello_ip='192.168.10.1'):

        self.state_interval = state_interval
        self.command_timeout = command_timeout

        self.response_queue = queue.Queue(1)
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
                print(data)
                if data:
                    self.response_queue.put(data.decode(encoding='utf-8'))
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

    def send_command(self, command, command_timeout=None):
        if command_timeout is None:
            command_timeout = self.command_timeout
        print('>> Send Command:', command)

        self.socket.sendto(command.encode(encoding='utf-8'), self.tello_address)

        try:
            command_response = self.response_queue.get(timeout=command_timeout)
        except queue.Empty:
            logging.error("Empty Response Queue")
            command_response = "none_response"

        return command_response

    def enter_sdk_mode(self):
        return self.send_command('command')

    def start_stream(self):
        return self.send_command('streamon')

    def stop_stream(self):
        return self.send_command('streamoff')

    def take_off(self):
        return self.send_command('takeoff', 10)  # Takeoff Command takes longer than other Commands

    def land(self):
        return self.send_command('land', 10)  # Land Command can take longer than other Commands

    def emergency(self):
        return self.send_command('emergency')

    def _move(self, direction, distance):
        return self.send_command(f'{direction} {validate(distance, 20, 500)}')

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
        return self.send_command(f'{direction} {validate(degree, 1, 3600)}')

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
        def vd(distance): 
            return validate(distance, 20, 500)
        return self.send_command(f'go {vd(x)} {vd(y)} {vd(z)} {speed}')

    def curve(self, x1, y1, z1, x2, y2, z2, speed):
        def vd(distance): 
            return validate(distance, 20, 500)
        return self.send_command(f'curve {vd(x1)} {vd(y1)} {vd(z1)} {vd(x2)} {vd(y2)} {vd(z2)} {speed}')

    def set_speed(self, speed):
        return self.send_command(f'speed {validate(speed, 10, 100)}')

    def set_rc(self, a, b, c, d):
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

    def get_tof_distance(self):  # Unit: cm
        return self.send_command('tof?')

    def get_wifi_snr(self):
        return self.send_command('wifi?')

    def get_last_states(self):
        return self.states
