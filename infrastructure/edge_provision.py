#!/usr/bin/env python3
"""Edge/IoT helper for the Smart Campus Energy Cloud.

Subcommands (all need --stack and optionally --region):

  seed        Load buildings and example tariff windows into DynamoDB.
  provision   Create an IoT thing + X.509 certificate for a building gateway
              and attach the stack's device policy. Credentials are written
              to ./certs/<thing>/ (git-ignored).
  simulate    Publish synthetic telemetry (uses YOUR AWS credentials; dev only).
  cleanup     Detach and delete the things/certificates created by 'provision'.

Examples:
  python3 edge_provision.py --stack smart-campus-energy-dev seed
  python3 edge_provision.py --stack smart-campus-energy-dev seed --peak-now
  python3 edge_provision.py --stack smart-campus-energy-dev provision --building lab_1
  python3 edge_provision.py --stack smart-campus-energy-dev simulate --building lab_1 --count 20
"""
import argparse
import json
import math
import os
import pathlib
import random
import time
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import boto3

DEFAULT_BUILDINGS = "block_a:classroom,lab_1:lab,hostel_1:hostel,admin_1:admin"
ROOT_CA_URL = "https://www.amazontrust.com/repository/AmazonRootCA1.pem"
CERT_DIR = pathlib.Path(__file__).parent / "certs"

DEFAULT_TARIFF = [
    {"window_id": "morning-peak", "name": "Morning peak", "start_hour": 6, "end_hour": 10, "is_peak": True, "price_per_kwh": Decimal("9.0")},
    {"window_id": "evening-peak", "name": "Evening peak", "start_hour": 18, "end_hour": 22, "is_peak": True, "price_per_kwh": Decimal("9.0")},
    {"window_id": "off-peak", "name": "Off-peak", "start_hour": 22, "end_hour": 24, "is_peak": False, "price_per_kwh": Decimal("5.0")},
]


def stack_outputs(stack, region):
    cfn = boto3.client("cloudformation", region_name=region)
    outputs = cfn.describe_stacks(StackName=stack)["Stacks"][0].get("Outputs", [])
    return {o["OutputKey"]: o["OutputValue"] for o in outputs}


def parse_buildings(text):
    result = {}
    for part in text.split(","):
        building_id, _, btype = part.strip().partition(":")
        if building_id:
            result[building_id] = btype or "classroom"
    return result


# ------------------------------------------------------------------ seed
def cmd_seed(args, out):
    ddb = boto3.resource("dynamodb", region_name=args.region)
    buildings = ddb.Table(out["BuildingsTableName"])
    tariff = ddb.Table(out["TariffTableName"])

    for building_id, btype in parse_buildings(args.buildings).items():
        buildings.put_item(Item={"building_id": building_id, "building_type": btype})
        print("building:", building_id, btype)

    for window in DEFAULT_TARIFF:
        tariff.put_item(Item=window)
        print("tariff  :", window["window_id"])

    if args.peak_now:
        hour = datetime.now(ZoneInfo(args.timezone)).hour
        tariff.put_item(Item={
            "window_id": "demo-peak-now",
            "name": "Demo peak (current hour)",
            "start_hour": hour,
            "end_hour": hour + 1,
            "is_peak": True,
            "price_per_kwh": Decimal("9.0"),
        })
        print("tariff  : demo-peak-now covers local hour", hour, "(remove it after testing)")


# ------------------------------------------------------------- provision
def cmd_provision(args, out):
    iot = boto3.client("iot", region_name=args.region)
    thing = "{}-{}".format(out["ThingPrefix"], args.building)
    policy = out["IotPolicyName"]

    try:
        iot.create_thing(thingName=thing, attributePayload={"attributes": {"building_id": args.building}})
        print("created thing", thing)
    except iot.exceptions.ResourceAlreadyExistsException:
        print("thing exists:", thing)

    target = CERT_DIR / thing
    if (target / "device.pem.crt").exists() and not args.force:
        print("credentials already exist in", target, "(use --force to issue new ones)")
        return

    keys = iot.create_keys_and_certificate(setAsActive=True)
    iot.attach_policy(policyName=policy, target=keys["certificateArn"])
    iot.attach_thing_principal(thingName=thing, principal=keys["certificateArn"])

    target.mkdir(parents=True, exist_ok=True)
    (CERT_DIR / ".gitignore").write_text("*\n")
    (target / "device.pem.crt").write_text(keys["certificatePem"])
    (target / "private.pem.key").write_text(keys["keyPair"]["PrivateKey"])
    (target / "public.pem.key").write_text(keys["keyPair"]["PublicKey"])
    (target / "certificate_arn.txt").write_text(keys["certificateArn"])
    os.chmod(target / "private.pem.key", 0o600)

    try:
        with urllib.request.urlopen(ROOT_CA_URL, timeout=15) as resp:
            (target / "AmazonRootCA1.pem").write_bytes(resp.read())
    except Exception as err:  # offline: user can download manually
        print("Could not download Amazon Root CA 1 ({}); get it from {}".format(err, ROOT_CA_URL))

    endpoint = iot.describe_endpoint(endpointType="iot:Data-ATS")["endpointAddress"]
    print("\nCredentials saved to", target)
    print("MQTT endpoint :", endpoint)
    print("Client id     :", thing)
    print("Publish topic : campus/{}/telemetry".format(args.building))
    print("Keep private.pem.key secret; never commit it.")


