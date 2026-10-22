"""All five operations through real persistent Chromium with synthetic Reddit HTML."""
import base64
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from reddita import SourceRequest, SourceBudgets, acquire_reddit
from reddita.browser_guard import BrowserGuard

class CommandBrowserTests(unittest.TestCase):
    def test_all_five_operations_keep_original_browser_path(self):
        listing='''<div class="thing" data-fullname="t3_abc123" data-subreddit="python"><a class="title">Example</a><a class="comments" href="/r/python/comments/abc123/post/">1 comment</a></div>'''
        thread='''<div class="thing link" data-fullname="t3_abc123" data-subreddit="python"><a class="title">Example</a></div>'''
        about='''<shreddit-subreddit-header prefixed-name="r/python" description="Example"></shreddit-subreddit-header>'''
        cases=[('search','python tools',{},listing),('subreddit','python',{},listing),
               ('subreddit-search','python',{'query':'tools'},listing),
               ('thread','abc123',{},thread),('about','python',{},about)]
        import json
        for op,locator,params,html in cases:
            with self.subTest(op=op), tempfile.TemporaryDirectory() as tmp:
                def fixture(session,event):
                    session.send('Fetch.fulfillRequest',{'requestId':event['requestId'],
                        'responseCode':200,'responseHeaders':[{'name':'Content-Type','value':'text/html'}],
                        'body':base64.b64encode(html.encode()).decode()})
                def factory(*args,**kwargs):
                    return BrowserGuard(*args,**kwargs,resolver=lambda h:True,fixture=fixture)
                req=SourceRequest(source='reddit',operation=op,locator=locator,
                                  parameters_json=json.dumps(params),max_pages=1)
                with patch('reddita.browser_guard.BrowserGuard',side_effect=factory):
                    capture=acquire_reddit(req,budgets=SourceBudgets(timeout_seconds=10),
                        settings_digest='0'*64,profile_root=Path(tmp),native_transport=True,allow_stealth=True)
                self.assertEqual(len(capture.result.records),1)
                self.assertTrue(capture.result.envelope.complete)
