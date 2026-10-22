import base64
import unittest
from reddita.browser_guard import BrowserGuard, approved_resource_url

URL = 'https://old.reddit.com/search?q=test'

class PolicyTests(unittest.TestCase):
    def test_allowed_reddit_resources_and_denied_destinations(self):
        for url in ['https://old.reddit.com/search?q=test','https://www.reddit.com/r/Python/',
                    'https://www.redditstatic.com/a.js','https://preview.redd.it/a.png',
                    'https://styles.redditmedia.com/a.css']:
            self.assertTrue(approved_resource_url(url), url)
        for url in ['http://old.reddit.com/', 'https://127.0.0.1/',
                    'https://example.com/', 'https://redditstatic.com.evil.test/a.js',
                    'https://user:pass@old.reddit.com/', 'https://old.reddit.com:8443/',
                    'file:///etc/passwd']:
            self.assertFalse(approved_resource_url(url),url)

    def test_methods_navigation_budget_and_dns(self):
        guard = BrowserGuard('search','test',URL,resolver=lambda h:True,max_requests=4)
        self.assertTrue(guard.permits('GET',URL,document=True))
        self.assertFalse(guard.permits('POST',URL))
        self.assertFalse(guard.permits('GET','https://old.reddit.com/login',document=True))
        self.assertTrue(guard.permits('GET','https://www.redditstatic.com/a.js'))
        self.assertFalse(guard.permits('GET',URL))
        guard = BrowserGuard('search','test',URL,resolver=lambda h:False)
        self.assertFalse(guard.permits('GET',URL))

class ChromiumIntegrationTests(unittest.TestCase):
    def run_fixture(self, html, redirects=False):
        from patchright.sync_api import sync_playwright
        seen=[]
        def fixture(session,event):
            url=event['request']['url'];seen.append(url)
            if redirects:
                session.send('Fetch.fulfillRequest',{'requestId':event['requestId'],
                    'responseCode':302,'responseHeaders':[{'name':'Location','value':'https://example.com/stolen'}],
                    'body':''})
            else:
                session.send('Fetch.fulfillRequest',{'requestId':event['requestId'],
                    'responseCode':200,'responseHeaders':[{'name':'Content-Type','value':'text/html'}],
                    'body':base64.b64encode(html.encode()).decode()})
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True)
            context=browser.new_context(service_workers='block',accept_downloads=False)
            page=context.new_page()
            guard=BrowserGuard('search','test',URL,resolver=lambda h:True,fixture=fixture)
            guard.attach(context,page)
            try:
                page.goto(URL,timeout=15000)
            except Exception:
                if not redirects: raise
            if not redirects:
                page.wait_for_function('document.documentElement.dataset.finished === \"yes\"',timeout=10000)
                self.assertEqual(page.locator('html').get_attribute('data-script-worked'),'yes')
            blocked=list(guard.blocked)
            denied=guard.navigation_denied
            browser.close()
        return seen,blocked,denied

    def test_real_chromium_keeps_javascript_and_blocks_external_local_post(self):
        html='''<script>document.documentElement.dataset.scriptWorked='yes';
        Promise.allSettled([
          fetch('https://example.com/steal'),
          fetch('https://127.0.0.1/private'),
          fetch('/search?q=test',{method:'POST',body:'x'})
        ]).then(()=>document.documentElement.dataset.finished='yes');</script>'''
        seen,blocked,_=self.run_fixture(html)
        self.assertEqual(seen,[URL])
        self.assertIn(('GET','https://example.com/steal'),blocked)
        self.assertIn(('GET','https://127.0.0.1/private'),blocked)
        self.assertIn(('POST',URL),blocked)

    def test_real_chromium_redirect_blocked_at_request_stage(self):
        seen,blocked,denied=self.run_fixture('',redirects=True)
        self.assertEqual(seen,[URL])
        self.assertIn(('GET','https://example.com/stolen'),blocked)
        self.assertTrue(denied)
