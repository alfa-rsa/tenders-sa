"""Main CLI entry point for tenders-sa."""

import os
import sys

import click

from . import search as _search
from . import contacts as _contacts
from . import track as _track
from . import history as _history
from . import watch as _watch
from . import setup as _setup


@click.group()
@click.version_option(version="0.1.0a")
def main():
    """tenders-sa — SA Government Tender Intelligence."""
    pass


# Wire up subcommands
main.add_command(_search.search)
main.add_command(_search.new)
main.add_command(_history.history)
main.add_command(_history.winners)
main.add_command(_contacts.contacts)
main.add_command(_track.track)
main.add_command(_track.pipeline)
main.add_command(_watch.watch)
main.add_command(_watch.watch_list)
main.add_command(_setup.setup)
main.add_command(_setup.stats)


if __name__ == "__main__":
    main()
