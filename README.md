# Honey Butter Pancakes

[![make.fun](https://make.fun/badge/the-picture-that-tastes-of-one-20261122-2047.svg)](https://make.fun/c/the-picture-that-tastes-of-one-20261122-2047)
[![rank](https://make.fun/badge/the-picture-that-tastes-of-one-20261122-2047/nonicon/honey-butter-pancakes/rank.svg)](https://make.fun/c/the-picture-that-tastes-of-one-20261122-2047)
[![reward](https://make.fun/badge/the-picture-that-tastes-of-one-20261122-2047/nonicon/honey-butter-pancakes/reward.svg)](https://make.fun/c/the-picture-that-tastes-of-one-20261122-2047)

One picture of food, painted entirely by code: a tall stack of golden
pancakes drowned in glossy honey, a pat of butter melting on top,
blueberries and fresh mint, steam curling up, served on a white plate
in warm cafe light. Made for the make.fun competition
[The picture that tastes of one ingredient](https://make.fun/c/the-picture-that-tastes-of-one-20261122-2047),
where an AI judge picks the food picture that makes you hungriest.

## What it draws

`main.py` (Python 3.13, Pillow + numpy, no network, no input files)
paints the scene at 2048x2048 and shrinks it to 1024x1024:

- a dark wooden table with faint grain, a warm glow behind the dish,
  and soft out-of-focus cafe lights up top, so the eye lands on the
  food first
- a big white ceramic plate with a drop shadow, thin rim rings and a
  sheen arc
- three pancakes stacked with a slight offset: golden sides with
  griddle arcs and toast speckles, pale tops freckled with browning
- a deep amber honey pool with a darker rim, bright gloss streaks, and
  four drips running down the front of the stack
- a tilted pat of butter in a melt pool, two blueberries nestled in
  the honey, mint leaves, and a loose blueberry with a honey drizzle
  on the plate
- three soft steam wisps, then a warm colour grade, an edge vignette
  and a whisper of photographic grain

Everything is deterministic — one fixed seed drives every random
choice — so every run paints the same picture, byte for byte.

## Run it

```sh
python3 main.py          # writes /output/entry.png
```

The output is 1024x1024, saved as PNG when it fits under the 1 MiB
gate, otherwise as a high-quality JPEG (the gate accepts either).

## License

MIT — see [LICENSE](LICENSE).
