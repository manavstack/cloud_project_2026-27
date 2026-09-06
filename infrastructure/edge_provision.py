import boto3
import json
import os

def provision_edge_node(thing_name="CampusEdgeNode_01"):
    print(f"Provisioning IoT Thing: {thing_name}")
    iot = boto3.client('iot', region_name="ap-south-1")
    
    try:
        # 1. Create Thing
        response = iot.create_thing(thingName=thing_name)
        thing_arn = response['thingArn']
        thing_id = response['thingId']
        print(f"Created Thing {thing_name} with ID {thing_id}")
        
        # 2. Create Certificate
        cert_response = iot.create_keys_and_certificate(setAsActive=True)
        certificate_arn = cert_response['certificateArn']
        
        cert_dir = os.path.join(os.path.dirname(__file__), '..', 'local_server', 'certs')
        os.makedirs(cert_dir, exist_ok=True)
        
        with open(os.path.join(cert_dir, 'edge-certificate.pem.crt'), 'w') as f:
            f.write(cert_response['certificatePem'])
        with open(os.path.join(cert_dir, 'edge-private.pem.key'), 'w') as f:
            f.write(cert_response['keyPair']['PrivateKey'])
            
        print("Downloaded certificates to local_server/certs/")
        
        # 3. Attach Cert to Thing
        iot.attach_thing_principal(
            thingName=thing_name,
            principal=certificate_arn
        )
        print("Attached certificate to Thing.")
    except Exception as e:
        print(f"Failed to provision edge node: {e}")

if __name__ == "__main__":
    provision_edge_node()
