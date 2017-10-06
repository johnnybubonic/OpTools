import json
import re
from flask import render_template, make_response, request
from app import app

@app.route('/', methods = ['GET'])  #@app.route('/')
def index():
    # First we define interactive browsers
    _intbrowsers = ('camino', 'chrome', 'firefox', 'galeon', 'kmeleon', 'konqueror',
                    'links', 'lynx')
    # And then we set some parameter options for less typing later on.
    _yes = ('y', 'yes', 'true', '1')
    _no = ('y', 'no', 'false', '0')
    visitor = {'client': {'str': request.user_agent.string,
                          'browser': request.user_agent.browser,
                          'os': request.user_agent.platform,
                          'language': request.user_agent.language,
                          'to_header': request.user_agent.to_header(),
                          'version': request.user_agent.version},
               'ip': request.remote_addr,
               'headers': dict(request.headers)}
    # We have to convert these to strings so we can do tuple comparisons on lower()s.
    _json = str(request.args.get('json')).lower()
    _html = str(request.args.get('html')).lower()
    # Handle possibly conflicting options.
    # This forces JSON if html=0, and forces HTML if json=0. json= is processed first.
    if _json in _no:
        _html = '1'
    elif _html in _no:
        _json = '1'
    # Set the tabs for JSON
    try:
        _tabs = int(request.args.get('tabs'))
    except (ValueError, TypeError):
        _tabs = None
    if (visitor['client']['browser'] in _intbrowsers and _json not in _yes) or (_html in _yes):
        return(render_template('index.html', visitor = visitor))
    else:
        j = json.dumps(visitor, indent = _tabs)
        return(j)
