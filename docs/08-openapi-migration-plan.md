# OpenAPI Migration Plan (Ranger 2)

## Objective

Move from unstable reverse-engineered P2P tunnel flow to official Imou OpenAPI live flow.

## Scope

- Obtain `accessToken` from Imou OpenAPI.
- Create/query live stream for `IMOU Ranger 2`.
- Produce HLS URL for downstream analytics pipeline.

## Implementation

1. Prepare credentials in `camera.env.bat`:
   - `IMOU_APP_ID`
   - `IMOU_APP_SECRET`
   - `IMOU_CAMERA_SN`
   - `IMOU_OPENAPI_DC` (`sg`/`fk`/`or`) or `IMOU_OPENAPI_DOMAIN`
2. Run `run_openapi_live_test.bat`.
3. Validate output in:
   - Console HLS URL
   - `logs/openapi_live_result.json`
4. Feed HLS URL into analytics consumer (OpenCV/PyAV/FFmpeg).

## Risks

- Wrong data center causes API failures.
- Missing app permissions for target device.
- Stream may be disabled by plan/status (`liveStatus`).

## Rollback

- Keep existing `dh-p2p` scripts available as fallback PoC path.
- Use `run_rust_probe.bat` only for troubleshooting, not production path.
