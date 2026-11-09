"""Translations for imported exercises whose original copy contains Darija.

Fingerprint checks ensure translations stop applying if an organizer edits a
challenge in the admin panel. The English source remains the fallback.
"""
import hashlib
from types import SimpleNamespace

from CTFd.utils.user import get_locale


# SHA-256 digests of the original imported fields. Keep source challenge text
# out of this module so the language pack cannot accidentally expose answers.
SOURCE_HASHES = {
    "bootcamp-2025-3": {
        "name": "ec63c92cc479225dfb09d2ed3960411c5f252fb0c312de429337275384bcbf25",
        "description": "c7604e928946ca107e06e3009fdc9656ad8ed75dc145f441cc25399e621d824f",
    },
    "bootcamp-2025-8": {
        "name": "ab01e593c67cff5eed310542be03e8068438adcd498f2c580a53afcc49eccdbd",
        "description": "40032a8f94832e6b88151ab1821b90cc72e698676dd79602e58fe3822ff1d39d",
    },
    "bootcamp-2025-9": {
        "name": "0b205a48ded60294e7664e3c10b2ea6bec868b10863e3161b9be16c923542219",
        "description": "0bf0e384d23cf15883ea4c66184a8bc56a2fc5a1a51ff124dd4deedb30b7d12f",
    },
    "bootcamp-2025-13": {
        "name": "e50b8f1131e73a10e47d05c44397ebbea9695002a435162c762d0ac36981aee4",
        "description": "2f9f177aa7fc47430abf8f996d194c35e55ecac036d682a6228f5b1d11262ee5",
        "hint": "91ba3068dc641ab03ba92f33415d1ebfc11e0014a0259daf820827bc03bf7482",
    },
    "bootcamp-2025-20": {
        "name": "b46987a196f3c49834c4aa5c4fbefb8a81c14a665b3f4394800865052e131db3",
        "description": "e1ef017d74c999f26407720a49d7784ec6035bd98842a8807047ab8debc87f1f",
    },
    "bootcamp-2025-22": {
        "name": "c12575cd8d7855159b6a5f4f1b5186f16db53324b05871fcbc3777b801a94aae",
        "description": "5f0dd84b1824e0a3d18956ac3fa077c5ccacaf8df7fc2d2185253a42cac61072",
        "hint": "0a61039e25bfe446106624653d2ac0a5f3bdd7bb3e45aa99764210ef1242a8f1",
    },
    "bootcamp-2025-24": {
        "name": "a88b3f9ad82f5413b2ac220b3df16f89d0a431c4a62601733c9afe9e9501a11a",
    },
    "bootcamp-2025-32": {
        "name": "590a9ed812abad5c674ae06596ff220708c42d54b045be99f8f4d2eacb419805",
    },
    "bootcamp-2025-52": {
        "name": "35072c1ae546350e0bfa7ab11d49dc6f129e72ccd57ec7eb671225bbd197c8f1",
        "description": "3dbbc197d987af4ab7f43a13533351a009303292278cdc46a7488ef9697b1889",
    },
    "bootcamp-2025-54": {
        "name": "4791a3caa551624aaf25325567147257bf8468de37b265fcb89d35a3e4848aea",
        "description": "ec2688bfd26dcda7a4ba02be00e453e6472418299079dfdf480f8bd396e75c47",
        "hint": "9594d564282461e381c7ca97ea71d6baabf995d2693da88508d50bc1198e35a5",
    },
    "bootcamp-2025-55": {
        "name": "b8bac3478831db35dc64fcef3f84b0f0a69c8d703ec27d2e3d0bab2f73212d55",
        "description": "29f11d2709b65f56ff07a0555b5ed69b6f00b496078fd7c700286bbccae62d9e",
    },
    "bootcamp-2025-56": {
        "name": "1035a654045138d39064d9a9125b0b2d0ee3d15030279f4c7ec446bd9b191dc9",
        "description": "860c0a912f995e5fb9f8f809135c513c1ec3ec85fb0bb30c1fb259f8d4a17a73",
    },
    "bootcamp-2025-57": {
        "name": "0024744864ac927a2c442f261663cbfedb19ca6922f93906c760a663f1272056",
        "description": "474dbd73cc44f8ba76d5112ac6f36533039dce50d25b34ebf17b6aad995fe774",
    },
    "bootcamp-2025-58": {
        "name": "a78cc8b3f2f200eee41f6d6e0aab4b4425111cdab32d20530407b7a4e51060f1",
        "description": "2db9e0877114be73bc1a19a8f49a0a879e0202835121f633b2f8790e8b4bd713",
    },
    "bootcamp-2025-60": {
        "name": "46a04ccc58f1832a1e5839b6cc30fea82a6edabfe6e14931eb0e26496afb013c",
    },
    "bootcamp-2025-61": {"name": "8b18f5576f6eb5abac2aaa7cd6dbff884a7f53b3f04ce26dcfe4462e13608a27"},
    "bootcamp-2025-63": {
        "name": "04961cd5a5bf81b6880f52115f2b6661d3fcb2d8c92906e00f3da71b3a25506a",
        "description": "0acdfbde3ca178a0589ebb8aed3a5eaff1045d215fb2b9d2f08cdbd0d6e0e722",
        "hint": "f85f3b74bc78a25aaa1bf2a9e74cf681e260acd3bee42dafe85235e66aec87ff",
    },
}


