from __future__ import print_function
import io
from collections import defaultdict

import saleae
import tempfile

import sys


def start_triggered_capture():
    _s.capture_start_and_wait_until_finished()


def merge_analyzers(inputs, add_header=False):
    result = []
    columns = ['ts']
    for i, export in enumerate(inputs):
        value_key = 'v{}'.format(i)
        columns.append(value_key)
        for row in export[1:]:
            if ',' in row:
                ts, value = row.split(',')[0:2:]
                # noinspection PyArgumentList
                result.append(
                    defaultdict(lambda: '',
                                {
                                    'ts': 1000.0 * float(ts),
                                    value_key: value
                                })
                )

    result = sorted(result, key=lambda mergerow: mergerow['ts'])
    mergeformat = ','.join(['{{merged[{}]}}'.format(c) for c in columns])
    csv = [mergeformat.format(merged=m) for m in result]
    if add_header:
        csv.insert(0, ','.join(columns))
    return csv

# Take a reference to the Socket API bridge
_s = saleae.Saleae()

if __name__ == '__main__':
    import tempfile

    # print('Logging raw data to temp file: {}'.format(outwrapper.name), file=sys.stderr)

    print('Analysers:')
    exported = []
    for a in _s.get_analyzers():
        aname, aindex = a
        afile = tempfile.NamedTemporaryFile(
            prefix='{name}_{idx}'.format(name=aname, idx=aindex),
            suffix='.csv',
            delete=False
        )
        afile.close()
        print(' {}: {}'.format(aindex, aname))

        # _s.export_analyzer(aindex, afile.name)
        print(' exporting to {}'.format(afile.name))

        # _s._build('EXPORT_ANALYZER')
        # _s._build(str(aindex))
        # _s._build(afile.name)
        # _s._build('extra')
        # resp = _s._finish()
        resp = _s.export_analyzer(aindex, afile.name, data_response=True)

        exported.append(resp.split('\n'))

    # Merge them
    merged = merge_analyzers(exported, add_header=True)

    mergefile = tempfile.NamedTemporaryFile(prefix='Merged', suffix='.csv', delete=False)
    # outfile = io.open(outwrapper.name, mode='w+b' )
    print('\n'.join(merged), file=mergefile)
    mergefile.close()
    print('Merged to {}'.format(mergefile.name))
