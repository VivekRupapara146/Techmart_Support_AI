# Deployment

Three ways to run this, in the order you'll actually use them:

1. **Local Docker Compose** — fastest way to run the whole backend + a
   local Mongo, no cloud account needed.
2. **AWS App Runner** — the primary deployment target. This is what lets
   you honestly write "deployed on AWS" on your resume.
3. **Render** — documented fallback, genuinely free, good for keeping a
   demo link alive between interviews without AWS charges.

The frontend is a separate static build (Vite) that can be hosted anywhere
static files are served (Render static site, S3+CloudFront, Netlify,
Vercel, GitHub Pages) — it's not tied to whichever platform hosts the
backend. **It always needs `VITE_API_BASE_URL` set at build time** to the
backend's real URL + `/v1` (e.g. `https://xxxx.awsapprunner.com/v1`),
otherwise it falls back to a same-origin relative `/v1` path that won't
resolve when frontend and backend are on different domains.

---

## 1. Local Docker Compose

```bash
cp .env.docker.example .env.docker   # fill in GEMINI_API_KEY at minimum
docker compose up --build
```

- API: http://localhost:8000 (http://localhost:8000/docs for interactive
  OpenAPI docs)
- Mongo: localhost:27017 (a named volume persists data across restarts)

Frontend, separately:

```bash
cd frontend
npm install
echo "VITE_API_BASE_URL=http://localhost:8000/v1" > .env.local
npm run dev
```

---

## 2. AWS App Runner (primary target)

### Why App Runner over ECS Fargate
Both were on the table; App Runner wins for this project specifically
because there's no load balancer, task definition, or VPC networking to
hand-wire for a single container — you get a public HTTPS URL, autoscaling,
and `docker build → push → deploy` in three real AWS primitives (ECR,
App Runner, IAM) instead of eight. ECS Fargate is the better choice once
you have multiple services or need VPC-private networking; neither applies
here.

### Real cost, stated plainly
App Runner has **no free tier** — unlike Lambda, it keeps at least one
instance running continuously. At the smallest configuration (0.25 vCPU /
0.5 GB), expect roughly **$5-8/month** if left running. Two honest options:
- Leave it running while actively interviewing, then **pause or delete the
  service** afterward (`aws apprunner pause-service` / delete) — App Runner
  bills by the second it's running.
- Deploy once to produce real, verifiable screenshots/a recording of a live
  AWS deployment for your portfolio, then tear it down. The commit history
  and this doc are proof it was genuinely deployed, not just "configured
  to deploy."

### One-time setup

**a. MongoDB Atlas (free tier, M0 cluster)**
1. Create a free cluster at https://www.mongodb.com/cloud/atlas.
2. Database Access → add a user with a strong generated password.
3. Network Access → add `0.0.0.0/0` (App Runner doesn't have static
   outbound IPs on the free/default config — this is the same documented
   tradeoff the original Render deployment made; your Mongo
   username/password become the real access boundary, so make that
   password strong and don't reuse it).
4. Copy the connection string — this is your `MONGO_URI`.

**b. ECR repository**
```bash
aws ecr create-repository --repository-name techmart-support-backend --region <your-region>
```

**c. IAM role for GitHub Actions OIDC** (no long-lived AWS keys stored in
GitHub — the workflow assumes a role instead)

Trust policy (`trust-policy.json`), replacing `<ACCOUNT_ID>` and
`<YOUR_GH_ORG>/<YOUR_REPO>`:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com" },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": { "token.actions.githubusercontent.com:aud": "sts.amazonaws.com" },
      "StringLike": { "token.actions.githubusercontent.com:sub": "repo:<YOUR_GH_ORG>/<YOUR_REPO>:*" }
    }
  }]
}
```
(If your account has never used GitHub's OIDC provider before, create it
first: `aws iam create-open-id-connect-provider --url https://token.actions.githubusercontent.com --client-id-list sts.amazonaws.com --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1`.)

```bash
aws iam create-role --role-name techmart-gha-deploy-role --assume-role-policy-document file://trust-policy.json
aws iam attach-role-policy --role-name techmart-gha-deploy-role --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser
aws iam attach-role-policy --role-name techmart-gha-deploy-role --policy-arn arn:aws:iam::aws:policy/AWSAppRunnerFullAccess
```
(`AWSAppRunnerFullAccess` is broader than strictly needed for a resume
project's convenience — for anything beyond a demo, scope this down to
`apprunner:StartDeployment` + `apprunner:DescribeService` on the one
service ARN.)

