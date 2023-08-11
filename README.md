# Build Manifest / ChunkV3 Utilties

This repository is a collection of various python scripts for working with [Build Manifests](https://docs.unrealengine.com/4.27/en-US/SharingAndReleasing/Patching/ChunkDownloader/) 
and the older [ChunkV3](https://docs.unrealengine.com/4.26/en-US/API/Plugins/HTTPChunkInstaller/) systems.

These scripts are written primarily for Battle Breakers[^1], and are not of much practical use anymore[^2]

[^1]: Some things (like paths, methods, etc) may be hardcoded to work specifically for Battle Breakers, and **will** require modification for other games and services.

[^2]: After ~12/05/2023, ChunkV3 chunks for older Fortnite Builds were removed. Battle Breakers ChunkV3 chunks are only partially available[^3]

[^3]: You can find all known and available ChunkV3 (and Build Manifest) manifests for Battle Breakers [here](https://github.com/dippyshere/battle-breakers-private-server/tree/main/res/wex/api/game/v2/manifests).

## Utilities

### Build Manifest
- [Build Manifest Downloader](https://github.com/dippyshere/build-manifest-downloader/blob/main/build%20manifest%20downloader.py)
  - *Downloads all the files in a build manifest*

### ChunkV3
- [ChunkV3 Manifest Creator](https://github.com/dippyshere/build-manifest-downloader/blob/main/cloudv3%20manifest%20creator.py)
  - *Assembles a master manifest file through trial and error*
- [ChunkV3 Manifest Downloader](https://github.com/dippyshere/build-manifest-downloader/blob/main/chunkv3%20manifest%20downloader.py)
  - *Downloads the manifests within a master manifest file*
- [ChunkV3 Chunk Downloader](https://github.com/dippyshere/build-manifest-downloader/blob/main/chunkv3%20chunk%20downloader.py)
  - *Downloads chunks from a manifest and assembles the file; Only compatible with single file manifests*
