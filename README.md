# Brain-Coverage

Attribution: This repository contains code adapted from the DCAN-Labs `brain_coverage` project:
- Upstream source: https://github.com/DCAN-Labs/brain_coverage

Modifications in this repository include:
- Loops through subject subdirectories using subject-specific ACPC-space masks to calculate DWI brain coverage computation
- Configuration-driven paths (CONFIG dictionary) for easy adaptation
- Output formatting tailored to `participant_id` and a single DWI coverage metric
