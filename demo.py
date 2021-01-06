import time

import keyboard

from advanced_tello import AdvancedTello

'''
Troubleshooting Step - In case the drone does not respond to any commands via the 'advanced' API

Just setting up the sockets and listeners from the initial API should be enough to make it respond to the advanced API
'''
# If not needed, you can comment the following lines
from tello import Drone1_3
Drone1_3()

drone = AdvancedTello()
drone.connect()
drone.start_joystick()
drone.update_joystick(1024, 1024, 1024, 1024, 0)

keys = {
    'd': (0, +1),
    'a': (0, -1),
    'w': (1, +1),
    's': (1, -1),
    'i': (2, +1),
    'k': (2, -1),
    'l': (3, +1),
    'j': (3, -1)
}

flip_keys = {
    8: 0,
    9: 4,
    6: 3,
    3: 5,
    2: 2,
    1: 6,
    4: 1,
    7: 7
}

print('''
Starting demo. Listing Controls

Using Joystick via keys:

Takeoff: Space
Land   : Q
Close  : P

Directional Movement
* W  /  S    -    Forwards           /  Backwards
* A  /  D    -    Left               /  Right
* I  /  K    -    Up                 /  Down
* J  /  L    -    Counter-clockwise  /  Clockwise

Flip via NumPad keys (or conventional number keys):
-------------------------------------------------------------------------------
| 7    Diagonal Front-Left    | 8    Front    | 9     Diagonal Front-Right    |
-------------------------------------------------------------------------------
| 4    Left                   | 5             | 6     Right                   |
-------------------------------------------------------------------------------
| 1    Diagonal Back-Left     | 2    Back     | 3     Diagonal Front-Left     |
-------------------------------------------------------------------------------
''')

while True:
    vals = [1024] * 4
    for key, (idx, i) in keys.items():
        if keyboard.is_pressed(key):
            vals[idx] += 660 * i
    for key, i in flip_keys.items():
        if keyboard.is_pressed(str(key)):
            drone.flip(i)
    drone.update_joystick(*vals, 0)
    if keyboard.is_pressed('space'):
        drone.take_off()
    if (e := keyboard.is_pressed('p')) or keyboard.is_pressed('q'):
        drone.stop_joystick()
        drone.land()
        if e:
            break
    time.sleep(0.02)

###############################################
# Previous Tests
###############################################

# from tello import Drone1_3
#
# drone = Drone1_3()
# drone.enter_sdk_mode()
# print(drone.get_battery())
# drone.start_stream()
#
#
# def record_video():
#     cap = cv2.VideoCapture("udp://@0.0.0.0:11111")
#     writer = cv2.VideoWriter("output.avi", cv2.VideoWriter_fourcc(*'MJPG'), 25, (960, 720))
#     while True:
#         ret, frame = cap.read()
#         try:
#             writer.write(frame)
#             # frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#             cv2.imshow('Frame', frame)
#             if cv2.waitKey(1) & 0xFF == ord('q'):
#                 break
#         except:
#             break
#
#     writer.release()
#     cap.release()
#     cv2.destroyAllWindows()
#
#
# record_video()>

# counter = 0
# colors = filter(lambda x: x.startswith("COLOR"), dir(cv2))
# NUMBER_FRAMES = 100
#
#         gray = cv2.cvtColor(frame, getattr(cv2, color))
#         # Display the resulting frame
#         cv2.imshow('frame', gray)
#         if cv2.waitKey(1) & 0xFF == ord('q'):
#             break
#         if cv2.waitKey(1) & 0xFF == ord('s'):
#             print(color)
#     except Exception as e:
#         continue
#     ret, frame = cap.read()
#
# for x in filter(lambda x: x.startswith("CAP_PROP"), dir(cv2)):
#     print(x, cap.get(getattr(cv2, x)))
#
# # When everything done, release the capture
# cap.release()
# cv2.destroyAllWindows()

# from itertools import count

#
# for i in count():
#     try:
#         print(drone.send_command(input(f"Enter Command ({i}): ")), 15)
#     except KeyboardInterrupt:
#         drone.land()
#         break