TRANSLATIONS = {'bootcamp-2025-3': {'en': {'name': "Yassir's Gift", 'description': 'Use the recovery ticket to identify the approved audit record for the correct operator. Decode the Base64 envelope, derive the AES key with the supplied PBKDF2 parameters, then authenticate and decrypt the flag. All records are synthetic.'},
                     'fr': {'name': 'Le cadeau de Yassir', 'description': 'Utilisez le ticket de récupération pour identifier le journal approuvé du bon opérateur. Décodez l’enveloppe Base64, dérivez la clé AES avec les paramètres PBKDF2 fournis, puis authentifiez et déchiffrez le flag. Tous les dossiers sont fictifs.'},
                     'ar': {'name': 'هدية ياسير', 'description': 'استخدم تذكرة الاستعادة لتحديد سجل التدقيق المعتمد للمشغّل الصحيح. فك ترميز ظرف Base64، واشتق مفتاح AES باستخدام معاملات PBKDF2 المرفقة، ثم تحقّق من سلامة التشفير وفكّه. جميع السجلات خيالية.'}},
 'bootcamp-2025-8': {'en': {'name': 'Forensics: The Police Report',
                            'description': 'Welcome back to digital forensics! Need a hint? Do you know the '
                                           '`strings` command?'},
                     'fr': {'name': 'Criminalistique : le rapport de police',
                            'description': "Bon retour en analyse numérique ! Besoin d'un indice ? "
                                           'Connaissez-vous la commande `strings` ?'},
                     'ar': {'name': 'التحليل الجنائي: تقرير الشرطة',
                            'description': 'مرحباً بعودتك إلى التحليل الجنائي الرقمي! هل تحتاج إلى تلميح؟ هل '
                                           'تعرف الأمر `strings`؟'}},
 'bootcamp-2025-9': {'en': {'name': 'Police Pursuit',
                            'description': 'I thought I had escaped the police, but they caught up with me. '
                                           'Can you help me get away?'},
                     'fr': {'name': 'La poursuite policière',
                            'description': "Je pensais avoir échappé à la police, mais elle m'a rattrapé. "
                                           "Pouvez-vous m'aider à m'en sortir ?"},
                     'ar': {'name': 'مطاردة الشرطة',
                            'description': 'ظننت أنني أفلتُّ من الشرطة، لكنها لحقت بي. هل يمكنك مساعدتي على '
                                           'الهرب؟'}},
 'bootcamp-2025-13': {'en': {'name': 'Paris Coordinates',
                             'description': 'Find the latitude and longitude of Paris. Submit your answer in '
                                            'this format: `CYBERDUNE{latitude,longitude}`.',
                             'hint': 'Use a map or a geolocation reference to look up the coordinates.'},
                      'fr': {'name': 'Coordonnées de Paris',
                             'description': 'Trouvez la latitude et la longitude de Paris. Soumettez votre '
                                            'réponse au format `CYBERDUNE{latitude,longitude}`.',
                             'hint': 'Consultez une carte ou une source géographique pour trouver les '
                                     'coordonnées.'},
                      'ar': {'name': 'إحداثيات باريس',
                             'description': 'اعثر على خط العرض وخط الطول لباريس، ثم أرسل الإجابة بهذا '
                                            'التنسيق: `CYBERDUNE{latitude,longitude}`.',
                             'hint': 'استخدم خريطة أو مرجعاً جغرافياً للعثور على الإحداثيات.'}},
 'bootcamp-2025-20': {'en': {'name': 'Modified App',
                             'description': 'You have a modified APK named `fake_app.apk`. It looks like '
                                            'CapCut Pro, but it contains hidden clues. Inspect the APK, '
                                            'search for an obfuscated or encoded string, and recover the '
                                            'flag in the format `CYBERDUNE{...}`.'},
                      'fr': {'name': 'Application modifiée',
                             'description': "Vous disposez d'un APK modifié nommé `fake_app.apk`. Il "
                                            'ressemble à CapCut Pro, mais contient des indices cachés. '
                                            'Analysez-le, recherchez une chaîne masquée ou encodée, puis '
                                            'retrouvez le flag au format `CYBERDUNE{...}`.'},
                      'ar': {'name': 'تطبيق معدّل',
                             'description': 'لديك ملف APK معدّلاً باسم `fake_app.apk`. يبدو مثل CapCut Pro، '
                                            'لكنه يحتوي على أدلة مخفية. افحص الملف وابحث عن نص مخفي أو '
                                            'مرمّز، ثم استخرج العلم بالتنسيق `CYBERDUNE{...}`.'}},
 'bootcamp-2025-22': {'en': {'name': 'Compiled Python',
                             'description': 'The Python program is compiled. Can you decompile it to recover '
                                            'the flag?',
                             'hint': 'Try an online Python decompiler, then inspect and analyze the '
                                     'recovered source code.'},
                      'fr': {'name': 'Python compilé',
                             'description': 'Le programme Python est compilé. Pouvez-vous le décompiler pour '
                                            'retrouver le flag ?',
                             'hint': 'Essayez un décompilateur Python, puis examinez et analysez le code '
                                     'source obtenu.'},
                      'ar': {'name': 'برنامج Python مترجم',
                             'description': 'برنامج Python مُترجم إلى صيغة تنفيذية. هل يمكنك فك ترجمته '
                                            'لاستعادة العلم؟',
                             'hint': 'جرّب أداة لفك تجميع Python، ثم افحص الشيفرة المصدرية الناتجة '
                                     'وحلّلها.'}},
 'bootcamp-2025-52': {'en': {'name': 'Image Metadata',
                             'description': 'Welcome to this beginner forensics challenge. Inspect the '
                                            "image's metadata to find the flag."},
                      'fr': {'name': "Métadonnées de l'image",
                             'description': 'Bienvenue dans ce défi de criminalistique numérique pour '
                                            "débutants. Examinez les métadonnées de l'image pour trouver le "
                                            'flag.'},
                      'ar': {'name': 'بيانات الصورة الوصفية',
                             'description': 'مرحباً بك في تحدي التحليل الجنائي الرقمي للمبتدئين. افحص بيانات '
                                            'الصورة الوصفية للعثور على العلم.'}},
 'bootcamp-2025-55': {'en': {'name': 'Potato',
                             'description': 'Potatoes are delicious! This challenge was created by '
                                            'Cyber0xWolF.'},
                      'fr': {'name': 'Pomme de terre',
                             'description': "Les pommes de terre, c'est délicieux ! Ce défi a été créé par "
                                            'Cyber0xWolF.'},
                      'ar': {'name': 'البطاطا',
                             'description': 'البطاطا لذيذة! هذا التحدي من إعداد Cyber0xWolF.'}},
 'bootcamp-2025-61': {'en': {'name': 'Free Palestine!'},
                      'fr': {'name': 'Liberté pour la Palestine !'},
                      'ar': {'name': 'الحرية لفلسطين!'}},
 'bootcamp-2025-24': {'en': {'name': 'Mouse and Cheese'},
                      'fr': {'name': 'La souris et le fromage'},
                      'ar': {'name': 'الفأر والجبن'}},
 'bootcamp-2025-32': {'en': {'name': 'Keypad Cipher'},
                      'fr': {'name': 'Chiffrement du clavier'},
                      'ar': {'name': 'شفرة لوحة المفاتيح'}},
 'bootcamp-2025-54': {'en': {'name': 'Read the Rules',
                             'description': 'Read the rules page, then inspect its source code to find the '
                                            'flag. Submit it in the required format.',
                             'hint': 'Open the rules page source and search for the flag.'},
                      'fr': {'name': 'Lisez le règlement',
                             'description': 'Lisez la page du règlement, puis examinez son code source pour '
                                            'trouver le flag. Envoyez-le au format demandé.',
                             'hint': 'Ouvrez le code source de la page du règlement et recherchez le flag.'},
                      'ar': {'name': 'اقرأ القواعد',
                             'description': 'اقرأ صفحة القواعد، ثم افحص مصدرها للعثور على العلم. أرسله '
                                            'بالتنسيق المطلوب.',
                             'hint': 'افتح مصدر صفحة القواعد وابحث عن العلم.'}},
 'bootcamp-2025-56': {'en': {'name': 'Memory Game',
                             'description': 'Can you beat the memory game and recover the flag? Use the '
                                            'attached challenge file and follow its instructions.'},
                      'fr': {'name': 'Jeu de mémoire',
                             'description': 'Pouvez-vous gagner au jeu de mémoire et retrouver le flag ? '
                                            'Utilisez le fichier joint et suivez ses instructions.'},
                      'ar': {'name': 'لعبة الذاكرة',
                             'description': 'هل يمكنك الفوز في لعبة الذاكرة واستخراج العلم؟ استخدم الملف '
                                            'المرفق واتبع تعليماته.'}},
 'bootcamp-2025-57': {'en': {'name': 'Banking Incident',
                             'description': "Youssef needs access to his money, but the bank's system has "
                                            'gone down. Investigate the incident and recover all three '
                                            'flags.'},
                      'fr': {'name': 'Incident bancaire',
                             'description': "Youssef a besoin d'accéder à son argent, mais le système de la "
                                            "banque est en panne. Enquêtez sur l'incident et retrouvez les "
                                            'trois flags.'},
                      'ar': {'name': 'حادث مصرفي',
                             'description': 'يحتاج يوسف إلى أمواله، لكن نظام البنك تعطل. حقّق في الحادث '
                                            'واستخرج الأعلام الثلاثة.'}},
 'bootcamp-2025-58': {'en': {'name': 'Loaded Sandwich',
                             'description': 'Think this challenge is easy? Give it a try and recover the '
                                            'flag from the provided challenge files.'},
                      'fr': {'name': 'Sandwich garni',
                             'description': 'Vous pensez que ce défi est facile ? Essayez-le et retrouvez le '
                                            'flag dans les fichiers fournis.'},
                      'ar': {'name': 'شطيرة محشوة',
                             'description': 'هل تظن أن هذا التحدي سهل؟ جرّبه واستخرج العلم من الملفات '
                                            'المرفقة.'}},
 'bootcamp-2025-60': {'en': {'name': 'Very Difficult'},
                      'fr': {'name': 'Très difficile'},
                      'ar': {'name': 'صعب جداً'}},
 'bootcamp-2025-63': {'en': {'name': 'Hardware Identification',
                             'description': 'Identify the hardware board shown in the challenge materials. '
                                            'Submit its name in the required flag format.',
                             'hint': 'Read the linked article by Travis Goodspeed for clues about '
                                     'identifying the board.'},
                      'fr': {'name': 'Identification matérielle',
                             'description': 'Identifiez la carte électronique montrée dans les éléments du '
                                            'défi. Envoyez son nom au format de flag demandé.',
                             'hint': "Lisez l'article lié de Travis Goodspeed pour trouver des indices sur "
                                     'la carte.'},
                      'ar': {'name': 'تحديد اللوحة الإلكترونية',
                             'description': 'حدّد اللوحة الإلكترونية الظاهرة في مواد التحدي، ثم أرسل اسمها '
                                            'بتنسيق العلم المطلوب.',
                             'hint': 'اقرأ مقالة Travis Goodspeed المرتبطة للعثور على دلائل تساعدك في تحديد '
                                     'اللوحة.'}}}


