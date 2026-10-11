# Raw Dataset Manifest

Raw sources are retained under `cloud datasets AWS uni/` to preserve the supplied filenames and provenance. They are not copied into this folder.

| Source | Forecast target | Cadence | Identity |
| --- | --- | --- | --- |
| IIT Bombay | Electricity, `W1 + W2 + W3` | Hourly | Anonymous apartment |
| La Trobe | Consumption, unit pending validation | 15 minutes | Campus and meter |
| Valahia UVTgv | Electricity demand | Hourly | ABR, C, ICSTM building |

The source parsers preserve the original filename and row number in PostgreSQL. No interpolation, unit conversion, or outlier removal occurs silently.
