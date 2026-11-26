# The World Today — Thursday 26 November 2026

[![news-image-20261126](https://make.fun/badge/news-image-20261126.svg)](https://make.fun/bounty/news-image-20261126)
[![rank](https://make.fun/badge/news-image-20261126/Hasanrdp/news-image-20261126/rank.svg)](https://make.fun/bounty/news-image-20261126)
[![reward](https://make.fun/badge/news-image-20261126/Hasanrdp/news-image-20261126/reward.svg)](https://make.fun/bounty/news-image-20261126)

A one-page newspaper front page that sums up the world's news of
**Thursday 26 November 2026** in a single image, built for the
[make.fun news-image-20261126 bounty](https://make.fun/bounty/news-image-20261126).

## The image

- **Lead story:** North Korea's Kim Jong Un orders a wider deployment of
  tactical nuclear weapons, reported by KCNA on Thursday 26 November —
  drawn as a rocket climbing over night hills.
- **32 more stories from 10 regions** (Asia, Europe, Middle East,
  Americas, Africa, Pacific, Science, Sport, Business, Culture), each
  dated **26 NOV** with its own drawn pictogram: the first Pakistani
  astronaut flying to Tiangong, US tariffs on 14 partners, Ukraine
  striking a Russian air base, Houthi strikes on the Ras Tanura
  refinery, tankers hitting mines in the Strait of Hormuz, Bangladesh's
  36% garment wage rise, India's 26/11 anniversary, Sudan drone
  strikes, the Cairo tanker fire, Colombia freeing 20 hostages,
  Venezuela's $237.5bn debt, and more.
- Every headline is a real story first reported on 26 November 2026
  (Reuters world news summary, KCNA via Reuters, and the day's wire
  round-ups). Nothing is invented.

## How it works

`main.py` is pure Python 3 standard library — no network, no
dependencies. It draws the whole 1024×1024 front page with its own
5×7 bitmap font and PNG encoder and writes it to
`/output/entry.png` (or `$MAKEFUN_OUTPUT_DIR/entry.png`):

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

The program is fully deterministic: two runs write byte-identical
PNGs, and it pins its own expected output hash (29,388 bytes,
sha256 `07377ceeb4997360b5cf769857001051a071705b98f280230a3c438cc83bef84`)
and refuses to finish silently if either ever changes.

## License

MIT — see [LICENSE](LICENSE).
