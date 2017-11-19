import json
import re
from flask import render_template, make_response, request
from app import app

@app.route('/', methods = ['GET'])  #@app.route('/')
def index():
    hostkeys = None  # TODO: hostkeys go here. dict?
    # First we define interactive browsers
    _intbrowsers = ['camino', 'chrome', 'firefox', 'galeon',
                    'kmeleon', 'konqueror', 'links', 'lynx']
    # Then we set some parameter options for less typing later on.
    _yes = ('y', 'yes', 'true', '1', True)
    _no = ('y', 'no', 'false', '0', False, 'none')
    # http://werkzeug.pocoo.org/docs/0.12/utils/#module-werkzeug.useragents
    # We have to convert these to strings so we can do tuple comparisons on lower()s.
    params = {'json': str(request.args.get('json')).lower(),
              'html': str(request.args.get('html')).lower(),
              'raw': str(request.args.get('raw')).lower()}
    if request.user_agent.browser in _intbrowsers:
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
        if request.user_agent.browser in _intbrowsers or params['html']:
            params['tabs'] = 4
        else:
            params['tabs'] = None
    j = json.dumps(hostkeys, indent = params['tabs'])
    if (request.user_agent.browser in _intbrowsers and params['html'] and not params['raw']) or \
        (request.user_agent.browser not in _intbrowsers and params['html']):
        return(render_template('index.html', hostkeys = hostkeys))
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
