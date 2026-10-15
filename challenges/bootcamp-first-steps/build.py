"""Build private, beginner CTFd exercises. Generated flags never belong in Git."""
import argparse
import base64
import io
import json
import secrets
import struct
import tarfile
import zipfile
from pathlib import Path


def gps_jpeg(source):
    """Replace EXIF metadata, preserving every compressed image-data byte."""
    from PIL import Image
    from PIL.TiffImagePlugin import IFDRational
    exif = Image.Exif()
    exif[315] = 'Bernard Gagnon'
    exif[33432] = 'CC BY-SA 3.0; https://creativecommons.org/licenses/by-sa/3.0/'
    exif[270] = 'Bootcamp exercise: GPS metadata added; image pixels unchanged.'
    exif[34853] = {0: b'\x02\x03\x00\x00', 1: 'N',
                   2: tuple(IFDRational(v, 1) for v in (34, 1, 27)),
                   3: 'W', 4: tuple(IFDRational(v, 1) for v in (6, 49, 22))}
    segment = exif.tobytes()
    data = source.read_bytes()
    assert data[:2] == b'\xff\xd8'
    kept = bytearray(data[:2])
    pos = 2
    while pos < len(data):
        marker = data[pos:pos + 2]
        if marker == b'\xff\xda':
            kept.extend(data[pos:])
            break
        length = int.from_bytes(data[pos + 2:pos + 4], 'big')
        chunk = data[pos:pos + 2 + length]
        if not (marker == b'\xff\xe1' and chunk[4:10] == b'Exif\x00\x00'):
            kept.extend(chunk)
        pos += 2 + length
    return bytes(kept[:2]) + b'\xff\xe1' + struct.pack('>H', len(segment) + 2) + segment + bytes(kept[2:])


