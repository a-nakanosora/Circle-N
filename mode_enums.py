from enum import Enum

class CommandMode(Enum):
    FINISH = 0
    PASS = 1
    PREVENT_DEFAULT = 2
    MODAL = 3
    CANCEL = 3.1
    SWITCH_OPERATION_TOGGLE = 4
    SWITCH_OPERATION_TO_MOVE = 5
    SWITCH_OPERATION_TO_ROT = 6
    SWITCH_OPERATION_TO_SCALE = 7

class CNMoveMode(Enum):
    DIR = 0
    UV = 1
    N = 2
    CAPTURE_N = 3

class CNRotMode(Enum):
    DIR = 0
    DIR_ROT = 1
    UV_ROT = 2
    CAPTURE_N = 3

class CNScaleMode(Enum):
    DIR = 0
    N_SCALE = 1
    UV_SCALE = 2
    CAPTURE_N = 3