# -------------------------------------------------------------- simulate
def synthetic_reading(base_kw, now):
    hour = now.hour + now.minute / 60
    daily = 0.6 + 0.4 * math.sin((hour - 9) / 24 * 2 * math.pi)
    return {
        "ts": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "power_kw": round(max(0.5, base_kw * daily + random.gauss(0, base_kw * 0.05)), 2),
        "voltage_v": round(230 + random.gauss(0, 2), 1),
        "temperature_c": round(26 + random.gauss(0, 1), 1),
        "humidity_pct": round(min(100, max(0, 55 + random.gauss(0, 5))), 1),
        "occupancy_count": max(0, int(60 * daily + random.gauss(0, 5))),
    }


def cmd_simulate(args, out):
    iot = boto3.client("iot", region_name=args.region)
    endpoint = iot.describe_endpoint(endpointType="iot:Data-ATS")["endpointAddress"]
    data = boto3.client("iot-data", region_name=args.region, endpoint_url="https://" + endpoint)
    topic = "campus/{}/telemetry".format(args.building)

    for i in range(args.count):
        payload = synthetic_reading(args.base_kw, datetime.now(timezone.utc))
        data.publish(topic=topic, qos=1, payload=json.dumps(payload))
        print("[{}/{}] {} {}".format(i + 1, args.count, topic, payload))
        time.sleep(args.interval)


# --------------------------------------------------------------- cleanup
def cmd_cleanup(args, out):
    iot = boto3.client("iot", region_name=args.region)
    prefix = out["ThingPrefix"] + "-"
    policy = out["IotPolicyName"]
    paginator = iot.get_paginator("list_things")
    for page in paginator.paginate():
        for thing in page["things"]:
            name = thing["thingName"]
            if not name.startswith(prefix):
                continue
            for arn in iot.list_thing_principals(thingName=name)["principals"]:
                iot.detach_thing_principal(thingName=name, principal=arn)
                try:
                    iot.detach_policy(policyName=policy, target=arn)
                except Exception:
                    pass
                cert_id = arn.split("/")[-1]
                iot.update_certificate(certificateId=cert_id, newStatus="INACTIVE")
                iot.delete_certificate(certificateId=cert_id, forceDelete=True)
            iot.delete_thing(thingName=name)
            print("deleted", name)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--stack", default=os.environ.get("STACK_NAME", "smart-campus-energy-dev"))
    parser.add_argument("--region", default=os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "ap-south-1")))
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("seed", help="load buildings and tariff windows")
    p.add_argument("--buildings", default=DEFAULT_BUILDINGS, help="id:type,id:type (default: %(default)s)")
    p.add_argument("--peak-now", action="store_true", help="add a peak window covering the current hour (for demos)")
    p.add_argument("--timezone", default=os.environ.get("TIMEZONE", "Asia/Kolkata"))
    p.set_defaults(func=cmd_seed)

    p = sub.add_parser("provision", help="create IoT thing + certificate for a building")
    p.add_argument("--building", required=True)
    p.add_argument("--force", action="store_true", help="issue a new certificate even if one exists locally")
    p.set_defaults(func=cmd_provision)

    p = sub.add_parser("simulate", help="publish synthetic telemetry (dev only)")
    p.add_argument("--building", required=True)
    p.add_argument("--count", type=int, default=10)
    p.add_argument("--interval", type=float, default=1.0)
    p.add_argument("--base-kw", type=float, default=45.0)
    p.set_defaults(func=cmd_simulate)

    p = sub.add_parser("cleanup", help="delete things/certificates created by 'provision'")
    p.set_defaults(func=cmd_cleanup)

    args = parser.parse_args()
    args.func(args, stack_outputs(args.stack, args.region))


if __name__ == "__main__":
    main()
