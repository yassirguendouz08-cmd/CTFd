# First CTF bootcamp

Eight French beginner exercises: two Web, two Crypto, two Linux and two OSINT.
Each teaches one concept, has a single downloadable attachment, awards a fixed
100 points and offers three free progressive hints. There is no required Docker
instance, paid account, scanner, or brute force.

| Exercise | Concept |
| --- | --- |
| Derrière la page | HTML source and comments |
| Une réponse bavarde | Reading a supplied HTTP response capture |
| Le message emballé | Base64 decoding; encoding versus encryption |
| Trois lettres plus loin | Caesar cipher with a known shift |
| Le fichier discret | `ls -a` and `cat` |
| Une ligne dans les logs | `grep` |
| La carte postale | Landmark identification and public-source corroboration |
| La photo se souvient | GPS EXIF metadata and mapping |

The Web exercises are downloadable teaching artifacts, not live target servers.
Linux requires a Linux terminal (VM, WSL, or Linux installation). OSINT allows
alternative research methods; attribution records are legitimate clues.

## Build privately

Install Pillow in your authoring environment. Place the two licensed originals in
a private `photos` directory as `photo-01.jpg` and `photo-02.jpg`. Record the expected
city answers in a private JSON file with the keys `landmark` and `gps`.

```bash
python challenges/bootcamp-first-steps/build.py --photos /private/photos --answers /private/answers.json --output /private/bootcamp-pack
```

Originals and licenses:

- [Photo 01, Milamber's portfolio](https://www.flickr.com/photos/90956808@N00/276404124), [CC BY 2.0](https://creativecommons.org/licenses/by/2.0/).
- [Photo 02, Bernard Gagnon](https://commons.wikimedia.org/wiki/File:Hassan_Tower.jpg), [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/).

The second image receives training GPS metadata based on its source coordinates;
the compressed image data remains unchanged. Its adaptation retains CC BY-SA 3.0.
Player archives include author, source, license and modification notices.

Keep the generated directory private: `manifest.json` and `ORGANIZER-GUIDE.md`
contain answers. Retain the same directory to keep flags stable. Do not commit
the directory, player artifacts, or actual flags to this public repository.

## Import and review

Run inside the production CTFd container after copying the pack into a private
mounted directory:

```bash
python scripts/import-bootcamp.py /private/bootcamp-pack
```

The importer always creates **Hidden** challenges. It never changes existing
unrelated challenges, scores, accounts or event configuration. It can be rerun
with the same unmodified pack without creating duplicates. It refuses to overwrite
an edited or published pack. A failed import rolls back its new database rows and
removes only files uploaded by that attempt.

Review them in **Admin → Challenges**. Hidden means visible to all administrators,
not regular players. To release a challenge later, change its state to Visible
in the admin editor. Keep the organizer guide outside player attachments.
