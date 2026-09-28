"""Build mystery.db, a small database to explore with the dataset library.

Usage: python3 build_mystery.py [database_file] [--replace]

The builder uses Python's unicodedata and zoneinfo modules. The tzdata package
supplies the time zone database where the operating system does not. Counts
vary with the Python version. It refuses to overwrite an existing file unless
--replace is given.

If you are using this as the "unknown database" exercise, run this script
once and then do not read it until you have explored the file.
"""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
import unicodedata
from zoneinfo import ZoneInfo, available_timezones

CATEGORIES = {
    "Lu": ("Uppercase letter", "Letter"),
    "Ll": ("Lowercase letter", "Letter"),
    "Lt": ("Titlecase letter", "Letter"),
    "Lm": ("Modifier letter", "Letter"),
    "Lo": ("Other letter", "Letter"),
    "Mn": ("Nonspacing mark", "Mark"),
    "Mc": ("Spacing mark", "Mark"),
    "Me": ("Enclosing mark", "Mark"),
    "Nd": ("Decimal digit", "Number"),
    "Nl": ("Letter number", "Number"),
    "No": ("Other number", "Number"),
    "Pc": ("Connector punctuation", "Punctuation"),
    "Pd": ("Dash punctuation", "Punctuation"),
    "Ps": ("Open punctuation", "Punctuation"),
    "Pe": ("Close punctuation", "Punctuation"),
    "Pi": ("Initial quote", "Punctuation"),
    "Pf": ("Final quote", "Punctuation"),
    "Po": ("Other punctuation", "Punctuation"),
    "Sm": ("Math symbol", "Symbol"),
    "Sc": ("Currency symbol", "Symbol"),
    "Sk": ("Modifier symbol", "Symbol"),
    "So": ("Other symbol", "Symbol"),
    "Zs": ("Space separator", "Separator"),
    "Zl": ("Line separator", "Separator"),
    "Zp": ("Paragraph separator", "Separator"),
    "Cc": ("Control", "Other"),
    "Cf": ("Format", "Other"),
    "Cs": ("Surrogate", "Other"),
    "Co": ("Private use", "Other"),
    "Cn": ("Unassigned", "Other"),
}

SCHEMA = """
create table category (
    code text primary key,
    description text not null,
    major_class text not null
);

create table character (
    codepoint integer primary key,
    symbol text not null,
    name text not null,
    category text not null references category(code),
    script text not null,
    width text not null,
    numeric_value real
);

create table timezone (
    name text primary key,
    region text not null,
    city text not null,
    january_offset_minutes integer not null,
    july_offset_minutes integer not null,
    uses_dst integer not null
);

create index idx_character_category on character(category);
create index idx_character_script on character(script);

create view script_summary as
    select script,
           count(*) as characters,
           min(codepoint) as first_codepoint,
           max(codepoint) as last_codepoint
    from character
    group by script;

create view numeric_character as
    select codepoint, symbol, name, numeric_value
    from character
    where numeric_value is not null;
"""

# Basic Multilingual Plane, plus the main emoji blocks.
CODEPOINT_RANGES = [range(0x20, 0x10000), range(0x1F300, 0x1FB00)]


def character_rows():
    for codepoints in CODEPOINT_RANGES:
        for codepoint in codepoints:
            symbol = chr(codepoint)
            name = unicodedata.name(symbol, "")
            if not name:
                continue
            yield (
                codepoint,
                symbol,
                name,
                unicodedata.category(symbol),
                name.split(" ")[0],
                unicodedata.east_asian_width(symbol),
                unicodedata.numeric(symbol, None),
            )


def offset_minutes(zone, moment):
    return int(moment.astimezone(zone).utcoffset().total_seconds() // 60)


def timezone_rows():
    january = datetime(2026, 1, 15, 12, tzinfo=timezone.utc)
    july = datetime(2026, 7, 15, 12, tzinfo=timezone.utc)
    for name in sorted(available_timezones()):
        if "/" not in name or name.startswith(("Etc/", "posix/", "right/")):
            continue
        region, _, city = name.partition("/")
        zone = ZoneInfo(name)
        jan, jul = offset_minutes(zone, january), offset_minutes(zone, july)
        yield name, region, city.replace("_", " "), jan, jul, int(jan != jul)


def build(path):
    connection = sqlite3.connect(path)
    try:
        connection.executescript(SCHEMA)
        connection.executemany(
            "insert into category values (?, ?, ?)",
            [(code, *details) for code, details in CATEGORIES.items()],
        )
        connection.executemany(
            "insert into character values (?, ?, ?, ?, ?, ?, ?)", character_rows())
        connection.executemany(
            "insert into timezone values (?, ?, ?, ?, ?, ?)", timezone_rows())
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build the mystery database.")
    parser.add_argument("database_file", nargs="?", default="mystery.db")
    parser.add_argument("--replace", action="store_true",
                        help="replace the file if it already exists")
    args = parser.parse_args()
    target = Path(args.database_file)
    if target.exists():
        if not args.replace:
            raise SystemExit(f"{target} already exists. Use --replace to rebuild it.")
        os.remove(target)
    build(target)
    print(f"Built {target} ({target.stat().st_size // 1024} KB, Unicode {unicodedata.unidata_version}).")
