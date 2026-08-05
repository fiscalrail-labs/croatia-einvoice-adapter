# One-upload update path

This archive is deliberately also provided under the compatibility filename:

`croatia-einvoice-adapter-deployable-v0.2.0.zip`

The existing `Unpack project` GitHub Action in the live repository expects that exact filename. Upload the compatibility archive to the repository root and run the existing workflow once. The workflow commits the updated files, and Render's GitHub auto-deploy should then build v0.3.0.

Do not enable paid marketplace plans until the live endpoint `GET /ready` returns HTTP 200 with `production_ready: true`.
