# AI-Youtube-Shorts-Generator

Highlight ranking criteria, requesting additional candidates and score-based
deduplication were adapted from:
https://github.com/Anil-matcha/AI-Youtube-Shorts-Generator

CLIPFARM retains its own local transcription, source timestamps, Codex integration,
non-overlapping clip selection and rendering. It does not depend on MuAPI.

MIT License

Copyright (c) 2026 Anil Chandra Naidu Matcha

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

# Kick playback API compatibility

The new public Kick playback endpoint and request schema were identified from
yt-dlp's proposed Kick extractor rework (Unlicense), with metadata handling
implemented locally in CLIPFARM from the actual player-session response:
https://github.com/yt-dlp/yt-dlp/pull/17322

# Bundled caption fonts

CLIPFARM bundles twenty fixed TrueType caption faces under the SIL Open Font License,
Version 1.1. The full upstream copyright and license notices remain alongside the
fonts at the paths below. The menu is a selection of font families, without an
asserted popularity ranking.

The catalog is `font_catalog.py`. `assets/fonts/provenance.json` records each binary's
official source URL, license source, SHA-256 and byte size. Licenses and repository
binaries are pinned to the [official Google Fonts repository](https://github.com/google/fonts/tree/9710da1eacb3be272583c3224dcb70f9da6eadbb),
retrieved on 2026-10-04. Ten families use that repository's static faces. Montserrat,
Inter, Roboto, Oswald, Open Sans, Nunito, Rubik, DM Sans, Raleway and Quicksand use
unmodified static Bold TTFs served by the official `fonts.googleapis.com` /
`fonts.gstatic.com` service; their provenance records also retain the CSS source and
original repository font URL. Anton was already bundled.

All paths in this table are relative to the repository root.

| Family | Bundled face | Full OFL notice |
| --- | --- | --- |
| Anton | `assets/fonts/Anton-Regular.ttf` | [OFL-Anton.txt](assets/fonts/OFL-Anton.txt) |
| Bebas Neue | `assets/fonts/BebasNeue-Regular.ttf` | [OFL.txt](assets/fonts/bebasneue/OFL.txt) |
| Montserrat | `assets/fonts/Montserrat-Bold.ttf` | [OFL.txt](assets/fonts/montserrat/OFL.txt) |
| Poppins | `assets/fonts/Poppins-Bold.ttf` | [OFL.txt](assets/fonts/poppins/OFL.txt) |
| Inter | `assets/fonts/Inter-Bold.ttf` | [OFL.txt](assets/fonts/inter/OFL.txt) |
| Roboto | `assets/fonts/Roboto-Bold.ttf` | [OFL.txt](assets/fonts/roboto/OFL.txt) |
| Oswald | `assets/fonts/Oswald-Bold.ttf` | [OFL.txt](assets/fonts/oswald/OFL.txt) |
| Open Sans | `assets/fonts/OpenSans-Bold.ttf` | [OFL.txt](assets/fonts/opensans/OFL.txt) |
| Lato | `assets/fonts/Lato-Bold.ttf` | [OFL.txt](assets/fonts/lato/OFL.txt) |
| Nunito | `assets/fonts/Nunito-Bold.ttf` | [OFL.txt](assets/fonts/nunito/OFL.txt) |
| Rubik | `assets/fonts/Rubik-Bold.ttf` | [OFL.txt](assets/fonts/rubik/OFL.txt) |
| Barlow Condensed | `assets/fonts/BarlowCondensed-Bold.ttf` | [OFL.txt](assets/fonts/barlowcondensed/OFL.txt) |
| Archivo Black | `assets/fonts/ArchivoBlack-Regular.ttf` | [OFL.txt](assets/fonts/archivoblack/OFL.txt) |
| DM Sans | `assets/fonts/DMSans-Bold.ttf` | [OFL.txt](assets/fonts/dmsans/OFL.txt) |
| Fjalla One | `assets/fonts/FjallaOne-Regular.ttf` | [OFL.txt](assets/fonts/fjallaone/OFL.txt) |
| Raleway | `assets/fonts/Raleway-Bold.ttf` | [OFL.txt](assets/fonts/raleway/OFL.txt) |
| Quicksand | `assets/fonts/Quicksand-Bold.ttf` | [OFL.txt](assets/fonts/quicksand/OFL.txt) |
| Lobster | `assets/fonts/Lobster-Regular.ttf` | [OFL.txt](assets/fonts/lobster/OFL.txt) |
| Pacifico | `assets/fonts/Pacifico-Regular.ttf` | [OFL.txt](assets/fonts/pacifico/OFL.txt) |
| Bungee | `assets/fonts/Bungee-Regular.ttf` | [OFL.txt](assets/fonts/bungee/OFL.txt) |
