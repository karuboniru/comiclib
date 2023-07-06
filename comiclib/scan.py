import importlib
import sys
import copy
import hashlib
import asyncio
from pathlib import Path
from pprint import pprint

from .database import engine, Base, Archive, Tag, Category
from sqlalchemy import select
from sqlalchemy.orm import Session
import watchfiles

from .config import settings

Base.metadata.create_all(bind=engine)

from . import scaner

sys.path.append('.')
scaners = [(importlib.import_module('.scaner.'+name, __package__).Scaner(), name) for name in scaner.__all__] + \
          [(importlib.import_module(p.stem).Scaner(), p.stem) for p in Path('.').glob('*.py')]
scaners.sort(key=lambda t:t[1])
print("Loaded scaners:", [scaner[1] for scaner in scaners])


def scan(paths):
    with Session(engine) as db:
        for p in paths:  # TODO: https://github.com/python/cpython/issues/77609
            p = Path(p).resolve().relative_to(Path(settings.content).resolve())
            if p.is_relative_to('thumb'):
                continue
            old_a = db.scalar(select(Archive).where(
                Archive.path == p.as_posix()))
            if old_a is None:
                a = Archive(path=p.as_posix())
                archive_id = hashlib.blake2b(
                    p.as_posix().encode(), digest_size=10).hexdigest()
            elif settings.skip_exits:
                continue
            else:
                a = old_a
                archive_id = old_a.id
            metadata = {"title": a.title, "subtitle": a.subtitle, "source": a.source, "pagecount": a.pagecount, "tags": set(
                t.tag for t in a.tags if not t.tag.startswith("date_added:")), "categories": set(c.name for c in a.categories)}
            real_path = Path(settings.content) / p
            prev_scaners = []
            for scaner, name in scaners:
                prev_metadata = copy.deepcopy(metadata)
                if scaner.scan(real_path, archive_id, metadata, prev_scaners):
                    prev_scaners.append(name)
                else:
                    metadata = prev_metadata
            if not prev_scaners:
                continue
            if not any(tag.startswith("date_added:") for tag in metadata["tags"]):
                metadata["tags"].add(f"date_added:{int(real_path.stat().st_mtime)}")
            pprint(metadata)
            a.title = metadata["title"]
            a.subtitle = metadata["subtitle"]
            a.source = metadata["source"]
            a.pagecount = metadata["pagecount"]
            a.thumb = metadata["thumb"]
            for tag in filter(lambda t: not t.tag in metadata["tags"], a.tags):
                a.tags.remove(tag)
            for tag in metadata["tags"] - set(t.tag for t in a.tags):
                a.tags.append(Tag(archive_id=archive_id, tag=tag))
            for category in filter(lambda c: not c.name in metadata["categories"], a.categories):
                a.categories.remove(category)
            for category in metadata["categories"] - set(c.name for c in a.categories):
                if (c := db.scalar(select(Category).where(Category.name == category))) is None:
                    c = Category(name=category, pinned=0)
                    db.add(c)
                a.categories.append(c)
            if old_a is None:
                a.id = archive_id
                db.add(a)
            db.commit()


async def watch():
    file_sizes = {}
    async for changes in watchfiles.awatch(settings.content, watch_filter=lambda change, _: change == watchfiles.Change.added, step=1000):
        for _, fname in changes:
            while file_sizes.get(fname, -1) != (fsize := Path(fname).stat().st_size):
                file_sizes[fname] = fsize
                await asyncio.sleep(1)
        asyncio.to_thread(scan, map(lambda change: change[1], changes))


def scannow():
    scan(Path(settings.content).rglob('*'))
