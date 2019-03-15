# encoding: utf-8
import sys
import re
from workflow import Workflow3, ICON_WEB, web, ICON_ERROR

log = None

def get_token(wf):
    token = wf.stored_data('token')
    if token is None:
        wf.add_item(
            'You must provide a token before using this workflow',
            subtitle='Enter github-auth {TOKEN}',
            icon=ICON_ERROR,
            valid=False
        )
        wf.send_feedback()
        sys.exit(1)
    return token

def request(token, url='https://api.github.com/user/repos'):
    r = web.get(url, headers={'Authorization': 'token %s' % token})
    r.raise_for_status()
    return r

def get_next(r):
    link = r.headers.get('link')
    searched = re.search('<([^>]+)>;\s*rel="next"', link)
    if not searched:
        return None
    return searched.group(1)
        

def get_all(token):
    r = request(token)
    repos = r.json()
    next_url = get_next(r)
    while next_url:
        r = request(token, next_url)
        repos = repos + r.json()
        next_url = get_next(r)
    return repos

def get_repos(wf, token):
    repos = wf.stored_data('repos')
    if repos:
        return repos
    repos = get_all(token)
    wf.store_data('repos', repos)
    return repos
    

def main(wf):
    args = wf.args
    if args and args[0] == '--auth':
        # TODO provide helper to take them to documentation to get api token
        # configured correctly
        wf.store_data('token', args[1])
        return

    token = get_token(wf)
    
    repos = get_repos(wf, token)
    if args:
        repos = wf.filter(args[0], repos, key=lambda repo: repo['full_name'])

    for repo in repos:
        url = repo['html_url']
        wf.add_item(
            repo['full_name'],
            subtitle=url,
            arg=url,
            uid=url,
            valid=True
        )
    wf.send_feedback()
    

if __name__ == u"__main__":
    wf = Workflow3(libraries=['./lib'])
    log = wf.logger
    sys.exit(wf.run(main))