# Keep new Academy exercises in step with the site's English, French and Arabic
# language setting. Source fingerprints preserve organizer edits.
_NEW_EXERCISE_TRANSLATIONS = {
    "field-notes": {
        "en": {"name": "Field Notes", "description": "Investigate a fictional archive using the case code and project index. Correlate the matching project with its archived public post, then decode the note. All people, projects, and records are synthetic; no external accounts or websites are involved.", "hint": "Match the exact case code first, then verify both the project and handle before decoding the archived note."},
        "fr": {"name": "Notes de terrain", "description": "Enquêtez dans une archive fictive à l’aide du code de dossier et de l’index des projets. Reliez le projet correspondant à sa publication publique archivée, puis décodez la note. Toutes les personnes, tous les projets et tous les dossiers sont fictifs ; aucun compte ni site externe n’est utilisé.", "hint": "Commencez par le code exact du dossier, puis vérifiez le projet et le pseudonyme avant de décoder la note archivée."},
        "ar": {"name": "ملاحظات ميدانية", "description": "تحقّق في أرشيف خيالي باستخدام رمز القضية وفهرس المشاريع. اربط المشروع المطابق بمنشوره العام المؤرشف، ثم فك ترميز الملاحظة. جميع الأشخاص والمشاريع والسجلات خيالية، ولا تُستخدم حسابات أو مواقع خارجية.", "hint": "طابق رمز القضية بدقة أولاً، ثم تحقّق من المشروع واسم المستخدم قبل فك ترميز الملاحظة المؤرشفة."},
    },
    "client-side-record-gate": {
        "en": {"name": "Client-Side Record Gate", "description": "Audit a fictional offline records viewer. Use the support ticket to identify the requested record, inspect how the browser selects records, and retrieve the matching entry. The files run locally and never contact a server.", "hint": "The page reads a record identifier from the URL. Follow that identifier into the local record catalog."},
        "fr": {"name": "Accès aux dossiers côté client", "description": "Auditez une visionneuse de dossiers fictive et hors ligne. Utilisez le ticket d’assistance pour identifier le dossier demandé, examinez comment le navigateur le sélectionne, puis récupérez l’entrée correspondante. Les fichiers s’exécutent localement et ne contactent aucun serveur.", "hint": "La page lit l’identifiant du dossier dans l’URL. Suivez cet identifiant dans le catalogue local."},
        "ar": {"name": "بوابة السجلات في المتصفح", "description": "افحص عارض سجلات خيالياً يعمل دون اتصال. استخدم تذكرة الدعم لتحديد السجل المطلوب، وافحص طريقة اختياره في المتصفح، ثم استخرج المدخل المطابق. تعمل الملفات محلياً ولا تتصل بأي خادم.", "hint": "تقرأ الصفحة معرّف السجل من الرابط. تتبّع هذا المعرّف في فهرس السجلات المحلي."},
    },
    "shell-history-recovery": {
        "en": {"name": "Shell History Recovery", "description": "Review a synthetic home-directory backup. Follow the analyst's shell history to the hidden transfer file, decode it, and read the recovered receipt for your flag.", "hint": "List hidden archive paths, then trace the base64 command recorded in .bash_history."},
        "fr": {"name": "Récupération depuis l’historique du shell", "description": "Examinez une sauvegarde fictive d’un répertoire personnel. Suivez l’historique du shell de l’analyste jusqu’au fichier de transfert caché, décodez-le et lisez le reçu récupéré pour trouver votre flag.", "hint": "Affichez les chemins cachés de l’archive, puis suivez la commande base64 dans .bash_history."},
        "ar": {"name": "استعادة من سجل الطرفية", "description": "افحص نسخة احتياطية خيالية لمجلد المستخدم. اتبع سجل أوامر المحلل للوصول إلى ملف النقل المخفي، وفك ترميزه، ثم اقرأ الإيصال المستعاد للعثور على العلم.", "hint": "اعرض المسارات المخفية في الأرشيف، ثم تتبّع أمر base64 المسجّل في .bash_history."},
    },
    "udp-fragment-capture": {
        "en": {"name": "UDP Fragment Capture", "description": "Analyze a synthetic Ethernet capture. Isolate the UDP stream sent to the training collector, order its numbered fragments, join their hexadecimal data, and decode the result.", "hint": "Filter on UDP destination port 31337. Ignore diagnostic packets without a sequence number."},
        "fr": {"name": "Capture de fragments UDP", "description": "Analysez une capture Ethernet synthétique. Isolez le flux UDP envoyé au collecteur d’entraînement, triez ses fragments numérotés, assemblez leurs données hexadécimales et décodez le résultat.", "hint": "Filtrez le port UDP de destination 31337. Ignorez les paquets de diagnostic sans numéro de séquence."},
        "ar": {"name": "التقاط أجزاء UDP", "description": "حلّل التقاطاً خيالياً لحركة Ethernet. اعزل تدفق UDP المرسل إلى خادم التدريب، ورتّب أجزائه المرقّمة، واجمع البيانات الست عشرية ثم فك ترميزها.", "hint": "رشّح حسب منفذ UDP الوجهة 31337، وتجاهل حزم التشخيص التي لا تحمل رقم تسلسل."},
    },
}

