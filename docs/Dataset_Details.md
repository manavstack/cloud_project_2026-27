# Dataset Details

## IIT Bombay residential electricity

- **Source:** supplied IIT Bombay CSV collection and README.
- **Size:** 39 hourly apartment files, stated December 2016 to June 2018.
- **Fields:** `TS`, phase voltages `V1-V3`, phase electricity values `W1-W3`.
- **License:** CC BY 4.0 according to the supplied README.
- **Processing:** retain anonymous apartment ID; parse `TS` as Unix epoch seconds (UTC instants; source-local display is IST); record `W1 + W2 + W3` as Wh only when all three phase values are present.

## La Trobe campus consumption

- **Source:** supplied `building_consumption.csv.zip`.
- **Size:** archive contains 263 MB CSV; workflow identifies 8,095,524 records and 64 campus-meter pairs.
- **Fields:** `campus_id`, `meter_id`, `timestamp`, `consumption`.
- **Processing:** streaming chunks; keep campus and meter as a compound identity. Unit and timezone need explicit confirmation before cross-source combinations.

## Valahia UVTgv demand

- **Source:** supplied E-LAND UVTgv demand files.
- **Size:** twelve building, energy-vector, and year files for 2019–2020.
- **Fields:** a single `kWh` column.
- **License:** CC BY-NC 4.0 according to the supplied README.
- **Processing:** reconstruct hourly timestamps from filename year using Europe/Bucharest policy; keep electricity and heat separate.
