# Planning answer — grounded example

This is a hand-written example of an answer that stays inside the inventory.
It exists so `scripts/planning_eval.py` has a known-clean input in the test
suite. It is not advice and not a real assistant transcript.

## Best fit

**3i CSU-W1 Spinning Disk** (`scope-3i-csu-w1-spinning-disk`)

- Route: `confocal_spinning_disk`.
- Illumination on that route: `source:laserstack_v4_2` (488 nm) and
  `source:laserstack_v4_3` (561 nm), both recorded on this route.
- Detection endpoint: `endpoint:detector_1`. The recorded branch block is
  exclusive, so `endpoint:detector_2` is an alternative, not a simultaneous
  second channel.
- Objectives are recorded per instrument, not per route, so objective choice
  needs staff confirmation.

## Backup

**Nikon Ti2-E Crest V3** (`scope-nikon-crest-v3`), route `confocal_spinning_disk`.

## Not established by the records

- Frame rates, exposure limits and simultaneous dual-camera capture.
- Whether either instrument can be booked; the inventory records no booking,
  access or training information.
- Phototoxicity limits for a 24 h run.

Please confirm the objective, the detection branch and scheduling with facility
staff before booking.
