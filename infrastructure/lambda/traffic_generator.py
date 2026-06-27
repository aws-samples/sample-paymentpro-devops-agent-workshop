"""
Lambda function that generates simulated payment traffic.
Triggered by EventBridge on a schedule (every 5 minutes).
"""

import json
import os
import urllib.request
import urllib.error


def handler(event, context):
    """Generate simulated traffic by calling the Payment Service simulate endpoint."""
    
    # Configuration from environment variables
    api_url = os.environ.get("API_URL", "http://localhost:8001")
    count = int(os.environ.get("PAYMENT_COUNT", "5"))
    profile = os.environ.get("PAYMENT_PROFILE", "mixed")
    merchant_id = os.environ.get("MERCHANT_ID", "demo")
    
    # Build the request URL
    url = f"{api_url}/api/v1/simulate/traffic?count={count}&profile={profile}&merchant_id={merchant_id}"
    
    print(f"Generating {count} payments with profile '{profile}' for merchant '{merchant_id}'")
    print(f"URL: {url}")
    
    try:
        req = urllib.request.Request(url, method="POST")
        req.add_header("Content-Type", "application/json")
        
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read().decode("utf-8")
            result = json.loads(body)
            
            print(f"Result: {json.dumps(result)}")
            
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": f"Generated {result.get('total', 0)} payments",
                    "result": result,
                }),
            }
            
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else str(e)
        print(f"HTTP Error {e.code}: {error_body}")
        return {
            "statusCode": e.code,
            "body": json.dumps({"error": error_body}),
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }
