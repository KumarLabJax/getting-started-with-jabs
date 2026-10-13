<!--
PROVENANCE / ATTRIBUTION
========================
This file is a verbatim copy of the README.md distributed with the source dataset,
vendored into this repository for offline reference and version stability.

Citation:
  Kumar, Vivek; Brian Geuther; Sean Deats, 2024,
  "The Jackson Laboratory (JAX) - Kumar Lab Mouse Strain Survey of Behavior
  in the Open Field Arena (Video Dataset)",
  https://doi.org/10.7910/DVN/SAPNJG, Harvard Dataverse, V1; README.md

License: CC BY-NC-SA 4.0 (http://creativecommons.org/licenses/by-nc-sa/4.0)
Retrieved from Harvard Dataverse datafile id 10174762.

Only this provenance header has been added; the dataset README content below
is unchanged from the source.
-->

# Organization of Data

The data is organized in folders. Each video file `[video_file].mp4` also has pose prediction files `[video_file]_pose_est_v6.h5`.

Each video is 99150 frames long and imaged at 30fps, or the equivalent of 55m and 5s. The first 150 frames (5 seconds) of the video are approximately when the mice are placed into the arena. The remaining 55 minutes of video are the data used in publications.

The metadata associated with each video is contained within `	
OFA_Release_ExperimentMetadata.csv` where the row providing the metadata points to the video using the `NetworkFilename`. For convenience, the `pose_file` column also points to the associated pose file.

# Description of Metadata Fields

* NetworkFilename: Video file associated with this row.
* pose_file: Pose file associated with this row.
* Strain: Strain code of the animal.
* Sex: Sex of the animal. M = Male. F = Female.
* Cage: Housing identifier of the animal. Same values indicate the animals were housed together. This does not necessarily indicate all the animals in the home cage.
* DOB: Date of birth of the animal, +/- 3 days.
* Box: Testing arena the animal was placed in.
* Test Date: Date of the experiment
* Weight: Measured body weight in grams of the animal 30 minutes before the experiment.
* TestTime: Approximate start time of the experiment. Time indicates when the experimenter began placing mice into their testing arenas.
* Tester: Person placing the animal into the arena.
* RoomOrigin: Room in which the mouse originated. These are all JAX breeding colony rooms except B2B, which is the Kumar Lab colony room.
* ShipDate: If the mouse was produced in a JAX breeding colony room, the date which the mouse was moved to B2B. Empty if the mouse was bred in B2B.
* LightIntensity: Approximate light intensity in lux measured at the middle of the floor of the arena. Light measurements were taken approximately every 6 months. Value indicates the most recent measurement.
* in_groom_dataset: Was this animal included in the grooming paper dataset?
* in_gait_dataset: Was this animal included in the gait paper (stride-level analysis) dataset?
* in_mass_dataset: Was this animal included in the visual mouse mass dataset?
* in_jabs600_v1_dataset: Was this animal included in the first version of the JABS600 dataset?
* in_jabs1200_v1_dataset: Was this animal included in the first version of the JABS1200 dataset?
* in_jabs600_v2_dataset: Was this animal included in the second version of the JABS600 dataset?
* in_jabs1200_v2_dataset: Was this animal included in the second version of the JABS1200 dataset?
* first_frame_pose: First frame where any keypoint was predicted.
* first_frame_full_pose: First frame with all 12 keypoints
* first_frame_seg: First frame where segmentation data was assigned an id
* pose_counts: Total number of poses with any keypoints predicted
* seg_counts: Total number of segmentations matched with poses
* early_poses: Number of pose predictions in the first 150 frames of the video
* early_segs: Number of segmentation matched with poses in the first 150 frames of the video
* missing_poses: Missing poses in the primary duration  (55 minutes of experiment)
* missing_segs: Missing segmentations in the primary duration  (55 minutes of experiment)
* pose_tracklets: Number of tracklets in the primary duration (55 minutes of experiment). Tracklet are contiguous segments of time.
* missing_keypoint_frames: Number of frames which don't contain all 12 keypoints in the primary duration (55 minutes of experiment)
* missing_arena_corners: Were the arena corners not predicted?

# Description of Pose File Contents

Pose files contain predictions from deep learning models from the Kumar Lab group.
The arena corner model may not always predict corners that make sense. When this occurs, no arena corner data is written and a default value (average value across 100 manual measurements) for the `cm_per_pixel` conversion is provided.

## Data Description

* `poseest/confidence`: peak value that the pose estimation model predicted per keypoint. Shape is `[frame, animal, keypoint]`.
* `poseest/id_mask`: unused for single mice
* `poseest/identity_embeds`: unused for single mice
* `poseest/instance_count`: number of valid poses along the `animal` dimension in `poseest/points`. Shape is `[frame]`
* `poseest/instance_embed_id`: resolved identity for the keypoint data for the entire video. Trivial for single mouse (always 1). Shape is `[frame, animal]`.
* `poseest/instance_embedding`: unused for single mice
* `poseest/instance_id_center`: unused for single mice
* `poseest/instance_seg_id`: tracklet id assigned to segmentation data. Shape is `[frame, animal]`.
* `poseest/instance_track_id`: tracklet id assigned to keypoint data. Shape is `[frame, animal]`.
* `poseest/longterm_seg_id`: resolved identity for the segmentation data for the entire video. Trivial for single mouse (always 1). Shape is `[frame, animal]`.
* `poseest/points`: location for individual keypoints. Shape is `[frame, animal, keypoint, position]`. Keypoint position is sorted `[y, x]`.
* `poseest/seg_data`: compressed segmentation data. Data is stored as a padded matrix of contours. Pad value is `-1` (invalid value for contours). Shape is `[frame, animal, contour, contour_length, position]`. Segmentation position is sorted `[x, y]`.
* `poseest/seg_external_flag`: describes whether a contour is an external (1) or internal (0) contour. Shape is `[frame, animal, contour]`.
* `static_objects/corners`: Predicted corner locations of the arena floor. Shape is `[corner_index, position]`. Arena corner positions are sorted `[x, y]`.

### Attributes

* `poseest` -> `cm_per_pixel`: coefficient to convert pixels to cm.
* `poseest` -> `cm_per_pixel_source`: origin of `cm_per_pixel` value.
* `poseest` -> `version`: version of the pose file. Always 6.0.

Each pose file also stores the model used in generating the predictions. The same set of models have been used for this entire release of this dataset.

* `poseest/points` -> `config`: string describing pose model configuration
* `poseest/points` -> `model`: string describing the configuration that produced the trained model
* `poseest/seg_data` -> `config`: string describing segmentation model configuration
* `poseest/seg_data` -> `model`: string describing the checkpoint used from training
* `static_objects/corners` -> `config`: string describing the arena corner model configuration
* `static_objects/corners` -> `config`: string describing the checkpoint used from training

### Shape Description

* `frame`: index of the frame of the video
* `animal`: index of the animal. Since this dataset is always 1-animal, this dimension is always 1
* `keypoint`: index of the keypoint. Keypoints are sorted:
 * 0: Nose
 * 1: Left Ear
 * 2: Right Ear
 * 3: Base Neck
 * 4: Left Front Paw
 * 5: Right Front Paw
 * 6: Center Spine
 * 7: Left Rear Paw
 * 8: Right Rear Paw
 * 9: Base Tail
 * 10: Mid Tail
 * 11: Tail Tip
* `position`: axis of length 2 for either `[x, y]` or `[y, x]` values pointing to the image pixels.
* `contour`: contour index when multiple contours are needed to describe a segmentation mask.
* `contour_length`: point index in the contour. Contours are a list of keypoints. This is that "list" dimension. Contours are compressed using opencv's `CHAIN_APPROX_SIMPLE` compression.
* `corner_index`: index of for each of the 4 corners.
