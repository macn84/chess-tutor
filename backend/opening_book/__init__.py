"""Opening book package.

Re-exports the two public functions from ``loader`` so callers can write::

    import opening_book
    entry = opening_book.lookup(fen)
"""

from .loader import lookup, get_all_entries

__all__ = ["lookup", "get_all_entries"]
