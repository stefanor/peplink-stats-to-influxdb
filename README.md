# Report PepLink statistics to InfluxDB

A Python application that reads statistics from a PepLink router via its
API, and records them in InfluxDB (for graphing with Grafana).

## Scope

Currently only recording:

* Cellular Network Statistics
* Client Bandwidth Statistics

Currently tested on:

* PepLink MAX BR1 5G

## Development

- clone the repo from Github
- edit code
- create a virtualenv and install the requirements in it.
- create a `config.ini` (using `example-config.ini`)
- run `python -m peplink_influxdb`

## License

Copyright 2023 Stefano Rivera <stefano@rivera.za.net>

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
