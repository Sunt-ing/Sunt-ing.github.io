"""Shared primary navigation for the homepage, writing index and articles."""
def navigation(lang='en', current='home'):
    entries = [('home', '/', 'Home'), ('writing', f'/{lang}/blog/', 'TingLog')]
    links = []
    for key, url, label in entries:
        active = ' aria-current="page"' if key == current else ''
        links.append(f'<a href="{url}" data-nav="{key}"{active}>{label}</a>')
    return '<nav class="main-nav" aria-label="Main navigation">' + ''.join(links) + '</nav>'
