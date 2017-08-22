import luigi
import json
import glob
from parse_page import ParsePage

TVTROPES_BASE = "tvtropes.org"
TVTROPES_MAIN = "http://tvtropes.org"
TVTROPES_PAGE = "%s/pmwiki/pmwiki.php" % TVTROPES_MAIN
TVTROPES_TROPE = "%s/Main" % TVTROPES_PAGE
TVTROPES_TROPEINDEX = "%s/Tropes" % TVTROPES_TROPE

ALL_MEDIA = ['Manga']

class PageComparison(luigi.Task):
    chal_page = luigi.Parameter()
    ref_page = luigi.Parameter()

    def requires(self):
        return {
            'chal': ParsePage(
                page_url=TVTROPES_PAGE + '/' + self.chal_page,
            ),
            'ref': ParsePage(
                page_url=TVTROPES_PAGE + '/' + self.ref_page,
            ),
        }

    def output(self):
        return luigi.LocalTarget(
            'page_pairs/{0}_{1}_comparison.json'.format(
                self.chal_page.replace('/', '-'), self.ref_page.replace('/', '-')
            )
        )

    def run(self):
        print self.input()['chal'].path
        chal_data = json.load(self.input()['chal'].open('r'))
        chal_links = sorted([t[1] for t in chal_data['page_links'] + chal_data['sub_page_links']])
        ref_data = json.load(self.input()['ref'].open('r'))
        ref_links = sorted([t[1] for t in ref_data['page_links'] + ref_data['sub_page_links']])
        overlap = set(chal_links) & set(ref_links)
        union = set(chal_links) | set(ref_links)

        result = {
            'overlap': list(overlap),
            'overlap_size': len(overlap),
            'union': list(union),
            'union_size': len(union),
            'normalised_overlap': len(overlap) / float(len(union)),
        }

        with self.output().open('w') as f:
            json.dump(result, f)


    class PageDistances(luigi.Task):
        chal_page = luigi.Parameter()

        def get_refs(self):
            return [
                ref[11:-5]
                for media in ALL_MEDIA
                for ref in glob.glob("luigi_data/{0}/*.json".format(media))
                if ref[11:-5] != self.chal_page
            ]

        def output(self):
            return luigi.LocalTarget(
                "adjacency_matrix/{0}_distances.json".format(self.chal_page)
            )

        def requires(self):
            return [
                PageComparison(
                    chal_page=self.chal_page,
                    ref_page=ref_page
                )
                for ref_page in self.get_refs()
            ]

        def run(self):
            all_distances = []
            for ref, in_comp in zip(self.get_refs(), self.input()):
                in_data = json.load(in_comp.open('r'))
                all_distances.append((ref, in_data['overlap_size'], in_data['union_size'], in_data['normalised_overlap']))
            with self.output().open('w') as outfile:
                json.dump(all_distances, outfile)
