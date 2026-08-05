# Deploy-now checklist

## 1. Create a source repository

Create a private or public GitHub repository and upload this folder. Keep `.env` and real secrets out of the repository.

## 2. Deploy on Render

- In Render, choose **New > Blueprint**.
- Connect the repository containing `render.yaml`.
- Review the generated free Docker web service.
- Leave the generated `DIRECT_API_KEY` in place.
- Leave `RAPIDAPI_PROXY_SECRET` blank until RapidAPI supplies it.
- Deploy.
- Confirm `https://<service>.onrender.com/health` returns `status: ok`.

Render free web services can spin down when idle, so expect a cold-start delay. Use the free service only for demand validation, not an uptime promise.

## 3. Test direct access

Copy the generated `DIRECT_API_KEY` from Render and run:

```bash
BASE_URL=https://<service>.onrender.com \
DIRECT_API_KEY=<generated-key> \
./smoke_test.sh
```

## 4. Add to RapidAPI

- Create a provider API in RapidAPI Studio.
- Set the base URL to the Render service.
- Import `openapi.json`.
- Copy RapidAPI's unique `X-RapidAPI-Proxy-Secret` value.
- Add that value to Render as `RAPIDAPI_PROXY_SECRET` and redeploy.
- Enable threat protection and request-schema validation.
- Set a strict request-size limit.
- Publish only the 100-call free developer-preview tier initially.

## 5. Promotion rule

Do not promise certified compliance or invoice acceptance. The listing must say developer preview until full UBL XSD, EN 16931, and Croatian Schematron validation pass official regression fixtures.
