#!/usr/bin/env python3

import json
import html.entities

# These are undefined. We still populate the dec, oct, hex, and bin though.
unused = (129, 141, 143, 144, 157)
# These are whitespace and delete (control characters unnecessary to put here).
noprint = (32, 127, 160, 173)

tpl = '| {d}\n| {o}\n| {h}\n| {b}\n| {ht}\n| {e}\n| {l}\n| {desc}\n'

charsets = {'ctrl': (0, 31),
            'print': (32, 127),
            'extend': (128, 255)}

with open('_meta.json', 'r') as fh:
    meta = json.loads(fh.read())

for f, r in charsets.items():
    fname = '{0}.adoc'.format(f)
    lines = []
    # range()'s second param is the *stop* value, so we kick it up by one to get the last.
    for n in range(r[0], (r[1] + 1)):
        charmeta = meta.get(str(n), {})
        vals = {'d': n,
                'o': '{0:0>3}'.format(oct(n).lstrip('0o')),
                'h': '{0:0>2}'.format(hex(n).lstrip('0x')),
                'b': '{0:0>8}'.format(bin(n).lstrip('0b')),
                'ht': '&amp;#{0:0>3};'.format(n),
                'e': html.entities.codepoint2name.get(n),
                'l': None,  # We define this below.
                'desc': charmeta.get('desc')}

        # Clean up the html escape
        if not vals['e']:
            vals['e'] = 'N/A'
        else:
            vals['e'] = '&amp;{0};'.format(vals['e'])

        # Try to get a printable character; if not, use the HTML number.
        if f == 'ctrl':
            vals['l'] = '_{0}_'.format(charmeta.get('sym', 'N/A'))
        elif n in noprint:
            vals['l'] = 'N/A'
        else:
            if n in unused:
                vals['l'] = 'N/A'
            else:
                c = chr(n)
                try:
                    c.encode('ascii')
                except UnicodeEncodeError as e:
                    c = '&#{0:0>3};'.format(n)
                if c in ('|', '\\'):
                    c = '\\{0}'.format(c)
                vals['l'] = c
    
        lines.append(tpl.format(**vals))

        with open(fname, 'w') as fh:
            fh.write('\n'.join(lines))