from .replacement_challenges import CHALLENGES as _ACADEMY_CHALLENGES

for _challenge in _ACADEMY_CHALLENGES:
    if _challenge["slug"] in _NEW_EXERCISE_TRANSLATIONS:
        SOURCE_HASHES[_challenge["slug"]] = {
            field: hashlib.sha256(_challenge[field].encode("utf-8")).hexdigest()
            for field in ("name", "description", "hint")
        }
        TRANSLATIONS[_challenge["slug"]] = _NEW_EXERCISE_TRANSLATIONS[_challenge["slug"]]

_INTERMEDIATE_STARTER_TRANSLATIONS = {
    "base64-trail": {
        "fr": "Suivez la livraison acceptée jusqu’à son enveloppe. Décodez-la, associez son identifiant de clé au trousseau, inversez le masque XOR répétitif et vérifiez le CRC avant de soumettre le flag.",
        "ar": "تتبّع عملية التسليم المقبولة إلى الظرف المطابق. فك ترميزه، وطابق معرّف المفتاح مع مجموعة المفاتيح، واعكس قناع XOR المتكرر، ثم تحقّق من CRC قبل إرسال العلم.",
    },
    "image-metadata": {
        "fr": "Examinez les métadonnées de l’image pour trouver son identifiant d’acquisition. Reliez-le à l’enregistrement de preuve vérifié, utilisez son identifiant de clé pour inverser le masque d’octets et validez la somme de contrôle.",
        "ar": "افحص بيانات الصورة الوصفية للعثور على معرّف الاقتناء. اربطه بسجل الأدلة الموثق، واستخدم معرّف المفتاح لعكس قناع البايتات، ثم تحقّق من checksum للسجل المستعاد.",
    },
    "public-trail": {
        "fr": "Enquêtez dans l’archive publique fictive. Reliez le code projet du briefing au bon profil, décodez son enveloppe, puis utilisez la clé d’archive et la somme de contrôle pour retrouver le flag. Aucune personne réelle ne doit être contactée.",
        "ar": "ابحث في الأرشيف العام الخيالي. طابق رمز المشروع في الموجز مع الملف الصحيح، وفك ترميز الظرف، ثم استخدم مفتاح الأرشيف وchecksum لاستعادة العلم. لا حاجة للتواصل مع أشخاص حقيقيين.",
    },
    "hidden-files": {
        "fr": "Examinez l’archive tar dans un répertoire d’entraînement. Comparez le manifeste des instantanés, trouvez le reçu caché actuel, décodez ses couches et utilisez la clé indiquée pour retrouver le flag. N’extrayez pas d’archives inconnues dans un dossier important.",
        "ar": "افحص أرشيف tar داخل مجلد تدريب. قارن بيان اللقطات، واعثر على الإيصال المخفي الحالي، وفك طبقاته، ثم استخدم المفتاح المشار إليه لاستعادة العلم. لا تفك أرشيفات غير موثوقة داخل مجلدات مهمة.",
    },
    "packet-courier": {
        "fr": "Analysez la capture synthétique dans Wireshark. Isolez la session complète du collecteur, réassemblez ses fragments numérotés, inversez le masque XOR répétitif avec la clé de session et validez le CRC. Les adresses sont réservées à la documentation.",
        "ar": "حلّل الالتقاط الاصطناعي في Wireshark. اعزل جلسة المُجمّع المكتملة، وأعد تجميع الأجزاء المرقمة، واعكس قناع XOR المتكرر بمفتاح الجلسة، ثم تحقّق من CRC. العناوين مخصصة للأمثلة التوثيقية.",
    },
    "archive-layers": {
        "fr": "Parcourez les couches d’encodage de l’archive ZIP, identifiez la clé dans les notes de preuve, inversez le masque d’octets et vérifiez la somme de contrôle finale pour retrouver le flag.",
        "ar": "اتبع طبقات الترميز في أرشيف ZIP، وحدّد مادة المفتاح في ملاحظات الأدلة، واعكس قناع البايتات، ثم تحقّق من checksum النهائي لاستعادة العلم.",
    },
}

