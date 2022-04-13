# encoding: utf-8
import sys
import re
from workflow import Workflow3, ICON_ERROR
from urllib.request import Request
from urllib import request
from json.decoder import JSONDecoder

log = None


def get_token(wf):
    token = wf.stored_data('token')
    if token is None:
        wf.add_item(
            'You must provide a token before using this workflow',
            icon=ICON_ERROR,
            valid=False
        )
        wf.send_feedback()
        sys.exit(1)
    return token.decode('utf-8')


def repos_request(token, url='https://api.github.com/user/repos'):
    request_with_header = Request(url, headers={'Authorization': 'token %s' % token})
    f = request.urlopen(request_with_header)

    return f

def decoded_repos_request(token, url='https://api.github.com/user/repos'):
    request_with_header = Request(url, headers={'Authorization': 'token %s' % token})
    f = request.urlopen(request_with_header)

    return f.read().decode('utf-8')

def get_last(r):
    link = r.headers.get('link')
    if not link:
        return None
    last_search = re.search('page=(\d+)>;\s*rel="last"', link)
    if not last_search:
        return None
    return int(last_search.group(1))


def get_all_urls(r):
    last = get_last(r)
    if not last:
        return []
    inclusive_last = last + 1
    return ['https://api.github.com/user/repos?page=%d' % page for page in range(2, inclusive_last)]


def get_all(token):
    from concurrent.futures import ThreadPoolExecutor, as_completed
    r = repos_request(token)
    repos = JSONDecoder().decode(r.read().decode('utf-8'))
    urls = get_all_urls(r)
    pool = ThreadPoolExecutor(20)
    futures = [pool.submit(decoded_repos_request,token,url) for url in urls]
    results = [r.result() for r in as_completed(futures)]
    for result in results:
        repos += JSONDecoder().decode(result)
    return repos


def get_cached_repos(wf):
    repos = wf.stored_data('repos')
    return repos


def load_repos(wf, token):
    repos = get_all(token)
    wf.store_data('repos', repos)
    return repos


def get_repos(wf, token):
    repos = get_cached_repos(wf)
    if repos:
        return repos
    return load_repos(wf, token)


def main(wf):
    args = wf.args
    if args and args[0] == '--auth':
        # TODO provide helper to take them to documentation to get api token
        # configured correctly
        token = args[1]
        wf.store_data('token', token.encode())
        load_repos(wf, token)
        return

    token = get_token(wf)

    if args and args[0] == '--refresh':
        load_repos(wf, token)
        return

    repos = get_repos(wf, token)
    if args:
        repos = wf.filter(args[0], repos, lambda repo: repo.get('full_name'))

    if not repos:
        wf.warn_empty('No repos found. Refresh repos or try a different query.')
        wf.send_feedback()
        return

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
