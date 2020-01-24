# TelloPython
Rewriting Tello Python Apis for Python3

## Structure
* The Tello App does not send Strings (e. g. "land" or "takeoff" to the Drone). Instead it sends Command Ids to the 
  drone (shorts). To find the ids:
* The `SocketPacketEntitiy` class contains different fields that you need to figure out before sending any command. To
  log the values of the arguments, I used the Xposed Framework (though you can probably figure it out with Wireshark):
    * cmdId: int
    * data: byte[]
    * pactype: int
    * seqnum: short
    * version: int

## How to find these Command Ids etc
* In the Tello App, the raw ids can be found in classes extending `com.ryzerobotics.tello.gcs.core.cmd.e`. (You can run
  the scripts in `dev_utils.py` to find Command Ids used in comparisons. These script need a decompiled Tello Folder
  (preferably from Jadx). A more complete list (still maybe not all ids) can be found in `cmd_ids`
* You should be able to figure out some Commands by having a look at the class `com.ryzerobotics.tello.gcs.core.cmd.c`
  ("ZOCmdStore")
* By setting the Tello Application to `UserDebuggable` you can figure out the ids of the buttons and search for their
  `onClickListener` (done to find `flip` command)
* With Xposed, you can hook every method of the classes extending `e`. Check what Id gets sent when using different
  features. (Takeoff, land etc.). A simpler way (less complete) would be hooking the before mentioned"ZOCmdStore" class.
* Similarly, you can hook the constructor of the class `com.ryzerobotics.tello.gcs.core.c` ("ZOCmdParser") and log 
  the `cmdId` field of the result of method `com.ryzerobotics.tello.gcs.ui.bean.SocketPacketEntity a(byte[], int)`. 
  Note that the `byte[]` sometimes contains useful information in form of text.

## Using the Joystick command
The joystick is handled by `com.ryzerobotics.tello.gcs.core.cmd.d.a(int, int, long, long, long)`
Values are set using Commands in "ZOCmdSendManager". Chinese names for the values are mentioned in log statements with 
tag "yaogan" - "Joystick"). You can understand their meaning by Trial and Error or hooking the Tello App and seeing
what values are passed to the method when using the Joystick in app.

| Chinese names | Directions                   | Name     |
| ------------- |:-----------------------------| :--------|
| zuoYou        | right - left                 | roll     |
| qianHou       | forward - backward           | pitch    |
| shangXia      | up - down                    | throttle |
| xuanZhan      | clockwise - counterclockwise | yaw      |

The last `long` argument does not have a specific name. This `speed_mode` variable is either 0 (slow mode) or 1 (quick 
mode). The values of the other arguments are ints between 364 - 1684 (both included).

* Min (movement on corresponding axis): 364
* ...
* Normal (no movement on corresponding axis): 1024
* ...
* Max (movement on corresponding axis): 1684

Speed per axis given by `abs(1024 - x)`. Direction on axis given by `x > 1024`
