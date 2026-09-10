"""TEMPORARY diagnostic: what do GraphQL and the public HTML expose about star lists?"""
import json, os, re, urllib.request, urllib.error

TOKEN = os.environ["GH_TOKEN"]; USER = os.environ["STARS_USERNAME"]

def gql(query, variables):
    req = urllib.request.Request("https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(), method="POST")
    req.add_header("Authorization", f"Bearer {TOKEN}"); req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "stars-probe")
    try:
        with urllib.request.urlopen(req) as r: return r.getcode(), json.loads(r.read())
    except urllib.error.HTTPError as e: return e.code, e.read().decode("utf-8", "replace")[:800]

print("== viewer + user.lists (GITHUB_TOKEN)")
print(gql("query($l:String!){ viewer{login __typename} user(login:$l){ login lists(first:5){ totalCount nodes{ name slug isPrivate items(first:2){ totalCount nodes{ ... on Repository{ nameWithOwner } } } } } } }", {"l": USER}))
print("== schema: fields on User containing 'list'")
code, body = gql('{ __type(name:"User"){ fields{ name } } }', {})
names = [f["name"] for f in (body.get("data", {}).get("__type", {}) or {}).get("fields", [])] if isinstance(body, dict) else []
print(code, [n for n in names if "list" in n.lower()])
print("== schema: UserList type")
print(gql('{ __type(name:"UserList"){ name fields{ name } } }', {}))

def html(url):
    req = urllib.request.Request(url); req.add_header("User-Agent", "Mozilla/5.0 (stars-probe)")
    req.add_header("Accept", "text/html")
    try:
        with urllib.request.urlopen(req) as r: return r.getcode(), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e: return e.code, e.read().decode("utf-8", "replace")[:500]

print("== HTML /stars/USER/lists")
code, page = html(f"https://github.com/stars/{USER}/lists")
print(code, len(page))
hrefs = sorted(set(re.findall(rf'href="(/stars/{USER}/lists/[^"?#]+)"', page)))
print("list hrefs:", hrefs[:40])
# Show the markup around the first list link so a parser can be designed.
if hrefs:
    i = page.find(hrefs[0]); print("--- snippet around first list link ---"); print(page[max(0, i-1200): i+800])
    print("== HTML first list page")
    code2, lp = html(f"https://github.com{hrefs[0]}")
    print(code2, len(lp))
    repos = re.findall(r'href="/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)"[^>]*>', lp)
    print("candidate repo hrefs (first 30):", repos[:30])
    j = lp.find('<h3'); print("--- snippet around first <h3> ---"); print(lp[max(0, j-600): j+900])
    print("pagination markers:", re.findall(r'href="([^"]*page=\d+[^"]*)"', lp)[:10])
    m = re.search(r'(\d+)\s+repositor', lp); print("count text:", m.group(0) if m else None)
