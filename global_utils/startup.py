from subprocess import Popen, PIPE
from django.conf import settings
import sys
if(settings.BASE_DIR not in sys.path): sys.path.append(settings.BASE_DIR)
from constants import MEMCACHED_SERVICE_ENABLED
import logging

logger = logging.getLogger(__name__)


def start_memcahced_server():

    '''
    @requires ROOT/ADMIN PERMISSION
    '''
    if(not MEMCACHED_SERVICE_ENABLED):
        print("[FAILED]: to Start memcached:: constants.py/MEMCACHED_SERVICE_ENABLED=False")
        return
    process = Popen("systemctl start memcached", shell=True, stdout=PIPE)
    process.wait()
    status_code = process.returncode
    if(status_code != 0):
        logging.error('Failed to load memCache server')
        print("[FAILED]: fail to load memCache server")


def stop_memcahced_server():

    '''
    @requires ROOT/ADMIN PERMISSION
    '''
    if(not MEMCACHED_SERVICE_ENABLED):
        print("[FAILED]: to Stop memcached:: constants.py/MEMCACHED_SERVICE_ENABLED=False")
        return

    process = Popen("systemctl stop memcached", shell=True, stdout=PIPE)
    process.wait()
    status_code = process.returncode
    if(status_code != 0):
        logging.error('Failed to stop memCache server')
        print("[FAILED]: fail to stop memCache server")

if (__name__ == "__main__"):
    start_memcahced_server()