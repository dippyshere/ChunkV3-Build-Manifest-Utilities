"""
Loop through a master.manifest json file, download each chunk's manifest, save to /manifests/file_name.manifest
e.g. https://battlebreakers-live-cdn.ol.epicgames.com/WorldExplorersLive/CL_3514827/Android_ATC/WorldExplorers_pakchunk1000CL_3514827.manifest
"""

import asyncio
import aiohttp
import orjson
import os
import time


async def download_manifest(session: aiohttp.client.ClientSession, url: str, file_name: str) -> None:
    """
    Download a manifest file
    :param session: The aiohttp session
    :param url: The url to download from
    :param file_name: The file name to save to
    :return: None
    """
    async with session.get(url) as response:
        if response.status == 200:
            with open(f"manifests/{file_name}", "wb") as file:
                file.write(await response.read())
                file.close()
            print(f"Downloaded {file_name}")
        else:
            print(f"Failed to download {file_name} with status code {response.status}")


async def main() -> None:
    """
    The main function
    :return: None
    """
    # Create the manifests directory if it doesn't exist
    if not os.path.exists("manifests"):
        os.makedirs("manifests")

    # Create the aiohttp session
    async with aiohttp.ClientSession() as session:
        # Read the master.manifest file
        with open("master.manifest", "r", encoding='utf-8') as file:
            master_manifest: dict = orjson.loads(file.read())

        # Loop through each chunk
        for chunk in master_manifest["files"]:
            # Download the chunk's manifest
            url: str = f"https://battlebreakers-live-cdn.ol.epicgames.com/WorldExplorersLive/{master_manifest['BuildUrl']}/{chunk['filename']}"
            await download_manifest(session, url, chunk["filename"])

        # Close the aiohttp session
        await session.close()


if __name__ == "__main__":
    # Start the timer
    start_time: float = time.time()

    # Run the main function
    loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
    loop.run_until_complete(main())

    # Print the time it took to run
    print("--- %s seconds ---" % (time.time() - start_time))