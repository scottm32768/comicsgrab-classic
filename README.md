# ComicsGrab Classic

ComicsGrab retrieves webcomic images and creates local HTML pages so you can read several comics together. This fork ports Tom Parker's original ComicsGrab 2.1 to Python 3, adds HTTPS support, and support for numbered image sequences in comics while retaining the original definition-file approach.

## Requirements

- Python 3.
- The `requests` and `curl_cffi` Python packages for HTTP retrieval.
- Tested on Linux. Other platforms may work but have not been verified.

## Setup

From the project directory, create a virtual environment and install the HTTP dependencies:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp strips.def.example strips.def
```

On Debian or Ubuntu, if virtual-environment creation reports missing support, install the appropriate package:

```sh
sudo apt install python3-venv
```

Edit your local `strips.def` to choose comics and define groups. Keep it out of Git. See [strips-def-readme.txt](strips-def-readme.txt) for the format and [strips.def.example](strips.def.example) for a small starting configuration.

## Quick start

Retrieve one strip into a dedicated output directory:

```sh
.venv/bin/python grabber.py -s sluggy ./output
```

Open `output/index.html` in your browser. ComicsGrab also writes a dated HTML page and stores images in dated subdirectories.

Select multiple strips by repeating `-s`:

```sh
.venv/bin/python grabber.py -s sluggy -s fauxpas ./output
```

To retrieve a group defined in your local configuration:

```sh
.venv/bin/python grabber.py -g examples ./output
```

Use a dedicated output directory: ComicsGrab updates existing pages and removes older comic images as part of its retention behavior. It is not a permanent archive; the current retention setting is 14 days, with exceptions for the latest available comic images.

## Command-line options

```text
grabber.py [-d LEVEL] [-f FILE] [-c DIRECTORY] [-p PROXY]
           [-g GROUP]... [-s STRIP]... OUTPUT_DIRECTORY
```

Place options before the output directory and select at least one strip or group.

| Option | Meaning | Default |
| --- | --- | --- |
| `-s STRIP` | Select a strip by its short name; repeat as needed | None |
| `-g GROUP` | Select a group; repeat as needed | None |
| `-f FILE` | Definition file | `strips.def` |
| `-c DIRECTORY` | Retrieval cache directory | `./cache` |
| `-p PROXY` | Proxy URL for HTTP requests | None |
| `-d LEVEL` | Minimum error category included in generated HTML | `2` |
| `-h` | Print help and exit | |

Error categories are 1 for warnings, 2 for failed comic extraction, 3 for HTTP errors, and 4 for additional diagnostics. Higher values are not simply increasing verbosity: the HTML report includes errors whose category is at least the selected level, while level 4 also enables some extra diagnostic output.

Replace the output directory with `listme` to print an HTML list of selected comic homepages:

```sh
.venv/bin/python grabber.py -s sluggy listme
```

Paths are relative to the directory where you run the command. For scheduled runs, use explicit paths for the interpreter, script, definition file, cache, and output.

### Running from a shell script

Create a script such as `update-comics.sh`, adjusting the paths and group name for your setup:

```sh
#!/bin/sh
COMICSDIR="$HOME/public_html/comics"
PROJECTDIR="$HOME/src/comicsgrab"

umask 022
cd "$PROJECTDIR" || exit 1
"$PROJECTDIR/.venv/bin/python" grabber.py -g examples "$COMICSDIR"
```

The group must be defined in your local `strips.def`. The script calls the virtual environment's Python interpreter directly, so activation with `source` is unnecessary.

Make the script executable, then run it:

```sh
chmod +x update-comics.sh
./update-comics.sh
```

Open `index.html` in the output directory to read the results.

## HTTP retrieval

ComicsGrab uses Python `requests` for normal HTTP GET and HEAD requests. If a request receives an HTTP 403 (Forbidden) response, a connection failure, or times out, it falls back to `curl_cffi` with browser impersonation.

## Definition examples

### Search and generated URLs

`type search` extracts an image URL from a web page using a regular expression. The captured image URL may be absolute or may need a `baseurl` prefix. If `searchpage` is omitted, the homepage is searched.

`type generate` builds an image URL from a template, typically using date fields such as `%Y`, `%m`, and `%d`.

### Numbered comics

```text
strip fauxpas
    name Faux Pas
    homepage https://www.ozfoxes.com/fauxpas.htm
    type numbered
    imageurl https://www.ozfoxes.com/fp/fp-%dlg.jpg
    fallbackurl https://www.ozfoxes.net/fp/fp-%d.jpg
    start 3214
end
```

For `numbered`, `%d` is the strip number rather than the day of the month.

**`start` is the last-known number, not the first number to download.** With `start 3214` and no saved numbered images, the first request is for 3215. To begin with strip 3214, use `start 3213`.

On subsequent retrievals, ComicsGrab scans the output subdirectories for filenames such as `fauxpas-3215.jpg`. It resumes after the highest number found, using `start` as the lower bound. Keep the same output directory to preserve this progress.

For each number, ComicsGrab checks the preferred `imageurl`. If that existence check reports the image absent, it checks the optional `fallbackurl` for the same number. It then downloads the selected image and advances to the next number. It stops at the first unavailable number or failed check/download; it does not skip gaps. The fallback is not a general retry for every download failure.

### Shared classes

Classes let several strips share retrieval settings. A strip uses `useclass` and can add or override settings, such as its update days:

```text
strip foxtrot
    name FoxTrot
    useclass gocomics-srch
    days Sun
end
```

With a class homepage of `https://www.gocomics.com/$strip/`, `$strip` becomes `foxtrot`. Numbered class parameters such as `$1` are another way to supply strip-specific values; see the format documentation.

### More historical examples

The original project has a much larger [historical strips.def collection](https://github.com/palfrey/comicsgrab/blob/ebe10facf32f0af730820bf3186ad9e80019ac8d/strips.def). Later versions split the definitions into separate files.

The `numbered`, `start`, and `fallbackurl` features are additions in this fork.

## Troubleshooting

- **Missing `requests` or `curl_cffi`:** Install both packages using the same virtual-environment interpreter that runs ComicsGrab: `.venv/bin/python -m pip install requests curl_cffi`.
- **A comic stops updating:** Check its current page markup and image URL. Sites sometimes change and definitions must be update.
- **No image found:** Check the regular expression's captured URL, the search page, and any `baseurl` prefix. [Regular Expressions 101 can help with that.](https://regex101.com)
- **HTTP 403 persists:** The site is refusing the request even with the fallback client. The site may be blocking automated downloads.

## Credits and license

Original ComicsGrab by Tom Parker, derived from the definition format and collection used by Dailystrips. The original definition-file documentation credits Andrew Medico.

ComicsGrab Classic is released under GPL version 2, except where otherwise noted in individual source files. See [COPYING](COPYING). Preserve the original notices and applicable license terms. The upstream project is [palfrey/comicsgrab](https://github.com/palfrey/comicsgrab).

Comic artwork and other third-party content remain the property of their respective copyright holders. Users are responsible for complying with applicable laws and the terms and policies of the sites they access.

