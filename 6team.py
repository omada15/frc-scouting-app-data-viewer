import pieceviewer as pv
import logger

red = [
    9998,
    9997,
    9996,
]
blue = [
    9995,
    9994,
    9993
]
logger.log(f"Viewing teams: Red {red}, Blue {blue}")
pv.view(red + blue, True)