def build(output, photos, answers):
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / 'manifest.json'
    if manifest_path.exists():
        raise SystemExit('This output already has flags. Reuse it; choose a new directory for a new set.')
    entries = []
    guide = ['# Bootcamp — guide organisateur (privé)',
             '8 défis débutants, 100 points chacun, 3 indices gratuits par défi.',
             'État initial : Hidden. Les administrateurs peuvent les prévisualiser.',
             'Ne pas publier ce document ou manifest.json sur GitHub.\n']

    def add(slug, name, category, concept, task, hints, solution, files, flag=None):
        flag = flag or f'CYBERDUNE{{{slug.replace("-", "_")}_{secrets.token_hex(3)}}}'
        folder = output / slug
        folder.mkdir()
        paths = []
        for filename, body in files(flag).items():
            path = folder / filename
            path.write_bytes(body if isinstance(body, bytes) else body.encode('utf-8'))
            paths.append(f'{slug}/{filename}')
        description = (f'**Premier CTF · Niveau découverte · 5 à 10 minutes**\n\n'
                       f'### Le concept\n{concept}\n\n### Ta mission\n{task}\n\n'
                       '### Pour commencer\nTélécharge le fichier joint. Les trois indices sont gratuits : '
                       'ouvre-les un par un si tu bloques. Copie le flag dans le champ de réponse de ce défi.\n\n'
                       '**Format :** `CYBERDUNE{...}`. Respecte les caractères du flag. '
                       'Aucun compte externe payant, scan ou brute-force n’est nécessaire.')
        entries.append(dict(slug=slug, name=name, category=category, value=100,
                            description=description, hints=hints, flag=flag,
                            flag_data='case_insensitive' if category == 'OSINT' else '', files=paths))
        guide.extend([f'## {name} — {category}', f'Flag : `{flag}`', solution, '\n'])

    def html_file(flag):
        return {'welcome.html': f'''<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bienvenue au bootcamp</title><style>body{{font:18px/1.7 system-ui;background:#101014;color:#eee;max-width:760px;margin:10vh auto;padding:24px}}h1{{color:#f55}}code{{color:#fb8}}</style></head>
<body><h1>Bienvenue, explorateur !</h1><p>Cette page n’affiche aucun flag. Pourtant, ton navigateur a reçu tout son code HTML.</p>
<p>Un commentaire HTML est une note pour le développeur : le navigateur ne l’affiche pas dans la page.</p>
<!-- Note de développement : supprimer ce secret avant publication. Flag : {flag} -->
<p>Tu peux lire le code de ce fichier avec un éditeur de texte ou les outils de ton navigateur.</p></body></html>'''}

    add('web-source', 'Bootcamp 01 — Derrière la page', 'Web',
        'Le navigateur reçoit du HTML et le transforme en page. Les commentaires `<!-- ... -->` '
        'font partie du code reçu, même s’ils ne sont pas affichés. Un secret envoyé au navigateur peut être lu.',
        'Ouvre `welcome.html` dans ton navigateur. Retrouve le flag laissé dans le code source. '
        'Tu peux aussi ouvrir le fichier dans un éditeur de texte. Aucun serveur à lancer.',
        ['La page affichée et son code HTML ne sont pas la même chose.',
         'Sur Windows/Linux : Ctrl+U affiche souvent le source. Sinon, ouvre welcome.html avec un éditeur de texte.',
         'Cherche le commentaire qui commence par <!-- Note de développement et copie le flag complet.'],
        'Ouvrir welcome.html, afficher son source (Ctrl+U) et lire le commentaire HTML. '
        'Débrief : ne jamais envoyer un secret au navigateur en pensant le cacher avec du HTML.', html_file)

    def http_file(flag):
        body = '<!doctype html><html lang="fr"><body><h1>Tout semble normal</h1><p>Le flag n’est pas dans ce corps HTML.</p></body></html>\n'
        return {'response.http': 'HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n'
                f'Content-Length: {len(body.encode())}\r\nServer: Bootcamp-Demo\r\nX-Training-Flag: {flag}\r\n'
                'Cache-Control: no-store\r\n\r\n' + body}

    add('web-headers', 'Bootcamp 02 — Une réponse bavarde', 'Web',
        'Une réponse HTTP contient un statut, des en-têtes, une ligne vide, puis un corps. '
        'Le navigateur affiche généralement le corps, mais les en-têtes peuvent aussi révéler des informations.',
        'Le fichier `response.http` est une capture texte de réponse HTTP créée pour cet exercice. '
        'Ouvre-le avec un éditeur de texte et retrouve le flag dans les en-têtes. '
        'Tu n’as pas besoin de contacter un site ni d’installer Burp Suite.',
        ['Les en-têtes se trouvent avant la première ligne vide.',
         'Une ligne d’en-tête s’écrit Nom: valeur. Regarde les en-têtes qui commencent par X-.',
         'La valeur de X-Training-Flag est le flag. Copie seulement la valeur, sans le nom de l’en-tête.'],
        'Lire response.http et extraire X-Training-Flag. Débrief : lire une réponse complète, pas seulement son HTML.', http_file)

    add('crypto-base64', 'Bootcamp 03 — Le message emballé', 'Crypto',
        'Base64 est un encodage : il change la représentation d’un texte sans utiliser de clé secrète. '
        'Il peut être décodé directement. Ce n’est pas du chiffrement.',
        'Le texte de `message.txt` est encodé en Base64 une seule fois. Décode-le pour obtenir le flag. '
        'Tu peux utiliser un terminal Linux ou un outil de décodage Base64.',
        ['Tu connais déjà l’encodage : Base64. Il faut le décoder, sans chercher de mot de passe.',
         'Sur Linux : base64 -d message.txt',
         'Avec Python : python3 -c "import base64; print(base64.b64decode(open(\'message.txt\').read()).decode())"'],
        'Exécuter base64 -d message.txt. Le décodage restitue le flag complet. '
        'Débrief : encoder une donnée ne la rend pas secrète.',
        lambda flag: {'message.txt': base64.b64encode(flag.encode()).decode() + '\n'})

    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
    shifted = 'DEFGHIJKLMNOPQRSTUVWXYZABCdefghijklmnopqrstuvwxyzabc'
    add('crypto-caesar', 'Bootcamp 04 — Trois lettres plus loin', 'Crypto',
        'Le chiffre de César remplace chaque lettre par une autre à distance fixe dans l’alphabet. '
        'Ici, le décalage est +3 : A devient D, B devient E, et Z devient C. Les chiffres et symboles restent inchangés.',
        'Déchiffre `message.txt` en reculant chaque lettre de trois positions. '
        'Le préfixe du flag a lui aussi été décalé. Garde les accolades, chiffres et underscores.',
        ['Pour déchiffrer : D devient A, E devient B, et A devient X.',
         'Utilise une roue de César avec un décalage de -3 ou un outil ROT/Caesar. Préserve la casse.',
         'Sur Linux : tr \'A-Za-z\' \'X-ZA-Wx-za-w\' < message.txt'],
        'Appliquer le décalage -3 à toutes les lettres. '
        'Débrief : un chiffrement peut être réversible et néanmoins très faible.',
        lambda flag: {'message.txt': flag.translate(str.maketrans(alphabet, shifted)) + '\n'})

    def hidden_archive(flag):
        out = io.BytesIO()
        with tarfile.open(fileobj=out, mode='w:gz') as archive:
            for name, text in {'linux-hidden/README.txt': 'Bienvenue ! Le fichier visible n’est pas le seul fichier du dossier.\n',
                               'linux-hidden/.welcome-note': f'Tu as trouvé le fichier caché.\n{flag}\n'}.items():
                data = text.encode()
                item = tarfile.TarInfo(name)
                item.size, item.mode = len(data), 0o644
                archive.addfile(item, io.BytesIO(data))
        return {'linux-hidden.tar.gz': out.getvalue()}

    add('linux-hidden', 'Bootcamp 05 — Le fichier discret', 'Linux',
        'Sous Linux, un nom qui commence par un point désigne un fichier caché dans la liste habituelle. '
        '`ls` liste les fichiers, `ls -a` inclut les fichiers cachés, et `cat` affiche un fichier texte.',
        'Dans ton terminal Linux (Ubuntu, Kali, une VM ou WSL), extrais l’archive avec '
        '`tar -xzf linux-hidden.tar.gz`, puis entre dans le dossier avec `cd linux-hidden`. '
        'Retrouve le fichier caché et lis le flag. Pas besoin de sudo.',
        ['Dans le dossier linux-hidden, lance ls puis ls -a. Compare les deux résultats.',
         'Le nom recherché commence par un point. cat accepte aussi les noms qui commencent par un point.',
         'Exécute : cat .welcome-note'],
        'Extraire l’archive, cd linux-hidden, ls -a puis cat .welcome-note. '
        'Débrief : caché ne signifie ni chiffré ni protégé.', hidden_archive)

    def logs(flag):
        rows = [f'20:00:{i % 60:02d} INFO health_check request={i:03d} status=ok' for i in range(180)]
        rows.insert(97, f'20:01:37 TRAINING recovered_flag={flag}')
        return {'access.log': '\n'.join(rows) + '\n'}

    add('linux-grep', 'Bootcamp 06 — Une ligne dans les logs', 'Linux',
        'Un log est un journal d’événements. `grep` recherche les lignes qui contiennent un texte donné. '
        'Cela évite de lire un gros fichier ligne par ligne.',
        'Le fichier `access.log` contient une seule ligne avec le préfixe `CYBERDUNE{`. '
        'Retrouve-la avec grep et soumets uniquement le flag. Aucun programme à écrire.',
        ['Le mot à chercher est CYBERDUNE. grep affiche toute la ligne qui le contient.',
         'La syntaxe est : grep \'texte à chercher\' nom-du-fichier',
         'Exécute : grep \'CYBERDUNE{\' access.log. Copie seulement le flag, pas l’heure ni recovered_flag=.'],
        'grep \'CYBERDUNE{\' access.log affiche la ligne utile. '
        'Débrief : savoir filtrer du texte est un réflexe essentiel en investigation.', logs)

    credits1 = ("Photo: Milamber's portfolio. CC BY 2.0.\n"
                'License: https://creativecommons.org/licenses/by/2.0/\n'
                'Source: https://www.flickr.com/photos/90956808@N00/276404124\n'
                'Redistributed without changes. Attribution is part of the evidence.\n')
    def photo_archive(flag):
        out = io.BytesIO()
        with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('photo-01.jpg', (photos / 'photo-01.jpg').read_bytes())
            archive.writestr('CREDITS.txt', credits1)
        return {'carte-postale.zip': out.getvalue()}

    add('osint-landmark', 'Bootcamp 07 — La carte postale', 'OSINT',
        'L’OSINT consiste à retrouver et recouper des informations disponibles publiquement. '
        'Une photo peut fournir des indices : architecture, paysage, texte et origine de l’image.',
        'Extrais `carte-postale.zip` et observe `photo-01.jpg`. Dans quelle ville marocaine cette photo a-t-elle été prise ? '
        'Tu peux faire une recherche d’image inversée ou rechercher les indices visibles. '
        'Vérifie la ville avec une source publique. Soumets `CYBERDUNE{nom_de_la_ville}` en lettres latines, sans espaces.',
        ['Observe le grand minaret et la mer. Décris ces deux éléments dans une recherche.',
         'Une recherche d’image inversée (par exemple avec Lens) peut retrouver une page qui identifie le monument.',
         'Le monument est la mosquée Hassan II. Recherche sa ville ; le flag attend la ville, pas le nom de la mosquée.'],
        'Identifier la mosquée Hassan II et confirmer Casablanca. '
        'Une recherche de la photo originale ou de son attribution est également une voie OSINT valable. '
        'Source et licence : https://commons.wikimedia.org/wiki/File:Sunshine_on_mosque_Hassan_II_in_Casablanca,_Morocco_-_Flickr_-_Milamber%27s_portfolio.jpg',
        photo_archive, flag='CYBERDUNE{' + answers['landmark'] + '}')

    credits2 = ('Photo: Bernard Gagnon. CC BY-SA 3.0.\n'
                'License: https://creativecommons.org/licenses/by-sa/3.0/\n'
                'Source: https://commons.wikimedia.org/wiki/File:Hassan_Tower.jpg\n'
                'Changes: EXIF replaced with training GPS coordinates from the source page. Image pixels unchanged.\n'
                'The adapted metadata and photo are distributed under CC BY-SA 3.0.\n')
    def gps_archive(flag):
        out = io.BytesIO()
        with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('photo-02.jpg', gps_jpeg(photos / 'photo-02.jpg'))
            archive.writestr('CREDITS.txt', credits2)
        return {'photo-voyage.zip': out.getvalue()}

    add('osint-gps', 'Bootcamp 08 — La photo se souvient', 'OSINT',
        'Les métadonnées EXIF sont des informations stockées dans un fichier photo. '
        'Certaines contiennent une position GPS. Pour cet exercice, des coordonnées GPS ont été ajoutées à une photo publique.',
        'Extrais `photo-voyage.zip`. Lis les coordonnées GPS de `photo-02.jpg`, puis cherche cette position sur une carte. '
        'Dans quelle ville marocaine se trouve ce lieu ? Soumets `CYBERDUNE{nom_de_la_ville}` en lettres latines. '
        'Tu peux utiliser `exiftool` sur Linux ou un lecteur EXIF. N’envoie pas tes photos personnelles à un service en ligne.',
        ['Télécharge le fichier original du défi. Une capture d’écran peut perdre les métadonnées.',
         'Avec exiftool : exiftool -GPSLatitude -GPSLongitude -GPSLatitudeRef -GPSLongitudeRef photo-02.jpg',
         'La position est 34° 01\' 27" N, 6° 49\' 22" W. Entre-la dans une carte : N est positif et W négatif. Cherche la ville.'],
        'Lire GPSLatitude/GPSLongitude, puis placer 34.024167, -6.822778 sur une carte : Rabat. '
        'L’identification visuelle du monument et la recherche de la source restent des alternatives valables à ce niveau. '
        'Débrief : une photo peut révéler son lieu même sans légende. '
        'Source : https://commons.wikimedia.org/wiki/File:Hassan_Tower.jpg',
        gps_archive, flag='CYBERDUNE{' + answers['gps'] + '}')

    manifest_path.write_text(json.dumps({'pack': 'bootcamp-first-steps-v1', 'challenges': entries}, ensure_ascii=False, indent=2), encoding='utf-8')
    (output / 'ORGANIZER-GUIDE.md').write_text('\n\n'.join(guide), encoding='utf-8')
    print('Built 8 private challenges and organizer guide. No flags printed.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--photos', type=Path, required=True)
    parser.add_argument('--answers', type=Path, required=True, help='Private JSON with landmark and gps city answers.')
    args = parser.parse_args()
    build(args.output, args.photos, json.loads(args.answers.read_text(encoding='utf-8')))
