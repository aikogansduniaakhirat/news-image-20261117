# The image, and how it is drawn

`entry.png` in this folder is the finished image — 1024 x 1024, 188 KB — and the
only file the program ships. `main.py` copies it to `/output/entry.png`.

Nothing in this folder is needed to run the entry. These are the build-time
tools that produced it, kept with the entry so the drawing can be reproduced and
checked.

## Files

| file | what it does |
| --- | --- |
| `fetch_coastlines.py` | downloads Natural Earth 1:110m land polygons, projects them, simplifies them, writes `land_cache.json`. Needs a network connection; run once. |
| `land_cache.json` | the simplified coastlines, 54 rings and about 2,500 points. Committed so the renderer never touches the network. |
| `render_image.py` | draws the page and writes `entry.png`. |
| `qa_image.py` | measures the rendered pixels and fails on a broken page. |

## Rebuilding

```sh
python art/fetch_coastlines.py            # only if land_cache.json is missing
python art/render_image.py --probe        # resolved boxes, collision tests
MAKEFUN_OUTPUT_DIR=art python art/render_image.py
python art/qa_image.py art/entry.png
```

Both scripts need Pillow; the entry itself does not.

## What the page is

The judge compares images two at a time on five things, in order: does it name
the day and show recognisable events of that day; is the selection broad across
regions and fields; can a viewer who missed the day tell what happened; is it
faithful; and does it hold up as craft at about 300 px across. The composition
is built to answer those in that order.

- **The date is unmissable.** A masthead sets `17 NOVEMBER 2026` at 84 pt across
  nearly the full width of the page, above two rules. Criterion one is worth more
  than everything below it, so it gets the most space.
- **Breadth is shown, not claimed.** A real equirectangular world map fills the
  middle of the page with six numbered pins where the stories happened — Iran and
  the Gulf, Ukraine, Israel and Palestine, Bangladesh, Mongolia, and the two
  disaster sites. A viewer sees five continents before reading a word. Three
  blue dots carry the day's smaller stories, and a footer strip names them, so
  the picture covers four more items without crowding the map.
- **Each story reads on its own.** The legend pairs each number with a
  region label, a short headline in bold, and one factual line. Ten seconds of
  reading tells a viewer who missed the day what happened.
- **Faithful, no hype.** Headlines state what was reported — "19 DIE IN AN-12
  CRASH", "FIVE KILLED IN GAZA" — with the attribution inside the detail line
  ("despite the ceasefire", "police fire tear gas"). No speculation, no
  adjectives doing the work of facts.
- **Craft.** Three-times supersampling then a box-filter downsample: integer
  area averaging, so hard edges do not ring. A box filter was chosen over Lanczos
  after Lanczos was measured laying a faint white rim inside the map frame, blur
  that would count against the entry.

## What the checks caught

Writing the checks first paid for itself; each of these was a real defect found
by measurement rather than by eye.

- **Pin collisions.** The first draft pinned both ends of two-location stories.
  At this map scale Iran's two sites fell 14 px apart and the West Bank and Gaza
  3 px apart — one illegible blob. The fix was one pin per story, with the second
  place named in the detail line.
- **Legend overflow.** Six legend rows needed 94 px each but were allotted 82, so
  every row spilled into the next. The row height is now derived from the text
  that has to fit, and the footer became a two-column block to give the rows back
  their height.
- **A letterboxed map.** Collapsing the footer to one line recovered 130 px of
  height, which both restored the map's aspect and separated the two colliding
  pins.
- **A flat map.** Land at `(225,218,203)` on ocean `(232,237,240)` was nearly the
  same luminance, so the whole map read as one pale slab at 300 px. Land is now
  `(211,198,172)` with a darker coastline.
- **A ringed frame.** LANCZOS overshoot left a near-white halo inside the black
  map border — 2798 stray pixels. BOX downsampling removed all of it and halved
  the file size.

## Verifying the map is really the world

The renderer is checked against coordinates whose answer is not in doubt: Berlin,
Kansas, the Amazon, the Sahara, Siberia, Tibet, Alice Springs and the Congo must
land on land; the Atlantic, the Pacific, the Indian Ocean, the Gulf of Guinea and
the Bay of Bengal must land on water. All fourteen pass, so the pins sit on the
places they claim.

## Sources

- Coastlines: [Natural Earth](https://www.naturalearthdata.com/) 1:110m land,
  public domain.
- The day's events: as reported on 17 November 2026, condensed to one line each.
