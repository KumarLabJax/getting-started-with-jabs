# dense_gt_a2: second annotation pass of session 2010

A JABS project holding only session 2010 (video, pose and the second annotation pass). The same
instructor labeled every frame of 2010 a second time, **blind to the first pass**
(`data/dense_gt_a1/`). The labels are in `jabs/annotations/2010.json`.

The live demo compares `dense_gt_a2/jabs/annotations/2010.json` with
`dense_gt_a1/jabs/annotations/2010.json` to show how much two passes by the same person at two
different times agree. This is a conceptual demonstration, not best practice (best practice is
independent annotators). To label it again yourself, open this folder as a project in the JABS GUI
and do not open `data/dense_gt_a1/` meanwhile. JABS-generated folders here are gitignored.
