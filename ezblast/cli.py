import argparse
import configparser
import os
import sys

from ezblast import backend


class HelpParser(argparse.ArgumentParser):

    def error(self, message):
        sys.stderr.write('error {}\n'.format(message))
        self.print_help()
        sys.exit(2)


class EZBlastCLI:

    def __init__(self):
        self.apikey = None

    @staticmethod
    def _find_config_path():
        return os.path.join(os.path.expanduser('~'), '.ezblast')

    @staticmethod
    def _write_config(apikey):
        config = configparser.ConfigParser()
        config['default'] = {
            'api_key': apikey
        }
        path = EZBlastCLI._find_config_path()
        with open(path, 'w') as f:
            config.write(f)
        print('Configuration written to \'{}\''.format(path))

    def _find_config(self, args):
        path = self._find_config_path()
        if not os.path.exists(path):
            self.configure(args)

        config = configparser.ConfigParser()
        config.read(self._find_config_path())
        default = config['default']
        return default

    def create_parser(self):
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(
            title='subcommands', parser_class=HelpParser)

        # Create command to configure api key
        config = subparsers.add_parser('config',
            help='configure ncbi credentials')
        config.set_defaults(callback=self.configure)

        query = subparsers.add_parser('query',
            help='run ncbi blast')
        query.set_defaults(callback=self.query)
        query.add_argument('input_path', type=str,
            help='Path to fasta file holding query sequence')
        query.add_argument('output_path', type=str,
            help='Directory to store outputs')
        query.add_argument('-f', '--format', type=str,
            dest='output_format', help='Output data format',
            choices=backend.output_formats, default='json')
        query.add_argument('-d', '--db', '--database',
            dest='database', help='NCBI Database to query from',
            type=str, choices=backend.databases, default='nt')
        query.add_argument('-p', '--prog', '--program',
            dest='program', help='BLAST program', type=str,
            choices=backend.programs, default='blastn')
        query.add_argument('-m', '--megablast',
            help='Enable Megablast', action='store_true')

        return parser

    def configure(self, args):
        api_key = input('Enter ncbi BLAST api key: ')
        self._write_config(api_key)
        self.apikey = apikey
        return 0

    def query(self, args):
        config = self._find_config(args)
        return backend.blast(**vars(args), **config)


def main():
    cli = EZBlastCLI()
    parser = cli.create_parser()
    if len(sys.argv) == 1:
        parser.print_help()
        return 2
    
    args = parser.parse_args()
    return args.callback(args)
