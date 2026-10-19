A Fragile Watermarking for Medical Image Tamper Detection
START HERE — implementation package
Established 2026-10-19. Five documents, in the order you should read them.

================================================================
READING ORDER
================================================================

1. 01_PROJECT_DOSSIER.md        What we want to do, how, and what to do.
                                The single authority. Read it fully once.
2. 04_PITFALLS_AND_TRAPS.md     Thirty-five ways this fails. Read before
                                writing any code.
3. 02_ARCHITECTURE.md           Twelve modules with inputs, outputs,
                                invariants and tests.
4. 03_PROJECT_FLOW.md           Phases, gates, dependencies, decisions.
5. MANIFEST.txt                 What each file is.

================================================================
IF YOU ONLY REMEMBER FIVE THINGS
================================================================

1. The container is PNG. A JPEG container destroys the fragile mark at
   birth and every number afterwards is fiction.
2. The tag digest is computed from the LL summary the embedder never
   touches, never from the coefficients that carry the mark.
3. The verifier receives the image and the key. Nothing else. No mask.
4. Every accuracy is reported as a pair with its coverage. An abstaining
   system that reports only answered cases can look perfect while doing
   nothing.
5. The battery is frozen and hashed before results exist. A change after
   results is an amendment and a full re-run.

================================================================
FIRST SESSION, IN ORDER
================================================================

1. Create the repository and config.py. Put every tunable number in that
   one file with a comment saying whether it comes from the literature or
   was chosen here.
2. Write the Haar transform pair and the test that proves perfect
   reconstruction on random arrays.
3. Write preprocess and its receipt.
4. Write the binder and prove two things: changing a detail coefficient
   does not change the tag, and changing the address changes every bit.
5. Write the fragile embedder and the one-level perturbation test.
6. Write the container round trip and prove bit-identical reload.
7. Write the verifier and run the six pre-flight checks.
8. Do not proceed to anything else until all six pass.

A day spent here is a month saved later. A verifier that reports clean
images as tampered will produce a textbook full of numbers that mean
nothing.

================================================================
RULES THAT DO NOT BEND
================================================================

1. The dossier is the only authority. If another file disagrees with it,
   that file is wrong.
2. The title is fixed: A Fragile Watermarking for Medical Image Tamper
   Detection. It is never reworded.
3. The battery is twenty-two conditions. Any other count is withdrawn.
4. A number without a receipt does not exist. A receipt is the command,
   the seed, the image count and the code version.
5. Nothing is claimed as measured until it has been measured. Published
   figures from other papers are cited as theirs, in a table that says so.
6. The sealed expectations file is not opened until results are frozen.
   It exists to check the work afterwards, not to steer it.

================================================================
WHAT IS DELIBERATELY NOT IN THIS PACKAGE
================================================================

No earlier plan, no pilot output, no prior measured number, and no sealed
expectations document. The project is built from zero and every number it
reports will be derived from its own receipts. This is the point of the
package, not an omission.

================================================================
