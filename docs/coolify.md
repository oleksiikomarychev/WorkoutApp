# Backend deployment in Coolify

This deployment uses `docker-compose.prod.yml`. It contains only the API gateway,
six backend services, and Redis. Social, messaging, the agent, CRM, Celery workers,
monitoring, and analytics are absent from this production file, so Coolify cannot
pull their large images during deployment. The corresponding API features need
those services before they can work.

## Server and images

The default stack has eight containers and several services run both HTTP and
gRPC processes. A 0.5 vCPU VPS is unlikely to run this stack reliably, especially
if Coolify is installed on the same machine. Use a larger deployment server and
watch CPU and RAM during startup and normal traffic. The PostgreSQL URLs in this
stack point to external databases; no PostgreSQL container is started.

All application services in the production Compose file use prebuilt Docker Hub
images tagged `latest`. The `Publish backend images` GitHub Actions workflow
builds and pushes all nine application images after a push to `main`, with
both `latest` and `sha-<commit>` tags. Add repository secrets
`DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` before relying on this workflow.
The token needs permission to push to the `oleksiikomarychev` Docker Hub
repositories. The workflow builds `linux/amd64` images, so check the VPS
architecture before deploying. Wait until all image jobs succeed, then
redeploy in Coolify; a Git-triggered deploy may run before image publishing
finishes.

## Create the Coolify application

1. In a Coolify project/environment, choose **New → Git repository** and select
   this repository and the production branch.
2. Select **Docker Compose** as the build strategy. Set **Base Directory** to
   `/` and **Docker Compose Location** to `/docker-compose.prod.yml`.
3. In **Environment Variables**, enter the production values. The local
   `.env.example` contains production values, but it is ignored by Git and is
   not available to Coolify automatically. Do not commit it. Copy only the
   variables this deployment needs into Coolify; Developer view accepts
   `.env` format. Replace placeholder passwords and any secrets that have
   been shared.
4. At minimum, set `PLANS_DATABASE_URL`, `EXERCISES_DATABASE_URL`,
   `USER_MAX_DATABASE_URL`, `WORKOUTS_DATABASE_URL`,
   `ACCOUNTS_DATABASE_URL`, `INTERNAL_GATEWAY_SECRET`, `REDIS_PASSWORD`,
   `FIREBASE_CREDENTIALS_BASE64`, and `FIREBASE_PROJECT_ID`. The Compose
   definition marks these values as required. Use a strong URL-safe Redis
   password because Celery broker URLs include it. The password and internal
   gateway secret in `.env.example` are placeholders and must be replaced.
5. Add a domain such as `https://api.example.com` to the **gateway** service,
   with internal port **8000**. Point its DNS record to the deployment server.
   Use normal Compose deployment, not Raw, so Coolify configures the proxy.
6. Deploy. Check the deployment and runtime logs, then request
   `https://api.example.com/api/v1/health`. Check the other API functions that
   your client uses; the gateway health endpoint does not test every upstream.

Redis and application data use named volumes in the Compose file. Back up those
volumes; persistent storage alone is not a backup. The supplements SQLite file
is stored in the persistent `workouts_data` volume.

## Client configuration

Flutter release builds now select the production API endpoint. Set it when
building the client, for example:

```sh
cd flutter_app
flutter build apk --release --dart-define=PROD_API_BASE_URL=https://api.example.com
```

The build-time value overrides the production URL in
`flutter_app/assets/env/app.env`. The web image routes `/api/` to the existing
gateway through Nginx, so browser API calls use the website's HTTPS origin.
The optional agent, social, and messaging features are unavailable in this
deployment.

If using Stripe, update public callback URLs to the new HTTPS domain and set
the Stripe variables in Coolify. CRM requires a separate deployment.
