"""
Loop through a directory of manifests, download the chunks, and save them to a directory
e.g. https://battlebreakers-productionlive-cdn.s3.amazonaws.com/WorldExplorersLive/CL_3514827/Android_ATC/ChunksV3/79/7D8628F07C7F4797_1865E37A4FD1B9CD35AA12BFEFBF1502.chunk
https://battlebreakers-productionlive-cdn.s3.amazonaws.com/WorldExplorersLive/ - base
CL_3514827/ - BuildVersionString
Android_ATC/ - Derive from FileManifestList[0]Filename: get between - and . pakchunk1-Android_ATC.pak
ChunksV3/ - dir
79/ - DataGroupList[Guid] (remove leading 0s)
7D8628F07C7F4797 - ChunkHashList[Guid]
_ - separator
1865E37A4FD1B9CD35AA12BFEFBF1502 - Guid
.chunk - extension
"""

import asyncio
import aiohttp
import orjson
import os
import zlib
import time


def blob2hex(blob: str, reverse: bool = True, returnInt: bool = True) -> int | str:
    """
    Convert a blob to hex
    :param blob: The blob to convert
    :param reverse: True to reverse the blob
    :param returnInt: True to return an int
    :return: The hex string or int
    """
    sets: list = [blob[i:i + 3] for i in range(0, len(blob), 3)]
    if reverse:
        sets.reverse()
    out: str = ""
    for val in sets:
        out += "{:02X}".format(int(val))
    if returnInt:
        return int(out, 16)
    else:
        return out


async def decompress(data: bytes) -> bytes:
    """
    Decompress a chunk
    :param data: The raw response chunk data
    :return: The decompressed chunk data
    """
    offset: int = data[8]
    data: bytes = data[8:] if offset == 120 else data[offset:]
    try:
        return await asyncio.get_event_loop().run_in_executor(None, zlib.decompress, data)
    except zlib.error:
        return data


async def download_chunk(session: aiohttp.client.ClientSession, url: str, save_chunks: bool = True) -> bytes | None:
    """
    Download a chunk file
    :param session: The aiohttp session
    :param url: The url to download from
    :param save_chunks: True to save the chunks to disk
    :return: None
    """
    # Extract the file name from the URL
    file_name: str = url.split("/")[-1]

    # Extract the directory path from the URL
    dir_path: str = "/".join(url.split("/")[4:-1])
    if save_chunks:
        # Create the directory if it doesn't exist
        os.makedirs(f"chunks/{dir_path}", exist_ok=True)

    async with session.get(url) as response:
        if response.status == 200:
            if save_chunks:
                # if the files are identical, skip writing
                if os.path.exists(f"chunks/{dir_path}/{file_name}"):
                    if os.path.getsize(f"chunks/{dir_path}/{file_name}") == int(response.headers["Content-Length"]):
                        return await decompress(await response.read())
                with open(f"chunks/{dir_path}/{file_name}", "wb") as file:
                    file.write(await response.read())
                    file.close()
            # print(f"Downloaded {file_name}")
            return await decompress(await response.read())
        else:
            print(f"Failed to download {url} with status code {response.status}")
            await asyncio.sleep(1)
            async with session.get(url) as response:
                if response.status == 200:
                    if save_chunks:
                        # if the files are identical, skip writing
                        if os.path.exists(f"chunks/{dir_path}/{file_name}"):
                            if os.path.getsize(f"chunks/{dir_path}/{file_name}") == int(
                                    response.headers["Content-Length"]):
                                return await decompress(await response.read())
                        with open(f"chunks/{dir_path}/{file_name}", "wb") as file:
                            file.write(await response.read())
                            file.close()
                    # print(f"Downloaded {file_name}")
                    return await decompress(await response.read())
                else:
                    print(f"Failed to download {url} with status code {response.status}")
                    return None


