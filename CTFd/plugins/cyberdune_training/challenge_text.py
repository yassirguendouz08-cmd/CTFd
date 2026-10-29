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
    "bootcamp-2025-8": {"description": "40032a8f94832e6b88151ab1821b90cc72e698676dd79602e58fe3822ff1d39d"},
    "bootcamp-2025-9": {"description": "0bf0e384d23cf15883ea4c66184a8bc56a2fc5a1a51ff124dd4deedb30b7d12f"},
    "bootcamp-2025-13": {
        "description": "2f9f177aa7fc47430abf8f996d194c35e55ecac036d682a6228f5b1d11262ee5",
        "hint": "91ba3068dc641ab03ba92f33415d1ebfc11e0014a0259daf820827bc03bf7482",
    },
    "bootcamp-2025-20": {"description": "e1ef017d74c999f26407720a49d7784ec6035bd98842a8807047ab8debc87f1f"},
    "bootcamp-2025-22": {"hint": "0a61039e25bfe446106624653d2ac0a5f3bdd7bb3e45aa99764210ef1242a8f1"},
    "bootcamp-2025-52": {"description": "3dbbc197d987af4ab7f43a13533351a009303292278cdc46a7488ef9697b1889"},
    "bootcamp-2025-55": {"description": "29f11d2709b65f56ff07a0555b5ed69b6f00b496078fd7c700286bbccae62d9e"},
    "bootcamp-2025-61": {"name": "8b18f5576f6eb5abac2aaa7cd6dbff884a7f53b3f04ce26dcfe4462e13608a27"},
}


TRANSLATIONS = {
    "bootcamp-2025-3": {
        "en": {
            "name": "Marlithor's Gift",
            "description": "A quick beginner challenge from marlithor_cyber. Decode the Base64 text below to recover the flag.\n\n`Q1lCRVJEVU5Fe2Jzc2E3dGFrX21saV9qYmFkdGlfaGFkYV9hc3NsYW5fZWFzeV9oaWhpfQ==`",
        },
        "fr": {
            "name": "Le cadeau de Marlithor",
            "description": "Un défi d'initiation proposé par marlithor_cyber. Décodez le texte Base64 ci-dessous pour retrouver le flag.\n\n`Q1lCRVJEVU5Fe2Jzc2E3dGFrX21saV9qYmFkdGlfaGFkYV9hc3NsYW5fZWFzeV9oaWhpfQ==`",
        },
        "ar": {
            "name": "هدية من Marlithor",
            "description": "تحدٍّ تمهيدي سهل من marlithor_cyber. فكّ ترميز نص Base64 أدناه لاستخراج العلم.\n\n`Q1lCRVJEVU5Fe2Jzc2E3dGFrX21saV9qYmFkdGlfaGFkYV9hc3NsYW5fZWFzeV9oaWhpfQ==`",
        },
    },
    "bootcamp-2025-8": {
        "en": {"description": "Welcome back to digital forensics! Need a hint? Sure. Do you know the `strings` command?"},
        "fr": {"description": "Bienvenue à nouveau en investigation numérique ! Besoin d'un indice ? Bien sûr. Connaissez-vous la commande `strings` ?"},
        "ar": {"description": "مرحباً بعودتك إلى التحليل الجنائي الرقمي! هل تحتاج إلى تلميح؟ بالطبع. هل تعرف الأمر `strings`؟"},
    },
    "bootcamp-2025-9": {
        "en": {"description": "I thought I had escaped the police, but they caught up with me. Can you help me get out of this situation?"},
        "fr": {"description": "Je pensais avoir échappé à la police, mais elle m'a rattrapé. Pouvez-vous m'aider à m'en sortir ?"},
        "ar": {"description": "ظننت أنني أفلتُ من الشرطة، لكنها لحقت بي. هل يمكنك مساعدتي على الخروج من هذا المأزق؟"},
    },
    "bootcamp-2025-13": {
        "en": {
            "description": "Find the latitude and longitude of Paris. Submit your answer in this format: `CYBERDUNE{latitude,longitude}`.",
            "hint": "Use a map or a geolocation reference to look up the coordinates.",
        },
        "fr": {
            "description": "Trouvez la latitude et la longitude de Paris. Soumettez votre réponse au format `CYBERDUNE{latitude,longitude}`.",
            "hint": "Consultez une carte ou une source de géolocalisation pour trouver les coordonnées.",
        },
        "ar": {
            "description": "اعثر على خط العرض وخط الطول لمدينة باريس، ثم أرسل الإجابة بهذا التنسيق: `CYBERDUNE{latitude,longitude}`.",
            "hint": "استخدم خريطة أو مرجعاً جغرافياً للعثور على الإحداثيات.",
        },
    },
    "bootcamp-2025-20": {
        "en": {
            "description": "You have a modified APK named `fake_app.apk`. It looks like CapCut Pro, but it contains hidden clues. Inspect the APK, search for an obfuscated or encoded string, and recover the flag in the format `CYBERDUNE{...}`."
        },
        "fr": {
            "description": "Vous disposez d'un APK modifié nommé `fake_app.apk`. Il ressemble à CapCut Pro, mais contient des indices cachés. Analysez-le, recherchez une chaîne masquée ou encodée, puis retrouvez le flag au format `CYBERDUNE{...}`."
        },
        "ar": {
            "description": "لديك ملف APK معدّلاً باسم `fake_app.apk`. يبدو مثل CapCut Pro، لكنه يحتوي على أدلة مخفية. افحص الملف وابحث عن نص مخفي أو مرمّز، ثم استخرج العلم بالتنسيق `CYBERDUNE{...}`."
        },
    },
    "bootcamp-2025-22": {
        "en": {"hint": "Try an online Python decompiler, then inspect and analyze the recovered source code."},
        "fr": {"hint": "Essayez un décompilateur Python en ligne, puis examinez et analysez le code source obtenu."},
        "ar": {"hint": "جرّب أداة لفك تجميع Python عبر الإنترنت، ثم افحص الشيفرة المصدرية الناتجة وحلّلها."},
    },
    "bootcamp-2025-52": {
        "en": {"description": "Welcome to this beginner forensics challenge. Inspect the image's metadata to find the flag."},
        "fr": {"description": "Bienvenue dans ce défi d'initiation en investigation numérique. Examinez les métadonnées de l'image pour trouver le flag."},
        "ar": {"description": "مرحباً بك في تحدي التحليل الجنائي الرقمي للمبتدئين. افحص بيانات الصورة الوصفية للعثور على العلم."},
    },
    "bootcamp-2025-55": {
        "en": {"description": "Potatoes are delicious! This challenge is brought to you by Cyber0xWolF."},
        "fr": {"description": "Les pommes de terre, c'est délicieux ! Ce défi est proposé par Cyber0xWolF."},
        "ar": {"description": "البطاطا لذيذة! هذا التحدي من إعداد Cyber0xWolF."},
    },
    "bootcamp-2025-61": {
        "en": {"name": "Free Palestine!"},
        "fr": {"name": "Liberté pour la Palestine !"},
        "ar": {"name": "الحرية لفلسطين!"},
    },
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
