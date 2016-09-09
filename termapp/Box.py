from collections import namedtuple


Box = namedtuple('Box', ['TL', 'T', 'TR', 'R', 'BR', 'B', 'BL', 'L'])

BoxStyle = {
    'double': Box(TL=u'\N{BOX DRAWINGS DOUBLE DOWN AND RIGHT}',
                   T=u'\N{BOX DRAWINGS DOUBLE HORIZONTAL}',
                   TR=u'\N{BOX DRAWINGS DOUBLE DOWN AND LEFT}',
                   R=u'\N{BOX DRAWINGS DOUBLE VERTICAL}',
                   BR=u'\N{BOX DRAWINGS DOUBLE UP AND LEFT}',
                   B=u'\N{BOX DRAWINGS DOUBLE HORIZONTAL}',
                   BL=u'\N{BOX DRAWINGS DOUBLE UP AND RIGHT}',
                   L=u'\N{BOX DRAWINGS DOUBLE VERTICAL}')
}