from .catalog import starter_rows as _starter_rows

for _starter in _starter_rows():
    if _starter["slug"] not in _INTERMEDIATE_STARTER_TRANSLATIONS:
        continue
    _starter_fields = {field: _starter[field] for field in ("name", "description", "hint")}
    SOURCE_HASHES[_starter["slug"]] = {
        field: hashlib.sha256(value.encode("utf-8")).hexdigest()
        for field, value in _starter_fields.items()
    }
    TRANSLATIONS[_starter["slug"]] = {
        "en": _starter_fields,
        "fr": {"name": _starter["name"], "description": _INTERMEDIATE_STARTER_TRANSLATIONS[_starter["slug"]]["fr"], "hint": ""},
        "ar": {"name": _starter["name"], "description": _INTERMEDIATE_STARTER_TRANSLATIONS[_starter["slug"]]["ar"], "hint": ""},
    }

_AUTHORED_TRANSLATIONS = {
    "cache-boundary": {
        "fr": {"name": "Frontière du cache", "description": "Reconstituez le décodage unique des pourcentages et la normalisation des chemins côté edge, puis reliez la trace de l’incident à la réponse backend correspondante. Décodez le corps sélectionné pour retrouver votre flag."},
        "ar": {"name": "حدود الذاكرة المؤقتة", "description": "أعد بناء خطوة فك الترميز الوحيدة للمسارات وكيفية توحيدها عند الحافة، ثم اربط سجل الحادث باستجابة الخادم الخلفي المطابقة. فك ترميز محتوى الاستجابة المختارة لاستعادة العلم."},
    },
    "nonce-reuse-audit": {
        "fr": {"name": "Audit de réutilisation du nonce", "description": "Une capture d’audit contient des enregistrements chiffrés par un service ayant réutilisé un nonce de chiffrement par flot. Identifiez la paire clé-nonce concernée, utilisez le message d’audit connu pour retrouver l’autre texte en clair et soumettez le flag."},
        "ar": {"name": "تدقيق إعادة استخدام nonce", "description": "يحتوي سجل التدقيق على بيانات مشفرة بخدمة أعادت استخدام nonce لتشفير التدفق. حدّد زوج المفتاح وnonce المرتبط، واستخدم رسالة التدقيق المعروفة لاستعادة النص الآخر ثم أرسل العلم."},
    },
    "frame-reassembly": {
        "fr": {"name": "Réassemblage des trames", "description": "Une acquisition endommagée contient des enregistrements entrelacés. Validez leurs sommes de contrôle, sélectionnez la session concernée, rétablissez l’ordre des octets et décompressez les preuves pour retrouver votre flag."},
        "ar": {"name": "إعادة تجميع الإطارات", "description": "يحتوي الالتقاط المتضرر على سجلات متداخلة. تحقّق من مجموعات التحقق، وحدّد جلسة الحادث، وأعد ترتيب البايتات ثم فك ضغط الأدلة لاستعادة العلم."},
    },
    "atlas-ledger": {
        "fr": {"name": "Registre Atlas", "description": "Reliez l’index d’un dossier fictif à deux jeux de données publics archivés. Vérifiez la cohérence du projet et du pseudonyme, appliquez les conditions de publication et de date, puis inversez la transformation documentée. Personnes, comptes et sites sont fictifs."},
        "ar": {"name": "سجل أطلس", "description": "اربط فهرس قضية خيالية بمجموعتي بيانات عامتين مؤرشفتين. تحقّق من تطابق المشروع والاسم المستعار، وطبّق شروط النشر والوقت، ثم اعكس تحويل البايتات الموضح. الأشخاص والحسابات والمواقع خيالية."},
    },
    "opcode-relay": {
        "fr": {"name": "Relais d’opcodes", "description": "Inversez un petit programme de machine virtuelle à partir de sa spécification et de son bytecode. Exécutez les transformations d’état dans l’ordre, puis retrouvez l’entrée d’origine depuis les registres finaux."},
        "ar": {"name": "ترحيل تعليمات الآلة", "description": "اعكس برنامج آلة افتراضية صغيراً بالاعتماد على مواصفات التعليمات والـbytecode. نفّذ تحويلات الحالة بالترتيب، ثم استخرج الإدخال الأصلي من السجلات النهائية."},
    },
    "heap-ledger": {
        "fr": {"name": "Registre du tas", "description": "Analysez un instantané statique de l’allocateur. Reconstituez le lien tcache protégé, localisez l’objet pointé dans l’image mémoire et annulez son masque dérivé du pointeur. Aucun code natif n’est exécuté."},
        "ar": {"name": "سجل الذاكرة الديناميكية", "description": "حلّل لقطة ثابتة للمخصّص. أعد بناء رابط tcache المحمي، واعثر على الكائن المشار إليه في صورة الذاكرة، ثم أزل قناعه المشتق من المؤشر. لا يُنفّذ أي كود أصلي."},
    },
    "rotation-recovery": {
        "fr": {"name": "Récupération après rotation", "description": "Examinez une sauvegarde fictive d’un répertoire Linux et des journaux d’audit rotatifs. Identifiez le compte et la session à l’origine du transfert conservé, suivez les commandes enregistrées et décodez le reçu récupéré."},
        "ar": {"name": "استعادة السجل المرحّل", "description": "افحص نسخة احتياطية خيالية لمجلد Linux وسجلات تدقيق مرحّلة. حدّد الحساب والجلسة التي أنشأت عملية النقل المتبقية، واتبع الأوامر المسجّلة، ثم فك ترميز الإيصال المستعاد."},
    },
    "dns-exfiltration": {
        "fr": {"name": "Exfiltration DNS", "description": "Étudiez une capture DNS synthétique pour retrouver une session d’exfiltration fictive. Isolez le bon client et le domaine collecteur, classez les fragments selon leurs étiquettes et décodez le message reconstitué."},
        "ar": {"name": "استخراج البيانات عبر DNS", "description": "افحص التقاط DNS خيالياً للعثور على جلسة استخراج بيانات. اعزل العميل والمجال الصحيحين، ورتّب الأجزاء بحسب التسميات، ثم فك ترميز الرسالة المكتملة."},
    },
    "constraint-mosaic": {
        "fr": {"name": "Mosaïque de contraintes", "description": "Rapprochez deux registres de maintenance fictifs à l’aide des règles d’acceptation et de l’heure limite. Sélectionnez l’unique exécution valide, remettez ses blocs dans l’ordre et inversez la transformation propre à cette exécution."},
        "ar": {"name": "فسيفساء القيود", "description": "طابق سجلّي صيانة خياليين باستخدام شروط القبول والوقت النهائي. اختر التشغيل الصحيح الوحيد، ورتّب كتله، ثم اعكس التحويل الخاص به لاستعادة العلم."},
    },
    "tcache-chain": {
        "fr": {"name": "Chaîne tcache", "description": "Reconstituez deux chaînes d’allocateur protégées par safe-linking dans un instantané synthétique du tas. Suivez le bac désigné jusqu’à son entrée terminale, trouvez l’enregistrement survivant dans ce bloc et inversez son masque dérivé du pointeur. Aucun code natif n’est exécuté."},
        "ar": {"name": "سلسلة tcache", "description": "أعد بناء سلسلتين للمخصّص محميتين بـsafe-linking في لقطة اصطناعية للذاكرة. اتبع قائمة الفئة المحددة حتى آخر مدخل، واعثر على السجل المتبقي في ذلك الكتلة، ثم اعكس القناع المشتق من المؤشر. لا يُنفّذ أي كود أصلي."},
    },
    "journal-window": {
        "fr": {"name": "Fenêtre du journal", "description": "Reliez un journal système synthétique entre plusieurs démarrages, utilisateurs et processus pour identifier le transfert de la session SSH conservée. Récupérez le reçu caché à l’aide des étapes de décodage documentées."},
        "ar": {"name": "نافذة السجل", "description": "اربط سجلاً نظامياً اصطناعياً عبر عمليات إقلاع ومستخدمين وعمليات مختلفة لتحديد النقل المرتبط بجلسة SSH المتبقية. استعد الإيصال المخفي باتباع خطوات فك الترميز الموضحة."},
    },
    "sequence-window": {
        "fr": {"name": "Fenêtre de séquence", "description": "Analysez une capture UDP synthétique avec des sessions entrelacées, des fragments désordonnés et un doublon endommagé. Validez chaque enregistrement décodé, reconstituez la séquence complète et retrouvez le message."},
        "ar": {"name": "نافذة التسلسل", "description": "حلّل التقاط UDP اصطناعياً يحوي جلسات متداخلة وأجزاء غير مرتبة ونسخة مكررة تالفة. تحقّق من كل سجل بعد فك ترميزه، وأعد بناء التسلسل كاملاً، ثم استخرج الرسالة."},
    },
    "http-page-capture": {
        "fr": {"name": "Capture de page HTTP", "description": "Examinez une capture HTTP synthétique dans Wireshark. Retrouvez la page de tableau de bord, suivez la ressource qu’elle référence dans le flux TCP, puis décodez le corps de la réponse correspondante pour retrouver votre flag. La capture est hors ligne et ne contient aucun service réel."},
        "ar": {"name": "التقاط صفحة HTTP", "description": "افحص التقاط HTTP اصطناعياً في Wireshark. اعثر على صفحة لوحة المعلومات، واتبع المورد الذي تشير إليه ضمن تدفق TCP، ثم فك ترميز محتوى الاستجابة المطابقة لاستعادة العلم. الالتقاط محلي ولا يحتوي على أي خدمات حقيقية."},
    },
}

