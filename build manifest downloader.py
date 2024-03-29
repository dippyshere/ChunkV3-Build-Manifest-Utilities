"""
https://github.com/dippyshere/build-manifest-downloader
Using a TXT file thats formatted like this:

$BUILD_ID = 1.80.1696-r10121395
$NUM_ENTRIES = 378
pakchunk1_pak1.pak	1179	SHA1:3c520662e82bd5c159e9894d89556f44620d2fc6	1	Windows/pakchunk1_pak1.pak
pakchunk2_pak1.pak	78360223	SHA1:e6a3cb9883216f3a2ccd7bdf10413950d889f4ac	2	Windows/pakchunk2_pak1.pak

Downloads each file from a url like this: https://battlebreakers-live-cdn.ol.epicgames.com/1.80.1696-r10121395/Windows/pakchunk1_pak1.pak
"""

import os
import re
import hashlib
import aiohttp
import aiofiles
import asyncio
import logging
import argparse
import time

from shutil import copyfileobj


def get_args() -> argparse.Namespace:
    """
    Gets the command line arguments.
    :return: argparse.Namespace - the command line arguments
    """
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description='Download files from Build Manifests.')
    parser.add_argument('file', type=str, help='Text file containing file info.')
    parser.add_argument('-d', '--dir', type=str, help='Directory to save files to.')
    parser.add_argument('-b', '--base', type=str, default='https://battlebreakers-live-cdn.ol.epicgames.com',
                        help='Base URL to download from.')
    parser.add_argument('-v', '--verbose', action='store_true', default=True, help='Enable verbose logging.')
    parser.add_argument('-t', '--threads', type=int, default=3, help='Number of threads to use.')
    parser.add_argument('-s', '--skip', action='store_true', default=True, help='Skip files that already exist.')
    parser.add_argument('-c', '--check', action='store_true', default=True, help='Check files that already exist.')
    parser.add_argument('-r', '--retries', type=int, default=2, help='Number of times to retry downloads.')
    parser.add_argument('-w', '--wait', type=int, default=3, help='Wait time between retries.')
    return parser.parse_args()


async def get_file_info(path: str) -> tuple[str, int, list]:
    """
    Reads and parses the build manifest file.
    :param path: str - the path to the file
    :return: str, int, list - the build id, number of entries, and entries
    """
    async with aiofiles.open(path, 'r') as f:
        lines: list[str] = await f.readlines()
    build_id: str = lines[0].split('=')[1].strip()
    num_entries: int = int(lines[1].split('=')[1].strip())
    entries: list = []
    for line in lines[2:]:
        entries.append(re.split(r'\t+', line.strip()))
    return build_id, num_entries, entries


async def download(session: aiohttp.client.ClientSession, url, path) -> None:
    """
    Downloads a file and saves to disk.
    :param session: The aiohttp session
    :param url: The url to download from
    :param path: The path to save the file to
    :return: None
    """
    async with session.get(url) as response:
        response.raise_for_status()
        async with aiofiles.open(path, 'wb') as f:
            await f.write(await response.read())


async def download_file(url: str, path: str, retries: int, wait: int | float, verbose: bool, build_id: str, base: str,
                        session: aiohttp.client.ClientSession) -> None:
    """
    Constructs the url and downloads the file to disk.
    :param url: The path to download from
    :param path: The path to download from
    :param retries: How many times to retry the download
    :param wait: How long to wait between retries
    :param verbose: Whether to log verbose messages
    :param build_id: The build id for the url
    :param base: The base url to download from
    :param session: The aiohttp session
    :return: None
    """
    url: str = f'{base}/{build_id}/{url}'
    if os.path.exists(path):
        os.remove(path)
    logging.info('Downloading %s to %s', url, path)
    for i in range(retries):
        try:
            await download(session, url, path)
            logging.info('Downloaded %s successfully :D', path)
            break
        except Exception as e:
            if i == retries - 1:
                raise e
            if verbose:
                logging.warning('Failed to download %s (%s), retrying in %d seconds', url, e, wait)
            time.sleep(wait)


async def check_file(path: str, sha1: str) -> bool:
    """
    Checks if a file exists and has the correct sha1 hash.
    :param path: The path to the file
    :param sha1: The sha1 hash to check against
    :return: bool - whether the file exists and has the correct sha1 hash
    """
    if not os.path.exists(path):
        return False
    with open(path, 'rb') as f:
        data: bytes = f.read()
    return hashlib.sha1(data).hexdigest() == sha1


async def main() -> None:
    """
    Main function.
    :return: None
    """
    args: argparse.Namespace = get_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)
    build_id, num_entries, entries = await get_file_info(args.file)
    if args.dir:
        os.chdir(args.dir)
    else:
        os.chdir("D:/Battle Breakers/")
    if not os.path.exists(build_id):
        os.mkdir(build_id)
    os.chdir(build_id)
    if not os.path.exists(entries[0][4].split('/')[0]):
        os.mkdir(entries[0][4].split('/')[0])
    session: aiohttp.client.ClientSession = aiohttp.ClientSession()
    tasks: list = []
    for entry in entries:
        path: str = entry[4]
        if args.skip and os.path.exists(path):
            continue
        if args.check and await check_file(path, entry[2].split(':')[1]):
            continue
        tasks.append(asyncio.create_task(
            download_file(path, path, args.retries, args.wait, args.verbose, build_id, args.base, session))
        )
    await asyncio.gather(*tasks)
    await session.close()


if __name__ == '__main__':
    asyncio.run(main())
    logging.info('All files downloaded successfully :D')
