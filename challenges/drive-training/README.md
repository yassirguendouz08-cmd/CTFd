# Supplied introductory training

Four distinct exercises from the supplied Drive archive are imported as hidden,
standard CTFd challenges. Each is worth 100 points with unlimited attempts and
three free hints. Names, descriptions and hints follow English, French and Arabic
platform preferences. Administrators can review them from the normal board;
regular players cannot access them or download their evidence.

| Source folder | English title | Category |
| --- | --- | --- |
| `hello_chalenge` | Training 01 — Hello, hexadecimal | Crypto |
| `linux_easyyy-lab` | Training 02 — The invisible file | Linux |
| `linux_lab-easy` | Training 03 — The archive maze | Linux |
| `linux_lab_meudiem` | Training 04 — Needle in the Log | Linux |

The supplied `linux_lab.rar` and `linux_lab_2.zip` are alternative versions with
answers already used by the selected maze and log exercises. They are omitted
following the organizer's choice to import four distinct challenges.

The original evidence and flags are preserved. The introductory hexadecimal
answer accepts either letter case. Solution files are excluded from all player
attachments. File trees are repackaged into portable `.tar.gz` archives while
preserving hidden files, spaces in paths and each original file's bytes.

Build on the organizer's machine, keeping output outside the repository:

```sh
python challenges/drive-training/build.py /private/source.zip --output /private/drive-training-pack
python scripts/import-drive-training.py /private/drive-training-pack
```

The private manifest contains flags and attachment hashes: never commit it or
the generated attachments. The importer verifies hashes and reviewed catalogue
text, and reuses its `drive-training:<slug>` marker tags on repeated imports.
It refuses to overwrite edited or published challenges, modified hints or
attachments. It never changes unrelated challenges or score records.

The public translation catalogue is
`CTFd/utils/challenge_localization/drive-training.json`. Update its French source
and translated fields together when changing challenge text. Administrative
editing APIs keep their original source content.
