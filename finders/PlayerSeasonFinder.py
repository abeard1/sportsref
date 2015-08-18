from bs4 import BeautifulSoup
from copy import deepcopy
import json
import os
from pprint import pprint
import requests
import time

PLAYER_SEASON_URL = ('http://www.pro-football-reference.com/'
                     'play-index/psl_finder.cgi')

CONSTANTS_FN = 'PSFConstants.json'

def PlayerSeasonFinder(**kwargs):
    """Description
    
    @param param:  Description
    @type  param:  Type
    
    @return:  Description
    @rtype :  Type
    
    @raise e:  Description
    """

    opts = kwArgsToOpts(**kwargs)
    querystring = '&'.join(['{}={}'.format(k, v) for k, v in opts.iteritems()])
    url = ('http://www.pro-football-reference.com/' +
           'play-index/psl_finder.cgi?' +
           querystring)
    print url
    html = requests.get(url).text
    soup = BeautifulSoup(html, 'lxml')
    for row in soup.select('table#stats tbody tr[class=""]'):
        print row.select_one('a').get('href')
        # I'm here

def kwArgsToOpts(**kwargs):

    constants = getConstants()

    # if positions addressed in one kwarg, give it priority over pos_is_X
    # entries by overwriting each of those it addresses
    ext = {}
    for k, v in kwargs.iteritems():
        if k.lower() in ('pos', 'position', 'positions'):
            v = [v] if not isinstance(v, list) else v
            for pos in constants['POSITIONS']:
                if pos in v:
                    ext['pos_is_' + pos] = 'Y'
    kwargs.update(ext)

    # same as above for draft position
    ext = {}
    for k, v in kwargs.iteritems():
        if k.lower() in ('draft_pos', 'draft_position', 'draft_positions'):
            v = [v] if not isinstance(v, list) else v
            for pos in constants['POSITIONS']:
                if pos in v:
                    ext['draft_pos_is_' + pos] = 'Y'
                else:
                    ext['draft_pos_is_' + pos] = 'N'
    kwargs.update(ext)

    # start with defaults
    opts = deepcopy(constants['INPUTS_DEFAULTS'])
    # update based on kwargs
    for k, v in kwargs.iteritems():
        # small changes to keys/values for convenience
        k = 'team_id' if k in ('tm', 'team') else k
        v = 'Y' if v == True else v
        v = 'N' if v == False else v
        # if overwriting a default
        if k in opts:
            opts[k] = v

    # if no positions were selected, then select all positions
    noPos = True
    for k in kwargs:
        if k.startswith('pos_is_') and kwargs[k] in ('Y', True, 'y'):
            noPos = False
            break
    if noPos:
        for pos in constants['POSITIONS']:
            opts['pos_is_' + pos] = 'Y'

    # same as above for draft positions
    noPos = True
    for k in kwargs:
        if k.startswith('draft_pos_is_') and kwargs[k] in ('Y', True, 'y'):
            noPos = False
            break
    if noPos:
        for pos in constants['POSITIONS']:
            opts['draft_pos_is_' + pos] = 'Y'

    # turning on draft flag if necessary
    draft = False
    for k in opts:
        if k in constants['DRAFT_INPUTS']:
            draft = True
    if draft:
        opts['draft'] = '1'

    return opts

def getPositions(soup):
    striplen = len('pos_is_')
    return [
        posBox['name'][striplen:] for posBox in
        soup.select('form#psl_finder input[name^="pos_is"]')
    ]

def getCompStats(soup):
    return [
        option['value'] for option in 
        soup.select('form#psl_finder select#c1stat option') if option.get('value')
    ]

def getSortStats(soup):
    return [
        option['value'] for option in 
        soup.select('form#psl_finder select[name="order_by"] option') if option.get('value')
    ]

def getTeams(soup):
    teams = []
    for option in soup.select('form#psl_finder select#team_id option'):
        if 'disabled' in option.attrs and 'Defunct' in option.text:
            break
        if option.get('value'):
            teams.append(option['value'])
    return teams

def getInputsAndDefaults(soup):
    # start with input elements
    def_dict = {}
    for inp in soup.select('form#psl_finder input[name]'):
        if inp['type'] in ('checkbox', 'radio'):
            if 'checked' in inp.attrs:
                def_dict[inp['name']] = inp['value']
            else:
                def_dict[inp['name']] = def_dict.get(inp['name'], '')
        else:
            def_dict[inp['name']] = inp.get('value', '')

    # for dropdowns (select elements)
    for sel in soup.select('form#psl_finder select[name]'):
        defaultOpt = sel.select_one('option[selected]')
        if defaultOpt:
            def_dict[sel['name']] = defaultOpt.get('value', '')
        else:
            def_dict[sel['name']] = sel.select_one('option').get('value', '')

    for k in def_dict:
        if 'pos_is_' in k:
            def_dict[k] = 'N'
    
    return def_dict

def getDraftInputs(soup):
    draftInputs = []
    add = False
    for opt in soup.select('form#psl_finder [name]'):
        if opt['name'] == 'draft':
            add = True
        if add:
            draftInputs.append(opt['name'])
    return draftInputs

def getConstants():
    
    # switch to finders directory
    orig_cwd = os.getcwd()
    os.chdir(os.path.dirname(os.path.realpath(__file__)))

    # set time variables
    if os.path.isfile(CONSTANTS_FN):
        modtime = os.path.getmtime(CONSTANTS_FN)
        curtime = time.time()
    # if file not found or it's been >= a day, generate new constants
    if (not os.path.isfile(CONSTANTS_FN) or
            not int(curtime) - int(modtime) >= 24*60*60):
        
        # must generate the file
        
        html = requests.get(PLAYER_SEASON_URL).text
        soup = BeautifulSoup(html, 'lxml')

        constants = {
            'POSITIONS': getPositions(soup),
            'COMP_STATS': getCompStats(soup),
            'SORT_STATS': getSortStats(soup),
            'TEAMS': getTeams(soup),
            'INPUTS_DEFAULTS': getInputsAndDefaults(soup),
            'DRAFT_INPUTS': getDraftInputs(soup),
        }

        with open(CONSTANTS_FN, 'w+') as f:
            json.dump(constants, f)

    else:
        with open(CONSTANTS_FN, 'r') as const_f:
            constants = json.load(const_f)
    
    # change back to original directory and return
    os.chdir(orig_cwd)
    return constants
    
if __name__ == "__main__":
    psf = PlayerSeasonFinder(**{
        'year_min': 2000, 'year_max': 2014, 'pos': 'rb', 'order_by': 'rush_yds_per_g'
    })
