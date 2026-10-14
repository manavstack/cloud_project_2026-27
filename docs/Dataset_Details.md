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
- **Fields:** one demand-value column; supplied column labels vary by building/year. The dataset documentation identifies the values in kWh.
- **License:** CC BY-NC 4.0 according to the supplied README.
- **Processing:** reconstruct hourly timestamps from filename year using Europe/Bucharest policy; keep electricity and heat separate.
- **Loaded coverage:** 52,560 electricity and 52,560 heat observations across three buildings per vector (2019–2020); each building/year file contributes 8,760 hourly rows.
- **Coverage limitation:** the supplied 2020 files contain 8,760 rows, not the 8,784 hours in leap year 2020. Reconstructed timestamps therefore stop before the final calendar day; do not interpret this as complete 2020 coverage or synthesize missing readings without source evidence.
- **Forecast limitation:** the last reconstructed Valahia readings are on December 30, 2020. Forecasts are historical projections, not current demand predictions.
- **FedAvg eligibility:** all twelve building/year/vector files met the demo's 500-row threshold and trained as separate clients.

## IIIT-Delhi campus power

- **Source:** supplied IIIT-Delhi `energy_dataset` files and their `Readme.txt`.
- **Fields:** Unix-second `timestamp` and instantaneous `power` in watts, with Asia/Kolkata as the documented timezone. The supplied raw examples advance at one-minute intervals.
- **Client selection:** train the nine individual building/mains/UPS files as separate clients. Exclude campus-wide and transformer totals from this run because they overlap the building measurements and would double-count load.
- **Processing for the profile demo:** aggregate valid power readings to local-hour mean watts before local training. This is a profile-learning target, not an energy-in-kWh conversion.
- **FedAvg eligibility:** all nine selected building files met the demo's 500-hour threshold and trained as separate clients.

## University of Twente extracts

- **Source:** supplied nine building CSV extracts.
- **Fields:** timestamp plus a source-specific energy column labeled in kWh.
- **Coverage:** only 32–33 data rows per file are present. These extracts do not meet the 500-valid-row minimum for the chronological local training/holdout, so they are reported as excluded rather than presented as trained models.

## Database readiness

The local `cloud_project` database has 196,449 IIT Bombay electricity observations, 52,560 Valahia electricity observations, and 52,560 Valahia heat observations. These are distinct dataset contracts (source, energy vector, unit, and nominal interval) and must remain separate for analysis and training. La Trobe's 8,095,524 records are not loaded into the forecast dashboard because the source unit and timezone have not been verified.

The separate FedAvg profile experiment uses local-time features and scales each client's target by that client's training-only mean absolute value. Its shared target is dimensionless relative demand; a global weight vector cannot independently produce a Wh, W, or kWh forecast. IIT Bombay, IIIT-Delhi, and Valahia clients are each chronologically split and evaluated locally. La Trobe remains excluded until unit/timezone metadata is verified; Twente remains excluded until longer extracts are supplied.

In the recorded local run, 59 clients participated (38 IIT Bombay apartments, 9 IIIT-Delhi buildings, and 12 Valahia building/year/vector files). IIT Bombay apartment 13 had only 37 valid rows and was excluded; the nine short Twente extracts and La Trobe archive were also excluded. The full record of client counts, metrics, exclusions, and weights is in `results/federated_demo/weights.json`.
