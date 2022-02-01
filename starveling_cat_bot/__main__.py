import asyncio
import signal
import logging
import sys
import os
import json
import argparse

from starveling_cat_bot.bot import Bot


_log = logging.getLogger("starveling_cat_bot")

DISCORD_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")


async def main(config_path: str):
    _log.info("using config file %s", config_path)
    with open(config_path, "r") as stream:
        config = json.load(stream)

    # Пока в него не попали секреты можно напечатать
    _log.info("loaded config: %s", config)
    config.update({
        "github_secret": None,
        "discord_secret": DISCORD_TOKEN
    })

    handler = Bot(config)
    await handler.setup()
    await handler.start()
    _log.info("Everything started")

    stop_event = asyncio.Event()
    stop_event.clear()

    def on_signal(signum: int):
        _log.info("got signal %s. Stopping.", signal.strsignal(signum))
        stop_event.set()

    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT,)
    loop = asyncio.get_running_loop()
    for s in signals:
        _log.info("installing signal handler %s", signal.strsignal(s))
        loop.add_signal_handler(s, lambda s=s: on_signal(s))

    await stop_event.wait()
    stop_event.clear()

    # Выключаемся
    _log.info("shutting down")
    await handler.shutdown()

    tasks = [t for t in asyncio.all_tasks() if t is not
             asyncio.current_task()]

    tasks_count = 0
    for task in tasks:
        task.cancel()
        tasks_count +=1

    _log.info(f"Cancelling {tasks_count} outstanding tasks")
    await asyncio.gather(*tasks, return_exceptions=True)
    _log.info("Stopped")


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Starveling Cat Bot", add_help=True)
    parser.add_argument("-c", "--config", required=True, nargs='?', dest='config', type=str)
    argv = sys.argv[1:]
    args = parser.parse_args(argv)

    log_format = "%(asctime)s %(name)s %(levelname)s %(message)s"
    logging.basicConfig(stream=sys.stderr, level=logging.INFO, format=log_format)
    asyncio.run(main(args.config))