from .authored_challenges import CHALLENGES as _ORIGINAL_CHALLENGES

for _challenge in _ORIGINAL_CHALLENGES:
    fields = {"name": _challenge["name"], "description": _challenge["description"]}
    SOURCE_HASHES[_challenge["slug"]] = {
        field: hashlib.sha256(value.encode("utf-8")).hexdigest()
        for field, value in fields.items()
    }
    TRANSLATIONS[_challenge["slug"]] = {
        "en": fields,
        **_AUTHORED_TRANSLATIONS[_challenge["slug"]],
    }

_EASY_FLAG_TRANSLATIONS = {
    "bootcamp-2025-8": {
        "en": {
            "description": "Analyze the supplied disk image, recover the deleted evidence record, and decode its letter-rotated text to submit the flag.",
            "hint": "Inspect the filesystem and deleted entries; the recovered text uses a reversible alphabet rotation.",
        },
        "fr": {
            "description": "Analysez l’image disque fournie, récupérez l’enregistrement supprimé et décodez son texte dont les lettres ont été décalées pour trouver le flag.",
            "hint": "Examinez le système de fichiers et les entrées supprimées ; le texte récupéré utilise une rotation alphabétique réversible.",
        },
        "ar": {
            "description": "حلّل صورة القرص المرفقة، واستعد سجل الأدلة المحذوف، ثم فك تدوير حروف النص لإرسال العلم.",
            "hint": "افحص نظام الملفات والمدخلات المحذوفة؛ النص المستعاد يستخدم تدويراً قابلاً للعكس للحروف.",
        },
    },
    "bootcamp-2025-52": {
        "en": {
            "description": "Inspect the image metadata, locate the encoded evidence value, and decode it to submit the flag.",
            "hint": "Check metadata fields beyond the visible image properties; the note uses a reversible alphabet rotation.",
        },
        "fr": {
            "description": "Examinez les métadonnées de l’image, trouvez la valeur d’indice encodée et décodez-la pour soumettre le flag.",
            "hint": "Vérifiez les champs au-delà des propriétés visibles ; la note utilise une rotation alphabétique réversible.",
        },
        "ar": {
            "description": "افحص بيانات الصورة الوصفية، واعثر على قيمة الدليل المرمّزة ثم فك ترميزها لإرسال العلم.",
            "hint": "تحقّق من الحقول الإضافية في البيانات الوصفية؛ الملاحظة تستخدم تدويراً قابلاً للعكس للحروف.",
        },
    },
}

