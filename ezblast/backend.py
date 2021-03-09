import io
import logging
import re
import time
import urllib
import zipfile

from html.parser import HTMLParser
from pprint import pprint


output_formats = [
    'json', 'text', 'xml',
    'xml2', 'html', 'tab'
]

databases = [
    'nt', 'nr',
    'refseq_rna',
    'refseq_protein',
    'swissprot',
    'pdbaa',
    'pdbnt'
]

programs = [
    'blastn',
    'blastp',
    'tblastn',
    'tblastp',
]


class QBlastInfoParser(HTMLParser):

    _pattern = r'.*QBlastInfoBegin(.*)QBlastInfoEnd'

    def __init__(self):
        super().__init__()
        self._info = {}
   
    def handle_comment(self, comment):
        match = re.search(self._pattern, comment, re.DOTALL)
        if match is not None:
            info = {}
            response = match.group(1).strip().split('\n')
            for kv in response:
                k, v = [s.strip() for s in kv.split('=')]
                info[k] = v
            self._info = info

    def blast_info(self):
        return self._info

_FORMAT = '%(asctime)-15s [%(levelname)s] %(message)s'
logging.basicConfig(format=_FORMAT, level=logging.INFO)
_LOGGER = logging.getLogger(name='Blast')


class Backend:

#    _USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.96 Safari/537.36'
    _USER_AGENT = 'ezblast'
    _tsleep = 60

    _OUTPUT_MAP = {
        'json': 'JSON2',
        'text': 'Text',
        'xml': 'XML',
        'xml2': 'XML2',
        'html': 'HTML',
        'tab': 'Tabular'
    }

    def __init__(self, api_key=None):
        self._api_key = api_key

    @staticmethod
    def _request(url):
        from urllib import request
        req = request.Request(url, headers={
            'User-Agent': Backend._USER_AGENT
        })
        return request.urlopen(req)

    @staticmethod
    def _get_blast_info(response):
        parser = QBlastInfoParser()
        parser.feed(response.read().decode('utf-8'))
        return parser.blast_info()

    def _build_url(self, params):
        from urllib import parse
        if self._api_key is not None:
            params = {'api_key': self._api_key, **params}

        root_url = 'https://blast.ncbi.nlm.nih.gov/Blast.cgi'
        data = parse.urlencode(query=params)
        #data = '&'.join(['{}={}'.format(k, v) for k, v in params.items()])
        return '{}?{}'.format(root_url, data)

    def submit_search(self, params):
        with self._request(self._build_url(params)) as response:
            blast_info = self._get_blast_info(response)
            return blast_info['RID'], blast_info['RTOE']

    def poll(self, params):
        poll_url = self._build_url(params)
        _LOGGER.info('Monitor job status here: {}'.format(poll_url))
        while True:
            with self._request(poll_url) as response:
                blast_info = self._get_blast_info(response)
                if blast_info.get('Status') is not None:
                    if blast_info['Status'] == 'WAITING':
                        _LOGGER.info('Nothing yet, waiting for {} sec...'.format(
                            self._tsleep))
                        time.sleep(self._tsleep)
                    elif blast_info['Status'] == 'UNKNOWN':
                        raise ValueError('Unknown status received')
                if blast_info.get('ThereAreHits') is not None:
                    break

    def download(self, params, path):
        with self._request(self._build_url(params)) as response:
            f = io.BytesIO(response.read())
            zf = zipfile.ZipFile(f, "r")
            zf.extractall(path)


def blast(input_path, output_path, database='nt', program='blastn',
          output_format='json', megablast=False, api_key=None, **kw):
    if output_format not in output_formats:
        raise ValueError('Unknown output format: {}'.format(output_format))
    
    if database not in databases:
        raise ValueError('Unknown database: {}'.format(database))

    if program not in programs:
        raise valueError('Unknown program: {}'.format(program))

    with open(input_path, 'r') as fasta:
        query = fasta.read()

    backend = Backend(api_key)     
    output_format = backend._OUTPUT_MAP[output_format]
    search_params = {
        'DATABASE': database,
        'CMD': 'Put',
        'PROGRAM': program,
        'QUERY': query
    }

    if megablast:
        search_params['MEGABLAST'] = 'on'

    rid, rtoe = backend.submit_search(search_params)
    _LOGGER.info('Estimated wait time for job {}: {} sec'.format(rid, rtoe))

    poll_params = {
        'RID': rid,
        'FORMAT_OBJECT': 'SearchInfo',
        'CMD': 'Get'
    }

    time.sleep(10)
    hits = backend.poll(poll_params)
    _LOGGER.info('Result ready, downloading...')

    download_params = {
        'RID': rid,
        'CMD': 'Get',
        'FORMAT_TYPE': output_format
    }

    backend.download(download_params, output_path)
    _LOGGER.info('Done')
    return 0
                    
