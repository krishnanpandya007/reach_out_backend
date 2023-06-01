from subprocess import Popen, PIPE
import logging

logger = logging.getLogger(__name__)


def start_memcahced_server():

    '''
    @requires ROOT/ADMIN PERMISSION
    '''

    process = Popen("c:\memcached\memcached.exe -d start", shell=True, stdout=PIPE)
    process.wait()
    status_code = process.returncode
    if(status_code != 0):
        logging.error('Failed to load memCache server')
        print("[FAILED]: fail to load memCache server")


def stop_memcahced_server():

    '''
    @requires ROOT/ADMIN PERMISSION
    '''

    process = Popen("c:\memcached\memcached.exe -d stop", shell=True, stdout=PIPE)
    process.wait()
    status_code = process.returncode
    if(status_code != 0):
        logging.error('Failed to stop memCache server')
        print("[FAILED]: fail to stop memCache server")

if (__name__ == "__main__"):
    start_memcahced_server()