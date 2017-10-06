import json
import re
from flask import render_template, make_response, request
from app import app

@app.route('/', methods = ['GET'])  #@app.route('/')
def index():
    # First we define interactive browsers
    _intbrowsers = {'camino': ['http://caminobrowser.org/', 'Camino'],
                    'chrome': ['https://www.google.com/chrome/', 'Google Chrome'],
                    'firefox': ['https://www.mozilla.org/firefox/', 'Mozilla Firefox'],
                    'galeon': ['http://galeon.sourceforge.net/', 'Galeon'],
                    'kmeleon': ['http://kmeleonbrowser.org/', 'K-Meleon'],
                    'konqueror': ['https://konqueror.org/', 'Konqueror'],
                    'links': ['http://links.twibright.com/', 'Links'],
                    'lynx': ['http://lynx.browser.org/', 'Lynx']}
    _os = {'aix': ['https://www.ibm.com/power/operating-systems/aix', 'AIX'],
           'amiga': ['http://www.amiga.org/', 'Amiga'],
           'android': ['https://www.android.com/', 'Android'],
           'bsd': ['http://www.bsd.org/', 'BSD'],
           'chromec': ['https://www.chromium.org/chromium-os', 'ChromeOS'],
           'hpux': ['https://www.hpe.com/us/en/servers/hp-ux.html', 'HP-UX'],
           'iphone': ['https://www.apple.com/iphone/', 'iPhone'],
           'ipad': ['https://www.apple.com/ipad/', 'iPad'],
           'irix': ['https://www.sgi.com/', 'IRIX'],
           'linux': ['https://www.kernel.org/', 'GNU/Linux'],
           'macos': ['https://www.apple.com/macos/', 'macOS'],
           'sco': ['http://www.sco.com/products/unix/', 'SCO'],
           'solaris': ['https://www.oracle.com/solaris/', 'Solaris'],
           'wii': ['http://wii.com/', 'Wii'],
           'windows': ['https://www.microsoft.com/windows/', 'Windows']}
    _alts = {'amiga': ' (have you tried <a href="http://aros.sourceforge.net/">AROS</a> yet?)',
             'macos': ' (have you tried <a href="https://elementary.io/">ElementaryOS</a> yet?)',
             'sgi': ' (have you tried <a href="http://www.maxxinteractive.com">MaXX</a> yet?)',
             'windows': ' (have you tried <a href="https://https://reactos.org/">ReactOS</a> yet?)'}
    # And then we set some parameter options for less typing later on.
    _yes = ('y', 'yes', 'true', '1', True)
    _no = ('y', 'no', 'false', '0', False, 'none')
    # http://werkzeug.pocoo.org/docs/0.12/utils/#module-werkzeug.useragents
    visitor = {'client': {'str': request.user_agent.string,
                          'browser': request.user_agent.browser,
                          'os': request.user_agent.platform,
                          'language': request.user_agent.language,
                          'to_header': request.user_agent.to_header(),
                          'version': request.user_agent.version},
               'ip': re.sub('^::ffff:', '', request.remote_addr),
               'headers': dict(request.headers)}
    # We have to convert these to strings so we can do tuple comparisons on lower()s.
    params = {'json': str(request.args.get('json')).lower(),
              'html': str(request.args.get('html')).lower(),
              'raw': str(request.args.get('raw')).lower()}
    if visitor['client']['browser'] in _intbrowsers.keys():
        if params['html'] == 'none':
            params['html'] = True
            if params['json'] == 'none':
                params['json'] = False
            elif params['json'] in _yes:
                params['json'] = True
    for k in params.keys():
        if params[k] in _no:
            params[k] = False
        else:
            params[k] = True
    # Set the tabs for JSON
    try:
        params['tabs'] = int(request.args.get('tabs'))
    except (ValueError, TypeError):
        if visitor['client']['browser'] in _intbrowsers.keys() or params['html']:
            params['tabs'] = 4
        else:
            params['tabs'] = None
    j = json.dumps(visitor, indent = params['tabs'])
    if (visitor['client']['browser'] in _intbrowsers.keys() and params['html'] and not params['raw']) or \
        (visitor['client']['browser'] not in _intbrowsers.keys() and params['html']):
        return(render_template('index.html',
                               visitor = visitor,
                               browsers = _intbrowsers,
                               os = _os,
                               alts = _alts,
                               json = j,
                               params = params))
    else:
        if visitor['client']['browser'] in _intbrowsers.keys() and not params['raw']:
            return(render_template('json.html',
                                   json = j,
                                   params = params))
        return(j)

@app.route('/about', methods = ['GET'])
def about():
    return(render_template('about.html'))

@app.route('/usage', methods = ['GET'])
def usage():
    return(render_template('usage.html'))