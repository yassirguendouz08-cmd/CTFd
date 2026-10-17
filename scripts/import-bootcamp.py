"""Import a private first-steps pack as hidden challenges; never publishes them."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def import_pack(app, directory):
    from werkzeug.datastructures import FileStorage
    from CTFd.cache import clear_challenges
    from CTFd.models import ChallengeFiles, Challenges, Flags, Hints, Tags, db
    from CTFd.utils.uploads import get_uploader

    directory = Path(directory).resolve()
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    entries = manifest['challenges']
    if manifest.get('pack') != 'bootcamp-first-steps-v1' or len(entries) != 8:
        raise ValueError('Expected exactly 8 first-steps challenges.')
    if len({item['name'] for item in entries}) != 8 or len({item['slug'] for item in entries}) != 8:
        raise ValueError('Duplicate challenge name or slug.')
    for category in ('Web', 'Crypto', 'Linux', 'OSINT'):
        if sum(item['category'] == category for item in entries) != 2:
            raise ValueError('Expected two challenges in each category.')
    for item in entries:
        if len(item['hints']) != 3 or not item['files']:
            raise ValueError('Every challenge needs three hints and an attachment.')
        for filename in item['files']:
            path = (directory / filename).resolve()
            if directory not in path.parents or not path.is_file():
                raise ValueError('Missing attachment or path outside pack directory.')

    report = []
    uploaded = []
    with app.app_context():
        uploader = get_uploader()
        try:
            for position, item in enumerate(entries, start=1):
                marker = 'bootcamp-first-steps:' + item['slug']
                challenge = Challenges.query.filter_by(name=item['name']).first()
                if challenge:
                    if not Tags.query.filter_by(challenge_id=challenge.id, value=marker).first():
                        raise ValueError('Challenge name already exists outside this pack; refusing overwrite.')
                    flag = Flags.query.filter_by(challenge_id=challenge.id).one()
                    if flag.content != item['flag'] or challenge.state != 'hidden':
                        raise ValueError('Existing pack differs or has been published; refusing overwrite.')
                    if Hints.query.filter_by(challenge_id=challenge.id).count() != 3:
                        raise ValueError('Existing pack has modified hints; refusing overwrite.')
                    saved = ChallengeFiles.query.filter_by(challenge_id=challenge.id).all()
                    expected = {Path(name).name: hashlib.sha1((directory / name).read_bytes()).hexdigest() for name in item['files']}
                    if {Path(f.location).name: f.sha1sum for f in saved} != expected:
                        raise ValueError('Existing pack attachments differ; refusing overwrite.')
                else:
                    challenge = Challenges(name=item['name'], category=item['category'],
                                           description=item['description'], value=item['value'],
                                           type='standard', state='hidden', max_attempts=0,
                                           position=position, logic='any')
                    db.session.add(challenge)
                    db.session.flush()
                    db.session.add(Flags(challenge_id=challenge.id, type='static',
                                         content=item['flag'], data=item['flag_data']))
                    for index, hint in enumerate(item['hints'], start=1):
                        db.session.add(Hints(challenge_id=challenge.id, title=f'Indice {index}', content=hint, cost=0))
                    for tag in ('Bootcamp', 'Débutant', marker):
                        db.session.add(Tags(challenge_id=challenge.id, value=tag))
                    for filename in item['files']:
                        path = directory / filename
                        with path.open('rb') as stream:
                            location = uploader.upload(FileStorage(stream=stream, filename=path.name), path.name)
                        uploaded.append(location)
                        db.session.add(ChallengeFiles(challenge_id=challenge.id, location=location,
                                                      sha1sum=hashlib.sha1(path.read_bytes()).hexdigest()))
                challenge.attribution = 'Soussi' if item['category'] == 'Linux' else 'Yass1ir'
                report.append({'id': challenge.id, 'name': challenge.name,
                               'category': challenge.category, 'state': challenge.state,
                               'admin_url': f'/admin/challenges/{challenge.id}'})
            db.session.commit()
        except Exception:
            db.session.rollback()
            for location in uploaded:
                uploader.delete(location)
            raise
        clear_challenges()
    (directory / 'import-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path, help='Private directory containing manifest.json and player attachments.')
    args = parser.parse_args()
    from CTFd import create_app
    import_pack(create_app(), args.directory)
