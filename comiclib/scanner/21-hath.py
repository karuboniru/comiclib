from pathlib import Path
import re


class Scanner:
    '''For archives downloaded via Hentai@Home'''
    
    def scan(self, path: Path, id: str, metadata: dict, prev_scanners: list[str]) -> bool:
        if path.is_dir() and (path / 'galleryinfo.txt').exists():
            print(f' -> hath.py get {path}')
            metadata["source"] = 'https://exhentai.org/g/' + re.search(r"\[(\d+)\]$", path.name)[1] + '/'
            information = (path / 'galleryinfo.txt').read_text().splitlines()
            _key, _, title = information[0].partition(':')
            assert _key == 'Title'
            metadata["title"] = title.lstrip()
            _key, _, tags = information[4].partition(':')
            assert _key == 'Tags'
            metadata["tags"] = set(tags.lstrip().split(', '))
            _key, _, date_posted = information[1].partition(':')
            assert _key == 'Upload Time'
            metadata["tags"].add(f"date_posted:{date_posted.lstrip().partition(' ')[0]}")
            metadata["pagecount"] = len(list(path.iterdir())) - 1
            return True
        else:
            return False