from django.apps import AppConfig
from global_utils.startup import start_memcahced_server


class Auth2Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'auth2'

    def ready(self) -> None:
        
        import auth2.signals
        # Load/Start MemCached server at 127.0.0.1:11211
        start_memcahced_server()

