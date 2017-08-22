'''
    luigi --local-scheduler RerunAnalysisTask --module rerun_trope_scrape
'''

import luigi
import json

from launch_analysis import FindAllTropes
from parse_page import ParsePage

TVTROPES_MAIN = "http://tvtropes.org"

## Because Tropers think they're funny
bad_pages = [
    'http://tvtropes.org/pmwiki/pmwiki.php/Main/CircularRedirect',
    'http://tvtropes.org/pmwiki/pmwiki.php/Main/Recursion',
    'http://tvtropes.org/pmwiki/pmwiki.php/Main/ThisPageRedirectsToItself',
]

class RerunAnalysisTask(luigi.Task):
    def output(self):
        return luigi.LocalTarget(
            './luigi_data/rerun_page_list.json'
        )

    def requires(self):
        return FindAllTropes()

    def run(self):
        with self.input().open('r') as all_pages:
            downloaded_pages = yield [
                ParsePage(
                    page_url=trope
                ) for trope in json.load(all_pages)
                if trope.startswith(TVTROPES_MAIN)
                and trope not in bad_pages
            ]

        with self.output().open('w') as output_file:
            all_pages = []
            for page in downloaded_pages:
                with page.open('r') as page_file:
                    json_text = json.loads(page_file.read())
                    all_pages += [
                        link[1] for link in json_text['page_links']
                    ]
                    all_pages += [
                        link[1] for link in json_text['sub_pages']
                    ]
            all_pages = list(set(all_pages))
            json.dump(all_pages, output_file)
