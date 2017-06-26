"""
Defines a set of helper methods for performing migrations
"""

import asyncio
import concurrent
import contextlib
import logging
import signal

from blazingdb.util import sig


def finalize_loop(loop):
    """ Waits for all pending tasks in the loop to complete """
    logging.getLogger(__name__).info("Waiting for pending tasks to complete")

    pending = asyncio.Task.all_tasks(loop)
    gathered = asyncio.gather(*pending, loop=loop, return_exceptions=True)

    try:
        loop.run_until_complete(gathered)
    except:  # pylint: disable=bare-except
        logging.getLogger(__name__).warning("Ignoring pending tasks")

def shutdown_loop(loop):
    """ Shuts down the given loop, cancelling and completing all tasks """
    logging.getLogger(__name__).info("Shutting down event loop")
    shutdown_gens = loop.shutdown_asyncgens()

    try:
        loop.run_until_complete(shutdown_gens)
    except:  # pylint: disable=bare-except
        logging.getLogger(__name__).warning("Skipping shutdown of async generators")

    loop.close()

def migrate(migrator_factory):
    """ Performs a migration using the Migrator returned from the given factory function """
    loop = asyncio.new_event_loop()
    migrator = migrator_factory(loop)

    migration_task = asyncio.ensure_future(migrator.migrate(), loop=loop)

    def _interrupt(sig_num, stack):  # pylint: disable=unused-argument
        nonlocal migration_task

        logging.getLogger(__name__).info("Cancelling import...")
        migration_task.cancel()

    with sig.SignalContext(signal.SIGINT, _interrupt):
        with contextlib.suppress(concurrent.futures.CancelledError):
            loop.run_until_complete(migration_task)

    loop.run_until_complete(migrator.shutdown())

    finalize_loop(loop)
    migrator.close()

    shutdown_loop(loop)

def main():
    raise NotImplementedError("'main' method has not been implemented yet")
