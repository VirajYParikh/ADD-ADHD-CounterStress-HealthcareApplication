import argparse
import os.path
import sys
import fileinput

from constants import cli_modes
import RobothonHandler


class CLIDriver:

    event_id = None

    def __init__(self, *args, **kwargs):
        kwargs2 = kwargs.copy()
        time = kwargs2["time"]
        mode = kwargs2["mode"]
        self.event_id = kwargs2['event_id']
        print('\nRobothons - Healthcare Competition Platform (CLI)')
        if "event_id" in kwargs2:
            self.event_id = kwargs2['event_id']
            self.cli_terminal_selection(time=time,
                                        mode=mode,
                                        event_id=self.event_id)
        else:
            self.cli_terminal_selection(time=time, mode=mode)

    def print_help(self):
        print(
            'usage: python CLIDriver.py [-h] [-time [TIME]] [-mode [MODE]] [-event_id [EVENT_ID]]'
        )
        print('optional arguments:')
        print('-h, --help            : display this help message and exit')
        print('-time [TIME]          : number of times to enter modes')
        print('-mode [MODE]          : robothon competition mode')
        print('-event_id [EVENT_ID]  : robothon competition event ID')

    def cli_terminal_selection(self, *args, **kwargs):
        time = kwargs["time"]
        selected_mode = kwargs["mode"]
        if time == 'single':
            self.mode_selection(selected_mode)
        elif time == 'multiple':
            while True:
                self.print_mode_selection()
                selected_mode = input('Enter mode:\n')
                self.mode_selection(selected_mode)

    def mode_selection(self, mode):
        if mode == 'help' or mode == str(cli_modes.HELP):
            self.print_help()
        elif mode == 'start' or mode == str(cli_modes.START_SERVER):
            handler.startAllServerProcesses()
        elif mode == 'stop' or mode == str(cli_modes.STOP_SERVER):
            handler.stopAllServerProcesses()
        elif mode == 'download' or mode == str(cli_modes.DOWNLOAD_BOTS):
            handler.downloadBots(event_id=self.event_id)
        elif mode == 'validate' or mode == str(cli_modes.VALIDATE_BOTS):
            handler.validateBots(event_id=self.event_id)
        elif mode == 'run' or mode == str(cli_modes.RUN_BOTS):
            handler.runBots()
        elif mode == 'results' or mode == str(cli_modes.CALC_RESULTS):
            handler.calculateResults()
        elif mode == 'delete' or mode == str(cli_modes.DELETE_BOTS):
            handler.deleteBots()
        elif mode == 'test' or mode == str(cli_modes.RUN_TEST):
            handler.runFullTest()
        elif mode == 'testenv' or mode == str(cli_modes.RUN_TEST_ENVIRONMENT):
            handler.runSandboxEnv(event_id=self.event_id)
        elif mode == 'exit' or mode == str(cli_modes.EXIT_TERMINAL):
            print('Exited terminal')
            sys.exit(0)

    def print_mode_selection(self):
        print(""" 
            Help Menu:
            Help (1)     : display help menu
            
            Manage Server Menu:
            start (2)    : start all server processes, logged to server.log (Ex: python CLIDriver.py -mode 2)
            stop (3)     : stop all server processes and store data (Ex: python CLIDriver.py -mode 3)

            Manage Robothon Phases Menu:
            download (4) : download bot files from GitHub links (Ex: python CLIDriver.py -mode 4 -event_id 1)
            validate (5) : validate bots (Ex: python CLIDriver.py -mode 5 -event_id 1)
            run (6)      : run bots
            results (7)  : calculate and publish results
            test (8)     : run full test
            delete (9)   : delete bots
            
            Test Sandbox Environment Menu:
            run (10)     : run bots in test environment (Ex: python CLIDriver.py -mode 10 -event_id 1)
            
            Exit CLI:
            exit (11)     : exit this terminal
            """)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-time',
                        type=str,
                        const="single",
                        nargs='?',
                        default='single',
                        help='times')
    parser.add_argument('-mode',
                        type=str,
                        const="help",
                        nargs='?',
                        default='help',
                        help='mode')
    parser.add_argument('-event_id',
                        type=str,
                        const='1',
                        nargs='?',
                        default='1')
    args = parser.parse_args()
    handler = RobothonHandler.RobothonHandler()
    CLIDriver(time=args.time, mode=args.mode, event_id=args.event_id)