# Sanity Check

A visible 50-point welcome challenge. Its flag is stored in an HTML comment in
the existing `/rules` page, discoverable with View Page Source. The installer
preserves the rules text and saves its original content beside the private answer.
It also posts one public CTFd announcement in English and Darija directing players
to the Rules source and the Sanity Check submission form.

Keep a private JSON file with `challenge` set to `sanity-check:rules-source-v1`
and `flag` containing the chosen `CYBERDUNE{...}` answer. Do not commit it.
Run inside the CTFd container:

```sh
python scripts/import-sanity-check.py /private/sanity-check/answer.json
```

Repeated runs do not duplicate challenges, source comments or announcements.
The importer refuses to overwrite an edited challenge, flag or announcement.
After replacing Rules through Admin or `install-rules.py --replace`, rerun this
importer with the same answer file to restore the comment if necessary.

Verify as a regular player that Sanity Check appears, `/rules` includes the flag
inside a comment (not visible page text), and `/notifications` shows the notice.
Do not submit the production flag solely to test scoring on a live account.
