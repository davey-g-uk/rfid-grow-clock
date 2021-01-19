from libs.iocontrol import iocontrol
from libs.threadcontrol import threadcontrol
import signal
import sys

testmech = iocontrol()
def signal_handler(sig, frame):
    testmech.cleanup()
    sys.exit()

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    signal.pause()