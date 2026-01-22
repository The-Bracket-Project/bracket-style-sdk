# Welcome To Bracket Style SDK v1.0

## Python SDK

The SDK is a thin REST wrapper that authenticates with an API key and exposes a simple client interface.

```bash
python -m pip install -e .
```

```python
from bracket_sdk import BracketClient

client = BracketClient(
    api_key="YOUR_API_KEY",
    base_url="https://api.bracketstyle.com",
    client_id="acme-inc",
)
response = client.get("/v1/health")
print(response)
```

`client_id` is optional and is sent as `x-client-id` to help with internal usage tracking.

You can also call `client.health()` as a convenience method (defaults to `/v1/health`).

## Internal Dashboard

The internal usage dashboard lives in `dashboard/` and is intended for monitoring SDK calls and client IDs.

```bash
python -m pip install -e .[dashboard]
uvicorn dashboard.app:app --reload --port 8001
```

The dashboard reads configuration from environment variables. For local runs, copy `.env.example` to `.env`.

Container:

```bash
docker build -f Dockerfile.dashboard -t bracket-dashboard .
docker run --env-file .env -p 8001:8001 bracket-dashboard
```

### Dashboard Environment Variables

Required for CloudWatch data:
- `DASHBOARD_DATA_SOURCE=cloudwatch`
- `DASHBOARD_CLOUDWATCH_LOG_GROUP=/aws/apigateway/your-log-group`
- `AWS_REGION=us-west-1` (or `AWS_DEFAULT_REGION`)

Optional tuning:
- `DASHBOARD_WINDOW_HOURS_DEFAULT=24`
- `DASHBOARD_CLOUDWATCH_EVENT_LIMIT=2000`
- `DASHBOARD_CACHE_TTL_SECONDS=15`
- `DASHBOARD_CLIENT_ALIAS_FILE=./dashboard/client_aliases.json`

Cloudflare Access (Zero Trust):
- `DASHBOARD_REQUIRE_CF_ACCESS=true`
- `CF_ACCESS_TEAM_DOMAIN=your-team.cloudflareaccess.com`
- `CF_ACCESS_AUD=your-app-aud`
- Optional service token headers: `CF_ACCESS_CLIENT_ID`, `CF_ACCESS_CLIENT_SECRET`
- Health check bypass: `DASHBOARD_CF_ACCESS_SKIP_PATHS=/health`

### Cloudflare Access (Zero Trust)

The dashboard can require Cloudflare Access on every request. When enabled, the app validates the
`Cf-Access-Jwt-Assertion` header or a Cloudflare service token.

Prerequisites:
- Cloudflare Access application covering `sdk-dashboard.dev.thebracket.ai` (or `*.dev.thebracket.ai`)
- JWT assertion enabled in the Access app (so the header is forwarded)
- Cloudflare edge certificate covering `*.dev.thebracket.ai` (Advanced Certificate Manager)

### Deploy: ECS Fargate + ALB + Cloudflare Access

High-level flow:
1. Build and push the image to ECR (us-west-1 for ECS in us-west-1).
2. Run ECS Fargate tasks behind an ALB.
3. Use Cloudflare DNS (proxied) and Access to protect the hostname.

#### 1) ECR push

```bash
AWS_REGION=us-west-1
AWS_ACCOUNT_ID=471112914009
REPO_NAME=sdk-internal-dashboard
IMAGE_TAG=latest

aws ecr create-repository --repository-name "$REPO_NAME" --region "$AWS_REGION"
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

docker build -f Dockerfile.dashboard -t "$REPO_NAME:$IMAGE_TAG" .
docker tag "$REPO_NAME:$IMAGE_TAG" "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:$IMAGE_TAG"
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:$IMAGE_TAG"
```

#### 2) IAM roles

Execution role (ECS-managed):
- `AmazonECSTaskExecutionRolePolicy` (pull image, write logs)

Task role (app permissions):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["logs:FilterLogEvents", "logs:DescribeLogStreams"],
      "Resource": "arn:aws:logs:us-west-1:471112914009:log-group:/aws/apigateway/bracket-sdk-prod-access:*"
    }
  ]
}
```

If the log group is KMS-encrypted, add `kms:Decrypt` on the CMK.

#### 3) ECS task definition

- Container port: `8001`
- Env vars: set from the list above (CloudWatch + Cloudflare Access)
- Logs: awslogs

Deploy a new task definition revision whenever you push a new image.

#### 4) ALB (HTTPS)

- Create an **HTTPS:443** listener on the ALB with an ACM cert for `*.dev.thebracket.ai`.
- Forward to a target group on **HTTP:8001** with health check path `/health`.
- Optional: redirect HTTP:80 to HTTPS:443.

#### 5) Cloudflare DNS + Access

Cloudflare zone: `thebracket.ai`

DNS record:
- `CNAME` `sdk-dashboard.dev` → `sdk-dashboard-alb-1512508604.us-west-1.elb.amazonaws.com`
- Proxy: **ON** (orange cloud)

Cloudflare Access:
- Application domain `sdk-dashboard.dev.thebracket.ai` or `*.dev.thebracket.ai`
- Enable **JWT assertion**
- Policies for Google Workspace users/groups

TLS:
- Cloudflare SSL mode: **Full (strict)**
- Cloudflare Advanced Certificate Manager should include `*.dev.thebracket.ai`
- ACM in us-west-1 should include `*.dev.thebracket.ai`

#### 6) (Optional) Origin hardening

- Restrict the ALB security group to Cloudflare IP ranges.

### Troubleshooting

No CloudWatch data:
- Verify ECS **task role** has CloudWatch Logs permissions.
- Confirm the log group is in the same region as `AWS_REGION`.
- Ensure API Gateway access logs are JSON; non-JSON messages are skipped.
- Increase `DASHBOARD_WINDOW_HOURS_DEFAULT` to confirm data exists.

Cloudflare Access timeouts:
- Ensure tasks have outbound internet (NAT if in private subnets) to fetch JWKS.
- Confirm the Access app is sending the JWT header.

TLS errors:
- Cloudflare edge cert for `*.dev.thebracket.ai` is **Active**.
- ALB has HTTPS listener + ACM cert for `*.dev.thebracket.ai`.
## Demo API (v1)

Run the demo API locally to validate the SDK health check and usage tracking pipeline.

```bash
python -m pip install -e .[demo,dashboard]
export BRACKET_API_KEY="dev-key"
export DASHBOARD_URL="http://localhost:8001"
uvicorn demo_api.app:app --reload --port 8000
```

Then point the SDK at `http://localhost:8000` and call `/v1/health`.

## Smoke Test Scripts

If your API Gateway requires a stage, pass `--stage` (or set `BRACKET_STAGE`).
If your base URL already includes the stage, omit it.

```bash
python scripts/smoke_test.py \\
  --base-url "https://{api_id}.execute-api.{region}.amazonaws.com" \\
  --stage "prod" \\
  --api-key "YOUR_KEY" \\
  --client-id "acme-inc" \\
  --path "/v1/health"
```

```bash
python scripts/smoke_generate.py \\
  --base-url "https://{api_id}.execute-api.{region}.amazonaws.com" \\
  --stage "prod" \\
  --api-key "YOUR_KEY" \\
  --client-id "acme-inc" \\
  --body '{"inputs":"Say hello in one sentence.","parameters":{"max_new_tokens":64,"temperature":0.2}}'
```
