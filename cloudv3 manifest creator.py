"""
From a given ChangeList number, this script will try to create a manifest for all platforms
- Input: ChangeList number (e.g. 3514827)
- Create a folder ./manifests if it doesn't exist
- Create a folder ./manifests/CL_{ChangeList} if it doesn't exist
- For each platform (Android_ASTC, Android_ATC, Android_DXT, Android_ETC1, Android_ETC2, Android_PVRTC, IOS)
  - Create a folder ./manifests/CL_{ChangeList}/{Platform} if it doesn't exist
  - Set paknumber to 0
  - In a loop until we reach an error threshold of 5:
    - Increment paknumber by 1
    - Try to download https://battlebreakers-live-cdn.ol.epicgames.com/WorldExplorersLive/CL_{Changelist}/{Platform}/WorldExplorers_pakchunk{PakNumber}CL_{ChangeList}.manifest
    - If successful, save the manifest to ./manifests/CL_{ChangeList}/{Platform}/WorldExplorers_pakchunk{PakNumber}CL_{ChangeList}.manifest, set error threshold to 0
    - If unsuccessful, and increment error threshold by 1
    - If error threshold is 4, set paknumber to next paknumber set (>= 49 becomes 50, >= 99 becomes 100, >= 899 becomes 900, >= 999 becomes 1000)
    - If error threshold is 5, break the loop
  - If the folder ./manifests/CL_{ChangeList}/{Platform} is not empty:
    - Create a master manifest file
      - JSON format
      - "ClientVersion" : ChangeList number,
      - "BuildUrl" : "{ChangeList}/{Platform}",
      - List of all manifest files in the folder ./manifests/CL_{ChangeList}/{Platform}
        - "filename" : filename,
        - "uniqueFilename" : filename,
        - "length" : size in bytes,
        - "URL" : filename,
        - "hash" : sha1 hash of the file,
        - "hash256" : sha256 hash of the file
    - Save the master manifest file to ./manifests/CL_{ChangeList}/{Platform}.manifest
  - If the folder ./manifests/CL_{ChangeList}/{Platform} is empty:
    - Delete the folder ./manifests/CL_{ChangeList}/{Platform}
"""

import os
import json
import hashlib
import asyncio
import aiohttp

MAX_ERRORS: int = 15
MAX_ERROR: int = 5
MAX_RETRIES: int = 2
CHANGELIST: str = input("Enter the changelist number: ")
PLATFORMS: list[str] = ["Android_ASTC", "Android_ATC", "Android_DXT", "Android_ETC1", "Android_ETC2", "Android_PVRTC",
                        "IOS", "WindowsNoEditor"]
PENDING_CL: list[str] = ["3677158", "4076582"]


async def download_manifest(session: aiohttp.client.ClientSession, platform: str, paknumber: int,
                            changelist: str) -> bytes | None:
    """
    Downloads a manifest file
    :param session: The aiohttp session
    :param platform: The platform
    :param paknumber: The paknumber
    :param changelist: The changelist
    :return: The manifest file
    """
    # battlebreakers-productiondev-cdn.s3.amazonaws.com via dfu3c9cojym2w.cloudfront.net WorldExplorersDevLatest
    # battlebreakers-productionlive-cdn.s3.amazonaws.com via d1nwd9qr43mkip.cloudfront.net WorldExplorersLive
    async with session.get(
            f"https://battlebreakers-productionlive-cdn.s3.amazonaws.com/WorldExplorersLive/CL_{changelist}/{platform}"
            f"/WorldExplorers_pakchunk{paknumber}CL_{changelist}.manifest") as response:
        if response.status == 200:
            return await response.read()
        return None