async def main(platform: str = "Android_ASTC", build: str = "CL_3302067", save_chunks: bool = True,
               pakchunk: int = 1) -> None:
    """
    The main function
    :param platform: The platform to download chunks for
    :param build: The build to download chunks for
    :param save_chunks: True to save the chunks to disk
    :param pakchunk: The pakchunk to download chunks for
    :return: None
    """
    # Create the manifests directory if it doesn't exist
    if not os.path.exists("manifests"):
        os.makedirs("manifests")
    if not os.path.exists("chunks"):
        os.makedirs("chunks")

    # Create the aiohttp session
    async with aiohttp.ClientSession() as session:
        # loop through each manifest
        for file in os.listdir(f"manifests/{build}/{platform}"):
            if file.endswith(f"WorldExplorers_pakchunk{pakchunk}{build}.manifest"):
                # Read the manifest file
                # print(f"Reading {file}")
                with open(f"manifests/{build}/{platform}/{file}", "r", encoding='utf-8') as file:
                    manifest: dict = orjson.loads(file.read())

                # Create a list of chunk download coroutines
                download_tasks: list = []
                for filemanifest in manifest["FileManifestList"]:
                    for filechunk in filemanifest["FileChunkParts"]:
                        # Download the chunk
                        url = ("https://battlebreakers-productionlive-cdn.s3.amazonaws.com/WorldExplorersLive/{}/{"
                               "}/ChunksV3/{:02d}/{:016X}_{}.chunk").format(
                            manifest['BuildVersionString'],
                            filemanifest['Filename'].split('-')[1].split('.')[0],
                            int(manifest['DataGroupList'][filechunk['Guid']]),
                            blob2hex(manifest['ChunkHashList'][filechunk['Guid']]),
                            filechunk['Guid']
                        )
                        # if the file already exists, skip downloading
                        # Extract the directory path from the URL
                        dir_path = "/".join(url.split("/")[4:-1])
                        # if os.path.exists(f"chunks/{dir_path}/{url.split('/')[-1]}"):
                        #     continue
                        download_tasks.append(download_chunk(session, url, save_chunks))

                # Wait for all the chunks to download
                chunk_data_list = await asyncio.gather(*download_tasks)

                # Loop through each chunk and update the pak chunk
                pak_chunk: bytearray = bytearray()
                for filemanifest in manifest["FileManifestList"]:
                    for filechunk in filemanifest["FileChunkParts"]:
                        try:
                            # Get the chunk data and update the pak chunk
                            filechunk["Offset"]: int = blob2hex(filechunk["Offset"])
                            filechunk["Size"]: int = blob2hex(filechunk["Size"])
                            chunk_data: bytes = chunk_data_list.pop(0)[
                                                filechunk["Offset"]:filechunk["Offset"] + filechunk["Size"]]
                            filechunk["FileStart"] = 0
                            if filechunk != filemanifest["FileChunkParts"][0]:
                                filechunk["FileStart"] = \
                                    filemanifest["FileChunkParts"][filemanifest["FileChunkParts"].index(filechunk) - 1][
                                        "FileStart"] + \
                                    filemanifest["FileChunkParts"][filemanifest["FileChunkParts"].index(filechunk) - 1][
                                        "Size"]
                            pak_chunk: bytes = pak_chunk[:filechunk["FileStart"]] + chunk_data + pak_chunk[
                                                                                                 filechunk[
                                                                                                     "FileStart"] +
                                                                                                 filechunk["Size"]:]
                        except:
                            print(f"Failed to update {filemanifest['Filename']}")
                            continue
                    try:
                        os.makedirs(
                            f"chunks/{build}/{platform}/Chunks/Installed/base{filemanifest['Filename'].split('pakchunk')[1].split('-')[0]}",
                            exist_ok=True)
                        with open(
                            f"chunks/{build}/{platform}/Chunks/Installed/base{filemanifest['Filename'].split('pakchunk')[1].split('-')[0]}/{filemanifest['Filename']}",
                            "wb") as file:
                            file.write(pak_chunk)
                            print(f"Writing {filemanifest['Filename']}")
                            file.close()
                    except:
                        print(f"Failed to write {filemanifest['Filename']}")
                        continue

        # Close the aiohttp session
        await session.close()


if __name__ == "__main__":
    # Start the timer
    start_time: float = time.time()

    # build = "CL_3302067"
    platform: str = "Android_ETC1"

    builds: list[str] = ["CL_3719898", "CL_3842684", "CL_3891207"]
    # builds = ["CL_3693860"]

    for build in builds:
        # Run the main function
        loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
        for file in os.listdir(f"manifests/{build}/{platform}"):
            if file.endswith(f".manifest"):
                loop.run_until_complete(main(platform, build, True, int(file.split("pakchunk")[1].split("CL")[0])))
        # loop.run_until_complete(main())

        # Print the time it took to run
        print("--- %s seconds ---" % (time.time() - start_time) + ".. for build " + build)
