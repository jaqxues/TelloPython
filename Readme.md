# TelloPython
Rewriting Tello Python Apis for Python3

## Structure
* The Tello App does not send Strings (e. g. "land" or "takeoff" to the Drone). Instead it sends Command Ids to the 
  drone (shorts). To find the ids:
    * In the Tello App, they can be found in classes extending "com.ryzerobotics.tello.gcs.core.cmd.e". (You can run
      the scripts in `dev_utils.py` to find Command Ids used in comparations. A more complete list (still maybe not all ids
      can be found in `cmd_ids`)
    * With Xposed, you can hook every method of the classes extending "e". Check what Id gets sent when using different
      features. (Takeoff, land etc.)
    * Similarky, you can hook the constructor of the class `com.ryzerobotics.tello.gcs.core.c` ("ZOCmdParser") and log 
      the `cmdId` field of the result of method `com.ryzerobotics.tello.gcs.ui.bean.SocketPacketEntity a(byte[], int)`. 
      Note that the `byte[]` sometimes contains useful information in form of text.
* The `SocketPacketEntitiy` class contains different fields that you need to figure out before sending any command. To
  log the values of the arguments, I used the Xposed Framework (though you can probably figure it out with Wireshark):
    * cmdId: int
    * data: byte[]
    * pactype: int
    * seqnum: short
    * version: int