async def download_manifests(session: aiohttp.client.ClientSession, platform: str, changelist: str) -> None:
    """
    Downloads all manifest files for a given platform
    :param session: The aiohttp session
    :param platform: The platform
    :param changelist: The changelist
    :return: None
    """
    print(f"Downloading manifests for {platform}")
    if not os.path.exists(f"manifests/CL_{changelist}/{platform}"):
        print(f"Creating folder manifests/CL_{changelist}/{platform}")
        os.makedirs(f"manifests/CL_{changelist}/{platform}")
    paknumber: int = 0
    errors: int = 0
    retries: int = 0
    while errors < MAX_ERRORS:
        paknumber += 1
        filename: str = f"WorldExplorers_pakchunk{paknumber}CL_{changelist}.manifest"
        if os.path.exists(f"manifests/CL_{changelist}/{platform}/{filename}"):
            # print(f"Skipping {filename} (already exists)")
            errors: int = 0
            retries: int = 0
            continue
        manifest: None = None
        while retries < MAX_RETRIES:
            manifest: bytes = await download_manifest(session, platform, paknumber, changelist)
            if manifest is not None:
                break
            # print(f"Retrying {filename} ({retries + 1}/{MAX_RETRIES})")
            retries += 1
        if manifest is not None:
            print(f"Writing {filename}")
            with open(f"manifests/CL_{changelist}/{platform}/{filename}", "wb") as file:
                file.write(manifest)
            errors: int = 0
            retries: int = 0
        else:
            # This is messy, but basically
            # we have paknumbers in sets of 1-~15, sometimes 50-~60, 100-~120, 900-~940, 1000-~1400
            # This is specific to Battle Breakers, and each of these chunks do have a purpose (e.g. 1000+ for heroes)
            if errors >= MAX_ERROR:
                if paknumber < 49:
                    paknumber: int = 49
                    errors += 1
                    retries: int = 0
                    continue
                elif paknumber < 99:
                    paknumber: int = 99
                    errors += 1
                    retries: int = 0
                    continue
                elif paknumber < 899:
                    paknumber: int = 899
                    errors += 1
                    retries: int = 0
                    continue
                elif paknumber < 999:
                    paknumber: int = 999
                    errors += 1
                    retries: int = 0
                    continue
                else:
                    errors += 1
                    retries: int = 0
                    continue
            else:
                errors += 1
                retries: int = 0
                print(f"Trying paknumber {paknumber}")
                continue
    if len(os.listdir(f"manifests/CL_{changelist}/{platform}")) == 0:
        os.rmdir(f"manifests/CL_{changelist}/{platform}")
        print(f"Didn't download anything for CL_{changelist}/{platform}")
    else:
        print(f"Creating master manifest for {platform}")
        master_manifest: dict[str, int | str | list[dict[str, str | int]]] = {
            "ClientVersion": int(changelist),
            "BuildUrl": f"CL_{changelist}/{platform}",
            "files": []
        }
        for filename in os.listdir(f"manifests/CL_{changelist}/{platform}"):
            with open(f"manifests/CL_{changelist}/{platform}/{filename}", "rb") as file:
                data: bytes = file.read()
            master_manifest["files"].append({
                "filename": filename,
                "uniqueFilename": filename,
                "length": len(data),
                "URL": filename,
                "hash": hashlib.sha1(data).hexdigest().upper(),
                "hash256": hashlib.sha256(data).hexdigest().upper()
            })
        with open(f"manifests/CL_{changelist}/{platform}.manifest", "w") as file:
            json.dump(master_manifest, file, indent=4)
        print(f"Done creating master manifest for {platform}, found {len(master_manifest['files'])} files")


async def main() -> None:
    """
    The main function
    :return: None
    """
    if CHANGELIST == "":
        print("No changelist provided, exiting")
        return
    if CHANGELIST == "pending":
        for changelist in PENDING_CL:
            print(f"Downloading manifests for CL_{changelist}")
            if not os.path.exists("manifests"):
                os.makedirs("manifests")
            if not os.path.exists(f"manifests/CL_{changelist}"):
                os.makedirs(f"manifests/CL_{changelist}")
            async with aiohttp.ClientSession() as session:
                await asyncio.gather(*[download_manifests(session, platform, changelist) for platform in PLATFORMS])
            print(f"Done downloading manifests for CL_{changelist}")
        return
    if not os.path.exists("manifests"):
        os.makedirs("manifests")
    if not os.path.exists(f"manifests/CL_{CHANGELIST}"):
        os.makedirs(f"manifests/CL_{CHANGELIST}")
    async with aiohttp.ClientSession() as session:
        await asyncio.gather(*[download_manifests(session, platform, CHANGELIST) for platform in PLATFORMS])


if __name__ == "__main__":
    asyncio.run(main())