for _slug, _languages in _EASY_FLAG_TRANSLATIONS.items():
    _hashes = dict(SOURCE_HASHES.get(_slug, {}))
    _hashes.update({
        field: hashlib.sha256(_languages["en"][field].encode("utf-8")).hexdigest()
        for field in ("description", "hint")
    })
    SOURCE_HASHES[_slug] = _hashes
    for _language, _fields in _languages.items():
        TRANSLATIONS.setdefault(_slug, {}).setdefault(_language, {}).update(_fields)

_gift_fields = {
    "name": "Yassir's Gift",
    "description": "Use the recovery ticket to identify the approved audit record for the correct operator. Decode the Base64 envelope, derive the AES key with the supplied PBKDF2 parameters, then authenticate and decrypt the flag. All records are synthetic.",
}
SOURCE_HASHES["bootcamp-2025-3"] = {
    field: hashlib.sha256(value.encode("utf-8")).hexdigest()
    for field, value in _gift_fields.items()
}


def localize_challenge(challenge):
    """Return a non-persistent view with translated public challenge fields."""
    values = {column.key: getattr(challenge, column.key) for column in challenge.__table__.columns}
    language = str(get_locale() or "en").replace("_", "-").split("-")[0]
    if language not in ("en", "fr", "ar"):
        language = "en"
    translations = TRANSLATIONS.get(challenge.slug, {}).get(language, {})
    for field, digest in SOURCE_HASHES.get(challenge.slug, {}).items():
        source = getattr(challenge, field, None)
        if source is None or hashlib.sha256(source.encode("utf-8")).hexdigest() != digest:
            continue
        if field in translations:
            values[field] = translations[field]
    return SimpleNamespace(**values)
