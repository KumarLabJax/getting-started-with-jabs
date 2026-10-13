# Training Report: grooming

**Date:** October 13, 2026 at 01:33:52 PM

## Training Summary

- **Behavior:** grooming
- **Classifier:** XGBoost
- **Window Size:** 60
- **Balanced Training Labels:** Yes
- **Symmetric Behavior:** No
- **Distance Unit:** cm
- **Training Time:** 612.86 seconds

### Label Counts

- **Behavior frames:** 13,375
- **Not-behavior frames:** 17,843
- **Behavior bouts:** 34
- **Not-behavior bouts:** 68

## Cross-Validation Results

### Performance Summary

- **Mean Accuracy:** 0.8691 (± 0.0845)
- **Mean F1 Score (Behavior):** 0.7641 (± 0.2090)

### Iteration Details
CV Grouping Strategy: Individual Animal

|   Iter |   Accuracy |   Precision (Not Behavior) |   Precision (Behavior) |   Recall (Not Behavior) |   Recall (Behavior) |   F1 Score | Test Group     |
|--------|------------|----------------------------|------------------------|-------------------------|---------------------|------------|----------------|
|      1 |     0.9126 |                     0.9422 |                 0.5616 |                  0.9622 |              0.4505 |     0.5    | 2018.avi \[0\] |
|      2 |     0.9738 |                     0.9548 |                 0.9849 |                  0.9737 |              0.9738 |     0.9793 | 2009.avi \[0\] |
|      3 |     0.7431 |                     0.6638 |                 1      |                  1      |              0.4785 |     0.6473 | 2012.avi \[0\] |
|      4 |     0.9    |                     0.7774 |                 1      |                  1      |              0.8463 |     0.9168 | 2021.avi \[0\] |
|      5 |     0.9843 |                     0.964  |                 1      |                  1      |              0.9729 |     0.9863 | 2015.avi \[0\] |
|      6 |     0.6871 |                     0.3856 |                 1      |                  1      |              0.6106 |     0.7582 | 2013.avi \[0\] |
|      7 |     0.9495 |                     0.9427 |                 1      |                  1      |              0.7014 |     0.8245 | 2022.avi \[0\] |
|      8 |     0.8248 |                     0.9978 |                 0.233  |                  0.8165 |              0.9683 |     0.3756 | 2007.avi \[0\] |
|      9 |     0.7633 |                     0.5546 |                 1      |                  1      |              0.6645 |     0.7984 | 2014.avi \[0\] |
|     10 |     0.8593 |                     0.464  |                 1      |                  1      |              0.8398 |     0.9129 | 2001.avi \[0\] |
|     11 |     0.8947 |                     0.8068 |                 0.9629 |                  0.944  |              0.8653 |     0.9115 | 2016.avi \[0\] |
|     12 |     0.9002 |                     0.928  |                 0.8749 |                  0.8711 |              0.9302 |     0.9017 | 2017.avi \[0\] |
|     13 |     0.857  |                     1      |                 0.2016 |                  0.8517 |              1      |     0.3356 | 2019.avi \[0\] |
|     14 |     0.9182 |                     0.9343 |                 0.873  |                  0.9538 |              0.8256 |     0.8486 | 2004.avi \[0\] |

## Feature Importance

Top 20 features from final model (trained on all labeled data):

|   Rank | Feature Name                                                                   |   Importance |
|--------|--------------------------------------------------------------------------------|--------------|
|      1 | point\_velocity\_dirs fft\_band-5.0Hz-8.0Hz NOSE velocity direction cosine     |         0.11 |
|      2 | pairwise\_distances median NOSE-RIGHT\_FRONT\_PAW                              |         0.06 |
|      3 | pairwise\_distances min RIGHT\_FRONT\_PAW-TIP\_TAIL                            |         0.05 |
|      4 | pairwise\_distances median NOSE-BASE\_TAIL                                     |         0.04 |
|      5 | pairwise\_distances median NOSE-RIGHT\_REAR\_PAW                               |         0.03 |
|      6 | pairwise\_distances min NOSE-TIP\_TAIL                                         |         0.03 |
|      7 | centroid\_velocity\_dir std\_dev centroid\_velocity\_dir                       |         0.03 |
|      8 | pairwise\_distances max LEFT\_EAR-LEFT\_FRONT\_PAW                             |         0.02 |
|      9 | angles median angle RIGHT\_FRONT\_PAW-BASE\_NECK-CENTER\_SPINE sine            |         0.02 |
|     10 | angles min angle RIGHT\_REAR\_PAW-BASE\_TAIL-CENTER\_SPINE sine                |         0.02 |
|     11 | angles fft\_band-8.0Hz-15.0Hz angle RIGHT\_REAR\_PAW-BASE\_TAIL-MID\_TAIL sine |         0.02 |
|     12 | point\_velocity\_dirs mean MID\_TAIL velocity direction                        |         0.02 |
|     13 | point\_velocity\_dirs skew BASE\_TAIL velocity direction sine                  |         0.02 |
|     14 | centroid\_velocity\_dir psd\_kurtosis centroid\_velocity\_dir cosine           |         0.02 |
|     15 | pairwise\_distances mean NOSE-LEFT\_FRONT\_PAW                                 |         0.01 |
|     16 | pairwise\_distances mean NOSE-BASE\_TAIL                                       |         0.01 |
|     17 | pairwise\_distances mean RIGHT\_EAR-RIGHT\_REAR\_PAW                           |         0.01 |
|     18 | pairwise\_distances mean CENTER\_SPINE-LEFT\_REAR\_PAW                         |         0.01 |
|     19 | pairwise\_distances mean CENTER\_SPINE-BASE\_TAIL                              |         0.01 |
|     20 | pairwise\_distances median NOSE-LEFT\_FRONT\_PAW                               |         0.01 |
