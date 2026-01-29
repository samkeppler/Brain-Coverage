# Brain-Coverage

Attribution: This repository contains code adapted from the advanced-brain-coverage.py script from DCAN-Labs `brain_coverage` project:
- Upstream source: https://github.com/DCAN-Labs/brain_coverage

Modifications in this repository include:
  1. Imaging modality change (BOLD fMRI → DWI)
     - The upstream script computes brain coverage for task-based BOLD fMRI images (*_task-*_run-*_bold.nii.gz).
     - This implementation operates on qsiprep-preprocessed diffusion data (*_space-ACPC_desc-preproc_dwi.nii.gz).
     - Coverage is computed once per subject rather than per task/run.
  2. Configuration-driven execution
     - The upstream script is fully CLI-driven using argparse.
     - This implementation replaces CLI arguments with a centralized CONFIG block specifying dataset paths,qsiprep        version, output locations, and runtime options.
     - This change favors reproducibility and dataset-specific deployment over general-purpose CLI flexibility.
  3. Removal of participants.tsv read/write logic
     - The upstream script reads and updates a BIDS participants.tsv file, adding multiple bc_<task>_run-XXcolumns.
     - This implementation does not modify participants.tsv. Output is written to a standalone QC TSV containing          only participant_id and a single brain coverage metric.
  4. Simplified subject handling
     - The upstream script supports explicit subject and session selection, wildcard matching, and multi-session          datasets.
     - This implementation removes user-specified wildcard filtering and instead uses a fixed file discovery
       pattern to automatically discover qsiprep-preprocessed DWI outputs. It specifically searches for files
       matching: *_dir-*_space-ACPC_desc-preproc_dwi.nii.gz
  5. Subject-specific ACPC-space mask usage
     - The upstream script accepts an arbitrary MNI mask at runtime.
     - This implementation uses a subject-specific ACPC-space brain coverage mask with a deterministic filename
       derived from the subject ID. This ensures spatial alignment between the diffusion data and the mask.
  6. Refactored path and intermediate file management
     - All filesystem paths are centralized in the CONFIG block. Intermediate files are written to a dataset
       specific QC working directory rather than a generic temporary location.
     - Intermediate files are automatically removed unless explicitly retained.
  7. Simplified output metric
     - The upstream script produces task- and run-specific coverage columns. This implementation produces a single        subject-level coverage value (brain_coverage), reflecting diffusion brain coverage rather than task-level
       fMRI coverage.
  8. Script renaming
     - The script has been renamed from the upstream naming convention to brain_coverage_dseg.py to reflect its
       diffusion-specific scope and segmentation-based masking.
