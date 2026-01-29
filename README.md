## Conceptual Overview

This repository implements a two-stage workflow for computing brain coverage metrics from qsiprep-preprocessed diffusion MRI data.

First, a preprocessing script applies MNI-space anatomical masks (e.g., cerebrum, cerebellum, brainstem) to each subject’s native ACPC diffusion space. The specific masks used in this step are uploaded in this repository in the masks folder. This step produces subject-specific, region-level brain masks that are spatially aligned to the diffusion data.

Second, a coverage computation script uses these subject-specific masks to quantify the proportion of each region that is covered by the diffusion data. Coverage is computed by thresholding the mean diffusion image, applying the region mask, and calculating the percentage of nonzero voxels relative to the
full mask extent.

Together, these scripts enable reproducible, region-specific brain coverage quality control for diffusion MRI datasets.

## Mask Transformation Preprocessing (`apply_dseg_masks.sh`)

The script `apply_mni_masks.sh` is a required preprocessing step for the brain coverage analysis. Its purpose is to transform a set of anatomical masks defined
in MNI152NLin2009cAsym space into each subject’s native ACPC diffusion space.

  ### What the script does

  For each subject, the script:

  1. Locates the QSIPrep-provided composite transform from MNI152NLin2009cAsym space to subject ACPC space.
  2. Identifies the subject’s diffusion reference image (`*_space-ACPC_dwiref.nii.gz`) to define the target grid.
  3. Applies the MNI→ACPC transform to each input mask using`antsApplyTransforms` (via the `antsx/ants:2.5.3` Docker container).
  4. Resamples each mask into the subject’s diffusion reference space using nearest-neighbor interpolation to preserve label integrity.
  5. Writes subject-specific, ACPC-space mask files into the QSIPrep `dwi/` directory.

  This process is repeated for multiple anatomical masks (e.g., cerebrum, cerebellum, brainstem), enabling region-specific coverage metrics downstream.

  ### Inputs

  - A list of subject identifiers (`sj_list.txt`)
  - MNI-space anatomical masks stored in the `masks/` directory
  - QSIPrep derivatives containing:
  - MNI→ACPC composite transforms
  - ACPC-space diffusion reference images

  ### Outputs

  For each subject and each mask, the script generates an ACPC-space mask with a deterministic filename of the form:sub-<ID>space-ACPC<region>_brain_coverage_mask.nii.gz. 
  These outputs are used directly by the coverage computation script.

  ### Notes

  - The script is designed to be idempotent: mask generation is skipped if the
  output file already exists.
  - Nearest-neighbor interpolation is used to avoid partial-volume artifacts in
  binary or label masks.
  - The script assumes QSIPrep-compliant directory and filename conventions.

## Brain Coverage Calculation (brain_coverage_dseg.py)

  ### Attribution:
  - This script contains code adapted from the advanced-brain-coverage.py script from DCAN-Labs `brain_coverage` project:
  - Upstream source: https://github.com/DCAN-Labs/brain_coverage
  
  ### Modifications from the upstream script include:
  1. Imaging modality change (BOLD fMRI → DWI)
     - The upstream script computes brain coverage for task-based BOLD fMRI images (*_task-*_run-*_bold.nii.gz).
     - This implementation operates on qsiprep-preprocessed diffusion data (*_space-ACPC_desc-preproc_dwi.nii.gz).
     - Coverage is computed once per subject rather than per task/run.
  2. Configuration-driven execution
     - The upstream script is fully CLI-driven using argparse.
     - This implementation replaces CLI arguments with a centralized CONFIG block specifying dataset paths,qsiprep version, output locations, and runtime options.
     - This change favors reproducibility and dataset-specific deployment over general-purpose CLI flexibility.
  3. Removal of participants.tsv read/write logic
     - The upstream script reads and updates a BIDS participants.tsv file, adding multiple bc_<task>_run-XXcolumns.
     - This implementation does not modify participants.tsv. Output is written to a standalone QC TSV containing only participant_id and a single brain coverage metric.
  4. Simplified subject handling
     - The upstream script supports explicit subject and session selection, wildcard matching, and multi-session datasets.
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
     - The upstream script produces task- and run-specific coverage columns. This implementation produces a single subject-level coverage value (brain_coverage), reflecting
       diffusion brain coverage rather than task-level fMRI coverage.
  8. Script renaming
     - The script has been renamed from the upstream naming convention to brain_coverage_dseg.py to reflect its
       diffusion-specific scope and segmentation-based masking.
