# Put in polls/management/commands/runserver.py
from django.core.management.commands.runserver import Command as RunServer


class Command(RunServer):
    def inner_run(self, *args, **options):
        self.pre_start()
        super().inner_run(*args, **options)
        self.pre_quit()

    def pre_start(self):
        print("Pre-Start")

    def pre_quit(self):
        print("Pre-Quit")