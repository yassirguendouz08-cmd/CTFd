"""Crawlers discover the homepage without indexing account routes."""
import unittest
from flask import Flask
from CTFd.plugins.cyberdune_seo import load


class Checks(unittest.TestCase):
    def setUp(self):
        self.app=Flask(__name__)
        self.rules='User-agent: *\nDisallow: /admin\nDisallow: /private\n'
        self.app.add_url_rule('/robots.txt','views.robots',lambda:self.rules)
        for path in ['/','/login','/team','/admin/config','/api/v1/users']:
            self.app.add_url_rule(path,path,lambda:'ok')
        load(self.app)
        self.client=self.app.test_client()
    def test_sitemap_public_home_only(self):
        import xml.etree.ElementTree as ET
        r=self.client.get('/sitemap.xml');self.assertEqual(r.status_code,200)
        self.assertEqual([e.text for e in ET.fromstring(r.data).iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')],['https://ctf.cyberdune.online/'])
    def test_existing_robot_rules_preserved(self):
        r=self.client.get('/robots.txt').get_data(as_text=True)
        self.assertTrue(r.startswith(self.rules));self.assertEqual(r.count('Sitemap:'),1)
        self.rules=r
        self.assertEqual(self.client.get('/robots.txt').get_data(as_text=True),r)
    def test_home_indexable_account_routes_noindex(self):
        self.assertNotIn('X-Robots-Tag',self.client.get('/').headers)
        for path in ['/login','/team','/admin/config','/api/v1/users']:
            self.assertEqual(self.client.get(path).headers['X-Robots-Tag'],'noindex, nofollow')
