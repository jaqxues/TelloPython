import logging
import queue
import socket
import threading
import time

from utils import send_wrapper, command_wrapper


def _try_to_int(value):
    try:
        value = int(value)
    except ValueError:
        pass
    return value


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

    @send_wrapper
    def enter_sdk_mode(self):
        return 'command'

    @send_wrapper
    def start_stream(self):
        return 'streamon'

    @send_wrapper
    def stop_stream(self):
        return 'streamoff'

    @command_wrapper(command_timeout=10)
    def take_off(self):
        return 'takeoff'

    @command_wrapper(command_timeout=10)
    def land(self):
        return 'land'

    @send_wrapper
    def emergency(self):
        return 'emergency'

    @send_wrapper
    def move_backward(self, distance):
        return f'back {distance}'

    @send_wrapper
    def move_forward(self, distance):
        return f'forward {distance}'

    @send_wrapper
    def move_left(self, distance):
        return f'left {distance}'

    @send_wrapper
    def move_right(self, distance):
        return f'right {distance}'

    @send_wrapper
    def move_up(self, distance):
        return f'up {distance}'

    @send_wrapper
    def move_down(self, distance):
        return f'down {distance}'

    @command_wrapper(to_validate=(('degree',), 1, 3600))
    def clockwise(self, degree):
        return f'cw {degree}'

    @command_wrapper(to_validate=(('degree',), 1, 3600))
    def counter_clockwise(self, degree):
        return f'ccw {degree}'

    @send_wrapper
    def flip_left(self):
        return f'flip l'

    @send_wrapper
    def flip_right(self):
        return f'flip r'

    @send_wrapper
    def flip_forward(self):
        return 'flip f'

    @command_wrapper
    def flip_backward(self):
        return f'flip b'

    @command_wrapper(to_validate=(
            (('x', 'y', 'z'), 20, 500),
            (('speed',), 10, 100)))
    def go_location(self, x, y, z, speed):
        return f'go {x} {y} {z} {speed}'

    @command_wrapper(to_validate=(
            (('x1', 'x2', 'y1', 'y2', 'z1', 'z2'), 20, 500),
            (('speed',), 10, 60)))
    def curve(self, x1, y1, z1, x2, y2, z2, speed):
        return f'curve {x1} {y1} {z1} {x2} {y2} {z2} {speed}'

    @command_wrapper(to_validate=(('speed',), 10, 100))
    def set_speed(self, speed):
        return f'speed {speed}'

    @send_wrapper
    def set_rc(self, a, b, c, d):
        return f'rc {a} {b} {c} {d}'

    @send_wrapper
    def set_wifi_password(self, ssid, passwd):
        return f'wifi {ssid} {passwd}'

    @command_wrapper(result_conversion=_try_to_int)
    def get_speed(self):  # Unit: cm/s
        return 'speed?'

    @command_wrapper(result_conversion=_try_to_int)
    def get_battery(self):  # Unit: %
        return 'battery?'

    @command_wrapper(result_conversion=_try_to_int)
    def get_flight_time(self):  # Unit: s
        return 'time?'

    @command_wrapper(result_conversion=_try_to_int)
    def get_height(self):  # Unit: cm
        return 'height?'

    @command_wrapper(result_conversion=_try_to_int)
    def get_temp(self):  # Unit: °C
        return 'temp?'

    @send_wrapper
    def get_attitude(self):  # IMU Attitude Data
        return 'attitude?'

    @send_wrapper
    def get_barometer(self):  # Unit: m
        return 'baro?'

    @send_wrapper
    def get_acceleration(self):  # Unit: 0.001g
        return 'acceleration?'

    @command_wrapper(result_conversion=_try_to_int)
    def get_tof_distance(self):  # Unit: cm
        return 'tof?'

    @send_wrapper
    def get_wifi_snr(self):
        return 'wifi?'

    def get_last_states(self):
        return self.states


drone = Drone()
drone.enter_sdk_mode()
drone.take_off()
drone.land()
