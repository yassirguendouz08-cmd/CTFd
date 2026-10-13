# Search indexing

The public homepage has a descriptive title, description, canonical URL, social metadata and WebSite structured data. `/sitemap.xml` lists only the public homepage; `/robots.txt` retains configured crawl restrictions and advertises that sitemap. Account, admin and API routes have a noindex response header.

To request indexing:

1. Open https://search.google.com/search-console and add the URL-prefix property `https://ctf.cyberdune.online/`.
2. Choose HTML tag verification and add the supplied tag through CTFd Admin → Config → Themes → Theme Header, or provide it to the maintainer for installation. Return to Search Console and click Verify.
3. Submit `sitemap.xml` under Sitemaps.
4. Inspect `https://ctf.cyberdune.online/` and choose Request indexing.

Search Console ownership and indexing submission require the owner's Google account. Sitemap delivery and valid metadata do not guarantee indexing or rankings. No Google verification token is installed yet.