**d. App Runner service** — created once via CLI (so "deploy automatically
on push" stays OFF; `deploy.yml` triggers each deployment explicitly):
```bash
aws apprunner create-service \
  --service-name techmart-support-backend \
  --source-configuration '{
    "ImageRepository": {
      "ImageIdentifier": "<ACCOUNT_ID>.dkr.ecr.<region>.amazonaws.com/techmart-support-backend:latest",
      "ImageRepositoryType": "ECR",
      "ImageConfiguration": {
        "Port": "8000",
        "RuntimeEnvironmentVariables": {
          "ENVIRONMENT": "production",
          "MONGO_DB_NAME": "techmart_support",
          "ACTIVE_ROUTER": "rule_based",
          "RATE_LIMIT_DEFAULT": "60/minute",
          "DEMO_USERNAME": "demo"
        },
        "RuntimeEnvironmentSecrets": {
          "JWT_SECRET_KEY": "arn:aws:secretsmanager:<region>:<ACCOUNT_ID>:secret:techmart/jwt-secret-key",
          "MONGO_URI": "arn:aws:secretsmanager:<region>:<ACCOUNT_ID>:secret:techmart/mongo-uri",
          "GEMINI_API_KEY": "arn:aws:secretsmanager:<region>:<ACCOUNT_ID>:secret:techmart/gemini-api-key",
          "DEMO_PASSWORD_HASH": "arn:aws:secretsmanager:<region>:<ACCOUNT_ID>:secret:techmart/demo-password-hash",
          "CORS_ALLOWED_ORIGINS": "arn:aws:secretsmanager:<region>:<ACCOUNT_ID>:secret:techmart/cors-origins"
        }
      }
    },
    "AutoDeploymentsEnabled": false
  }' \
  --instance-configuration '{"Cpu": "0.25 vCPU", "Memory": "0.5 GB"}' \
  --health-check-configuration '{"Protocol": "HTTP", "Path": "/health", "Interval": 10, "Timeout": 5, "HealthyThreshold": 1, "UnhealthyThreshold": 3}'
```
Create each `RuntimeEnvironmentSecrets` entry first in Secrets Manager
(`aws secretsmanager create-secret --name techmart/gemini-api-key
--secret-string "..."`, repeated per secret) — App Runner reads them at
container start, they're never stored in the image or in `render.yaml`/CI
logs. Generate `DEMO_PASSWORD_HASH` locally first:
`python -m scripts.generate_password_hash` (from `backend/`).

**e. GitHub repo configuration** (Settings → Secrets and variables →
Actions):
- Secret `AWS_DEPLOY_ROLE_ARN` = the role ARN from step (c)
- Variable `AWS_REGION` = e.g. `us-east-1`
- Variable `ECR_REPOSITORY` = `techmart-support-backend`
- Variable `APP_RUNNER_SERVICE_ARN` = from the `create-service` output

### Deploying
Actions tab → "Deploy to AWS App Runner" → Run workflow. It builds the
image, pushes to ECR, triggers the App Runner deployment, and waits for
`RUNNING`.

---

## 3. Render (fallback)

```bash
git push                      # Render deploys from a Git repo
```
In the Render dashboard: **New → Blueprint**, point it at this repo —
`render.yaml` at the root defines both services. Render will prompt for
every `sync: false` secret (`MONGO_URI`, `GEMINI_API_KEY`,
`DEMO_PASSWORD_HASH`, `CORS_ALLOWED_ORIGINS`, `VITE_API_BASE_URL`).

Two values can only be filled in **after** the first deploy, since each
needs the other service's URL:
1. Backend's `CORS_ALLOWED_ORIGINS` → the frontend's Render URL
2. Frontend's `VITE_API_BASE_URL` → the backend's Render URL + `/v1`

Set both, then trigger a manual redeploy of each service (env var changes
don't auto-redeploy).

Render's free tier spins down on inactivity — the first request after
idling can take 30-60 seconds while the container cold-starts. Not a bug;
a free-tier characteristic, worth disclosing rather than being surprised
by it live.

---

## Sanity checks (any target)

- `GET https://<backend-url>/v1/health` → `200`, `status: "operational"`
- `GET https://<backend-url>/docs` → interactive OpenAPI docs load
- Open the frontend URL → log in with the demo credential → send a message
  → confirm a grounded reply comes back with real evidence/telemetry (not
  the frontend's offline simulation — that only engages if the fetch
  itself fails, so a working deploy should never show it)

## Known, disclosed limitations

- **Single demo credential, not real user accounts** — fine for a resume
  demo link, not a real multi-user product (see `auth/service.py`).
- **`0.0.0.0/0` on Atlas** — the Mongo credential is the real access
  boundary; keep it strong and out of git.
- **In-process FAISS index, not a managed vector DB** — rebuilt from the
  six `knowledge_base/*.txt` files on first chat request per process; fine
  at this corpus size, a documented scaling boundary past it (see
  `rag/vector_store.py`'s docstring).
- **Running with `--workers > 1`** (the Dockerfile's default) means each
  worker process builds its own FAISS index independently on first use,
  and the in-memory rate limiter (slowapi) is per-worker, not shared
  across them — acceptable for a low-traffic demo, a real gap for anything
  resembling production traffic. Set `UVICORN_WORKERS=1` if you want one
  shared, consistent rate limit instead of N independent ones.
